from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import joblib
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "models"
MLRUNS_DIR = BASE_DIR / "mlruns"
MODEL_PATH = MODELS_DIR / "kev_horizon_ranker.joblib"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"
CLASSIFICATION_REPORT_PATH = REPORTS_DIR / "classification_report.csv"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.csv"
FEATURE_IMPORTANCE_PATH = REPORTS_DIR / "feature_importance.csv"
FEATURE_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "feature_importance.png"
SHAP_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "shap_feature_importance.png"

LABEL_HORIZON_DAYS = int(os.getenv("LABEL_HORIZON_DAYS", "180"))
RANDOM_STATE = 42

NUMERIC_FEATURES = [
    "cvss_base_score",
    "reference_count",
    "affected_entry_count",
    "published_month",
]
CATEGORICAL_FEATURES = [
    "cvss_base_severity",
    "attack_vector",
    "attack_complexity",
    "privileges_required",
    "user_interaction",
    "cwe_id",
]
TARGET_COLUMN = "kev_within_horizon"


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def load_training_data() -> pd.DataFrame:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Missing analytics database: {DATABASE_PATH}. Run scripts/run_pipeline.py first."
        )

    query = f"""
        with snapshot as (
            select max(epss_date) as observation_date
            from raw_vulnerability_priority
        )
        select
            m.cve_id,
            m.published_date,
            s.observation_date,
            m.cvss_base_score,
            m.reference_count,
            m.affected_entry_count,
            m.published_month,
            m.cvss_base_severity,
            m.attack_vector,
            m.attack_complexity,
            m.privileges_required,
            m.user_interaction,
            m.cwe_id,
            case
                when r.date_added is not null
                 and r.date_added <= m.published_date + interval '{LABEL_HORIZON_DAYS} days'
                then 1
                else 0
            end as {TARGET_COLUMN}
        from mart_vulnerability_priority as m
        inner join raw_vulnerability_priority as r using (cve_id)
        cross join snapshot as s
        where m.cvss_base_score is not null
          and m.published_date is not null
          and s.observation_date is not null
          and m.published_date <= s.observation_date - interval '{LABEL_HORIZON_DAYS} days'
        order by m.published_date, m.cve_id
    """

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        dataframe = connection.execute(query).fetchdf()

    if dataframe.empty:
        raise ValueError("No CVEs have a complete label observation window.")

    if dataframe[TARGET_COLUMN].nunique() < 2:
        raise ValueError("Training data must contain both target classes.")

    return dataframe


def build_model_pipeline() -> Pipeline:
    numeric_pipeline = Pipeline(
        [("imputer", SimpleImputer(strategy="constant", fill_value=0))]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("one_hot_encoder", make_one_hot_encoder()),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=1,
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def split_temporal(dataframe: pd.DataFrame):
    dataframe = dataframe.sort_values(["published_date", "cve_id"]).reset_index(drop=True)
    observation_date = pd.Timestamp(dataframe["observation_date"].max())
    mature_cutoff = observation_date - pd.Timedelta(days=LABEL_HORIZON_DAYS)

    current_quarter_start = mature_cutoff.to_period("Q").start_time
    test_start = current_quarter_start - pd.DateOffset(months=3)
    validation_start = test_start - pd.DateOffset(months=3)

    train = dataframe[dataframe["published_date"] < validation_start].copy()
    validation = dataframe[
        (dataframe["published_date"] >= validation_start)
        & (dataframe["published_date"] < test_start)
    ].copy()
    test = dataframe[dataframe["published_date"] >= test_start].copy()

    for name, split in (("train", train), ("validation", validation), ("test", test)):
        if split.empty:
            raise ValueError(f"Temporal {name} split is empty.")
        if split[TARGET_COLUMN].nunique() < 2:
            counts = split[TARGET_COLUMN].value_counts().to_dict()
            raise ValueError(f"Temporal {name} split does not contain both classes: {counts}")

    return train, validation, test, observation_date, mature_cutoff, validation_start, test_start


def feature_names(model: Pipeline) -> list[str]:
    preprocessor = model.named_steps["preprocessor"]
    categorical = preprocessor.named_transformers_["categorical"]
    encoder = categorical.named_steps["one_hot_encoder"]
    return NUMERIC_FEATURES + encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist()


def choose_threshold(y_true: np.ndarray, y_scores: np.ndarray) -> tuple[float, float]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
    if len(thresholds) == 0:
        return 0.5, 0.0

    f1_values = np.divide(
        2 * precisions[:-1] * recalls[:-1],
        precisions[:-1] + recalls[:-1],
        out=np.zeros_like(thresholds, dtype=float),
        where=(precisions[:-1] + recalls[:-1]) > 0,
    )
    best_index = int(np.argmax(f1_values))
    return float(thresholds[best_index]), float(f1_values[best_index])


def precision_recall_at_k(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    k: int,
) -> tuple[float, float]:
    k = min(k, len(y_true))
    ranked = np.argsort(-y_scores)[:k]
    positives = int(y_true.sum())
    hits = int(y_true[ranked].sum())
    return hits / k, hits / positives if positives else float("nan")


def save_feature_importance(model: Pipeline, names: list[str]) -> None:
    values = model.named_steps["classifier"].feature_importances_
    dataframe = pd.DataFrame({"feature": names, "importance": values}).sort_values(
        "importance", ascending=False
    )
    dataframe.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    top = dataframe.head(20).sort_values("importance")
    plt.figure(figsize=(10, 8))
    plt.barh(top["feature"], top["importance"])
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(FEATURE_IMPORTANCE_PLOT_PATH, dpi=160)
    plt.close()


def save_shap_importance(model: Pipeline, x_test: pd.DataFrame, names: list[str]) -> None:
    sample = x_test.sample(min(500, len(x_test)), random_state=RANDOM_STATE)
    transformed = model.named_steps["preprocessor"].transform(sample)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()

    values = shap.TreeExplainer(model.named_steps["classifier"]).shap_values(transformed)
    if isinstance(values, list):
        absolute = np.abs(values[-1])
    else:
        array = np.asarray(values)
        absolute = np.abs(array[:, :, -1]) if array.ndim == 3 else np.abs(array)

    dataframe = pd.DataFrame(
        {"feature": names, "mean_absolute_shap_value": absolute.mean(axis=0)}
    ).sort_values("mean_absolute_shap_value", ascending=False)
    top = dataframe.head(20).sort_values("mean_absolute_shap_value")
    plt.figure(figsize=(10, 8))
    plt.barh(top["feature"], top["mean_absolute_shap_value"])
    plt.xlabel("Mean absolute SHAP value")
    plt.tight_layout()
    plt.savefig(SHAP_IMPORTANCE_PLOT_PATH, dpi=160)
    plt.close()


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

    dataframe = load_training_data()
    (
        train,
        validation,
        test,
        observation_date,
        mature_cutoff,
        validation_start,
        test_start,
    ) = split_temporal(dataframe)

    x_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    x_train = train[x_columns]
    y_train = train[TARGET_COLUMN].astype(int)
    x_validation = validation[x_columns]
    y_validation = validation[TARGET_COLUMN].astype(int)
    x_test = test[x_columns]
    y_test = test[TARGET_COLUMN].astype(int)

    model = build_model_pipeline()
    model.fit(x_train, y_train)

    validation_probabilities = model.predict_proba(x_validation)[:, 1]
    tuned_threshold, validation_best_f1 = choose_threshold(
        y_validation.to_numpy(), validation_probabilities
    )

    test_probabilities = model.predict_proba(x_test)[:, 1]
    test_predictions = (test_probabilities >= tuned_threshold).astype(int)

    test_positive_rate = float(y_test.mean())
    metrics = {
        "label_definition": f"CISA KEV inclusion within {LABEL_HORIZON_DAYS} days of NVD publication",
        "evaluation_design": "retrospective_temporal_holdout",
        "label_horizon_days": LABEL_HORIZON_DAYS,
        "observation_date": str(observation_date.date()),
        "mature_cutoff_date": str(mature_cutoff.date()),
        "rows_after_observation_filter": int(len(dataframe)),
        "positive_examples": int(dataframe[TARGET_COLUMN].sum()),
        "train_rows": int(len(train)),
        "train_positives": int(y_train.sum()),
        "train_start_date": str(train["published_date"].min()),
        "train_end_date": str(train["published_date"].max()),
        "validation_rows": int(len(validation)),
        "validation_positives": int(y_validation.sum()),
        "validation_start_date": str(validation_start.date()),
        "validation_end_date": str(validation["published_date"].max()),
        "test_rows": int(len(test)),
        "test_positives": int(y_test.sum()),
        "test_start_date": str(test_start.date()),
        "test_end_date": str(test["published_date"].max()),
        "validation_roc_auc": round(float(roc_auc_score(y_validation, validation_probabilities)), 4),
        "validation_average_precision": round(
            float(average_precision_score(y_validation, validation_probabilities)), 4
        ),
        "validation_best_f1": round(validation_best_f1, 4),
        "tuned_threshold": round(tuned_threshold, 4),
        "test_positive_rate": round(test_positive_rate, 6),
        "test_accuracy": round(float(accuracy_score(y_test, test_predictions)), 4),
        "test_balanced_accuracy": round(
            float(balanced_accuracy_score(y_test, test_predictions)), 4
        ),
        "test_precision": round(
            float(precision_score(y_test, test_predictions, zero_division=0)), 4
        ),
        "test_recall": round(
            float(recall_score(y_test, test_predictions, zero_division=0)), 4
        ),
        "test_f1": round(float(f1_score(y_test, test_predictions, zero_division=0)), 4),
        "test_macro_f1": round(
            float(f1_score(y_test, test_predictions, average="macro", zero_division=0)), 4
        ),
        "test_roc_auc": round(float(roc_auc_score(y_test, test_probabilities)), 4),
        "test_average_precision": round(
            float(average_precision_score(y_test, test_probabilities)), 4
        ),
    }

    for k in (10, 20, 50):
        precision_k, recall_k = precision_recall_at_k(
            y_test.to_numpy(), test_probabilities, k
        )
        metrics[f"test_precision_at_{k}"] = round(float(precision_k), 4)
        metrics[f"test_recall_at_{k}"] = round(float(recall_k), 4)
        metrics[f"test_lift_at_{k}"] = (
            round(float(precision_k / test_positive_rate), 2)
            if test_positive_rate > 0
            else None
        )

    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame(
        classification_report(
            y_test,
            test_predictions,
            labels=[0, 1],
            output_dict=True,
            zero_division=0,
        )
    ).transpose().to_csv(CLASSIFICATION_REPORT_PATH)
    pd.DataFrame(
        confusion_matrix(y_test, test_predictions, labels=[0, 1]),
        index=["actual_0", "actual_1"],
        columns=["predicted_0", "predicted_1"],
    ).to_csv(CONFUSION_MATRIX_PATH)

    names = feature_names(model)
    save_feature_importance(model, names)
    save_shap_importance(model, x_test, names)
    joblib.dump(model, MODEL_PATH)

    mlflow.set_tracking_uri(MLRUNS_DIR.as_uri())
    mlflow.set_experiment("cyber-risk-kev-horizon")
    with mlflow.start_run(run_name="random_forest_temporal_ranker"):
        mlflow.log_params(
            {
                "model_type": "RandomForestClassifier",
                "label_horizon_days": LABEL_HORIZON_DAYS,
                "evaluation_design": "retrospective_temporal_holdout",
                "validation_start_date": str(validation_start.date()),
                "test_start_date": str(test_start.date()),
            }
        )
        for key, value in metrics.items():
            if isinstance(value, (int, float)) and value is not None:
                mlflow.log_metric(key, value)
        input_example = x_train.head(5).copy()
        input_example[NUMERIC_FEATURES] = input_example[NUMERIC_FEATURES].astype("float64")
        signature = infer_signature(
            input_example,
            model.predict_proba(input_example),
        )
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            signature=signature,
            input_example=input_example,
        )
        for artifact in (
            METRICS_PATH,
            CLASSIFICATION_REPORT_PATH,
            CONFUSION_MATRIX_PATH,
            FEATURE_IMPORTANCE_PATH,
            FEATURE_IMPORTANCE_PLOT_PATH,
            SHAP_IMPORTANCE_PLOT_PATH,
        ):
            mlflow.log_artifact(str(artifact))

    print(json.dumps(metrics, indent=2))
    print(f"Saved model: {MODEL_PATH}")


if __name__ == "__main__":
    main()
