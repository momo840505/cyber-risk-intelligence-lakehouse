from __future__ import annotations

import json
from pathlib import Path

import duckdb
import joblib
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parents[1]

ANALYTICS_DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "models"
MLRUNS_DIR = BASE_DIR / "mlruns"

MODEL_PATH = MODELS_DIR / "priority_classifier.joblib"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"
CLASSIFICATION_REPORT_PATH = REPORTS_DIR / "classification_report.csv"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.csv"
FEATURE_IMPORTANCE_PATH = REPORTS_DIR / "feature_importance.csv"
FEATURE_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "feature_importance.png"
SHAP_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "shap_feature_importance.png"


NUMERIC_FEATURES = [
    "cvss_base_score",
    "epss_score",
    "epss_percentile",
    "is_known_exploited",
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

TARGET_COLUMN = "priority_level"

RANDOM_STATE = 42
TEST_SIZE = 0.25


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def load_training_data() -> pd.DataFrame:
    if not ANALYTICS_DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Missing analytics database: {ANALYTICS_DATABASE_PATH}. "
            "Run scripts/run_dbt.py before training the model."
        )

    query = """
        select
            cvss_base_score,
            epss_score,
            epss_percentile,
            is_known_exploited,
            reference_count,
            affected_entry_count,
            published_month,
            cvss_base_severity,
            attack_vector,
            attack_complexity,
            privileges_required,
            user_interaction,
            cwe_id,
            priority_level
        from mart_vulnerability_priority
        where priority_level is not null
    """

    with duckdb.connect(str(ANALYTICS_DATABASE_PATH)) as connection:
        dataframe = connection.execute(query).fetchdf()

    if dataframe.empty:
        raise ValueError("Training dataframe is empty.")

    return dataframe


def prepare_train_test_split(dataframe: pd.DataFrame):
    features = dataframe[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    target = dataframe[TARGET_COLUMN].copy()

    class_counts = target.value_counts()
    can_stratify = bool((class_counts >= 2).all())

    stratify_target = target if can_stratify else None

    return train_test_split(
        features,
        target,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=stratify_target,
    )


def build_model_pipeline() -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("one_hot_encoder", make_one_hot_encoder()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def get_transformed_feature_names(model_pipeline: Pipeline) -> list[str]:
    preprocessor = model_pipeline.named_steps["preprocessor"]

    numeric_feature_names = NUMERIC_FEATURES

    categorical_transformer = preprocessor.named_transformers_["categorical"]
    one_hot_encoder = categorical_transformer.named_steps["one_hot_encoder"]
    categorical_feature_names = one_hot_encoder.get_feature_names_out(
        CATEGORICAL_FEATURES
    ).tolist()

    return numeric_feature_names + categorical_feature_names


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_feature_importance(
    model_pipeline: Pipeline,
    feature_names: list[str],
) -> pd.DataFrame:
    classifier = model_pipeline.named_steps["classifier"]

    importance_dataframe = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": classifier.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    importance_dataframe.to_csv(FEATURE_IMPORTANCE_PATH, index=False)

    top_features = importance_dataframe.head(20).sort_values(
        "importance",
        ascending=True,
    )

    plt.figure(figsize=(10, 8))
    plt.barh(top_features["feature"], top_features["importance"])
    plt.title("Top 20 Random Forest Feature Importances")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(FEATURE_IMPORTANCE_PLOT_PATH, dpi=160)
    plt.close()

    return importance_dataframe


def calculate_shap_importance(
    model_pipeline: Pipeline,
    features_test: pd.DataFrame,
    feature_names: list[str],
) -> pd.DataFrame:
    preprocessor = model_pipeline.named_steps["preprocessor"]
    classifier = model_pipeline.named_steps["classifier"]

    sample_size = min(500, len(features_test))
    shap_sample = features_test.sample(
        n=sample_size,
        random_state=RANDOM_STATE,
    )

    transformed_sample = preprocessor.transform(shap_sample)

    if hasattr(transformed_sample, "toarray"):
        transformed_sample = transformed_sample.toarray()

    explainer = shap.TreeExplainer(classifier)
    shap_values = explainer.shap_values(transformed_sample)

    if isinstance(shap_values, list):
        absolute_values = np.mean(
            [np.abs(class_values) for class_values in shap_values],
            axis=0,
        )
    else:
        shap_array = np.asarray(shap_values)

        if shap_array.ndim == 3:
            if shap_array.shape[1] == len(feature_names):
                absolute_values = np.mean(np.abs(shap_array), axis=2)
            elif shap_array.shape[2] == len(feature_names):
                absolute_values = np.mean(np.abs(shap_array), axis=0)
            else:
                raise ValueError(
                    f"Unexpected SHAP shape: {shap_array.shape}"
                )
        elif shap_array.ndim == 2:
            absolute_values = np.abs(shap_array)
        else:
            raise ValueError(f"Unexpected SHAP shape: {shap_array.shape}")

    shap_importance = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_absolute_shap_value": absolute_values.mean(axis=0),
        }
    ).sort_values("mean_absolute_shap_value", ascending=False)

    top_shap_features = shap_importance.head(20).sort_values(
        "mean_absolute_shap_value",
        ascending=True,
    )

    plt.figure(figsize=(10, 8))
    plt.barh(
        top_shap_features["feature"],
        top_shap_features["mean_absolute_shap_value"],
    )
    plt.title("Top 20 SHAP Feature Importances")
    plt.xlabel("Mean absolute SHAP value")
    plt.tight_layout()
    plt.savefig(SHAP_IMPORTANCE_PLOT_PATH, dpi=160)
    plt.close()

    return shap_importance


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n========== Train Vulnerability Priority Classifier ==========")

    dataframe = load_training_data()

    print(f"Training rows: {len(dataframe):,}")
    print("\nTarget distribution:")
    print(dataframe[TARGET_COLUMN].value_counts().to_string())

    features_train, features_test, target_train, target_test = prepare_train_test_split(
        dataframe
    )

    model_pipeline = build_model_pipeline()

    mlflow.set_tracking_uri(MLRUNS_DIR.as_uri())
    mlflow.set_experiment("cyber-risk-priority-classifier")

    with mlflow.start_run(run_name="random_forest_priority_classifier"):
        mlflow.log_param("model_type", "RandomForestClassifier")
        mlflow.log_param("random_state", RANDOM_STATE)
        mlflow.log_param("test_size", TEST_SIZE)
        mlflow.log_param("numeric_features", NUMERIC_FEATURES)
        mlflow.log_param("categorical_features", CATEGORICAL_FEATURES)
        mlflow.log_param("target_column", TARGET_COLUMN)

        model_pipeline.fit(features_train, target_train)

        predictions = model_pipeline.predict(features_test)

        accuracy = accuracy_score(target_test, predictions)
        balanced_accuracy = balanced_accuracy_score(target_test, predictions)
        macro_f1 = f1_score(target_test, predictions, average="macro")
        weighted_f1 = f1_score(target_test, predictions, average="weighted")

        metrics = {
            "training_rows": int(len(features_train)),
            "test_rows": int(len(features_test)),
            "accuracy": round(float(accuracy), 4),
            "balanced_accuracy": round(float(balanced_accuracy), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "classes": sorted(target_train.unique().tolist()),
        }

        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                mlflow.log_metric(metric_name, metric_value)

        save_json(metrics, METRICS_PATH)

        report = classification_report(
            target_test,
            predictions,
            output_dict=True,
            zero_division=0,
        )

        report_dataframe = pd.DataFrame(report).transpose()
        report_dataframe.to_csv(CLASSIFICATION_REPORT_PATH)

        labels = sorted(target_test.unique().tolist())
        confusion_matrix_dataframe = pd.DataFrame(
            confusion_matrix(target_test, predictions, labels=labels),
            index=[f"actual_{label}" for label in labels],
            columns=[f"predicted_{label}" for label in labels],
        )
        confusion_matrix_dataframe.to_csv(CONFUSION_MATRIX_PATH)

        feature_names = get_transformed_feature_names(model_pipeline)

        feature_importance_dataframe = save_feature_importance(
            model_pipeline=model_pipeline,
            feature_names=feature_names,
        )

        shap_importance_dataframe = calculate_shap_importance(
            model_pipeline=model_pipeline,
            features_test=features_test,
            feature_names=feature_names,
        )

        joblib.dump(model_pipeline, MODEL_PATH)

        mlflow.sklearn.log_model(
            sk_model=model_pipeline,
            artifact_path="priority_classifier",
        )

        mlflow.log_artifact(str(METRICS_PATH))
        mlflow.log_artifact(str(CLASSIFICATION_REPORT_PATH))
        mlflow.log_artifact(str(CONFUSION_MATRIX_PATH))
        mlflow.log_artifact(str(FEATURE_IMPORTANCE_PATH))
        mlflow.log_artifact(str(FEATURE_IMPORTANCE_PLOT_PATH))
        mlflow.log_artifact(str(SHAP_IMPORTANCE_PLOT_PATH))

    print("\n========== Model Metrics ==========")
    print(json.dumps(metrics, indent=2))

    print("\nTop 10 model feature importances:")
    print(feature_importance_dataframe.head(10).to_string(index=False))

    print("\nTop 10 SHAP feature importances:")
    print(shap_importance_dataframe.head(10).to_string(index=False))

    print(f"\nSaved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")
    print(f"Saved feature importance plot: {FEATURE_IMPORTANCE_PLOT_PATH}")
    print(f"Saved SHAP importance plot: {SHAP_IMPORTANCE_PLOT_PATH}")
    print(f"MLflow tracking directory: {MLRUNS_DIR}")
    print("\nML training workflow completed successfully.")


if __name__ == "__main__":
    main()