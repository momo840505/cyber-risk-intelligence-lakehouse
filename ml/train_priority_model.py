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
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parents[1]

ANALYTICS_DATABASE_PATH = BASE_DIR / "analytics" / "cyber_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "models"
MLRUNS_DIR = BASE_DIR / "mlruns"

# Renamed from priority_classifier.joblib: the model no longer predicts the
# deterministic priority_level, it predicts exploitation likelihood.
MODEL_PATH = MODELS_DIR / "exploitation_likelihood_classifier.joblib"
METRICS_PATH = REPORTS_DIR / "model_metrics.json"
CLASSIFICATION_REPORT_PATH = REPORTS_DIR / "classification_report.csv"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.csv"
FEATURE_IMPORTANCE_PATH = REPORTS_DIR / "feature_importance.csv"
FEATURE_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "feature_importance.png"
SHAP_IMPORTANCE_PLOT_PATH = REPORTS_DIR / "shap_feature_importance.png"


# ---------------------------------------------------------------------------
# Feature / target design
# ---------------------------------------------------------------------------
#
# WHY THESE FEATURES AND NOT OTHERS
#
# The target is `is_known_exploited`: whether a CVE has appeared on CISA's
# Known Exploited Vulnerabilities (KEV) catalogue. This is a genuinely
# uncertain, forward-looking label -- it is populated by CISA *after*
# real-world exploitation is observed, completely independently of the
# static CVSS/CWE metadata below.
#
# We deliberately EXCLUDE:
#   - risk_score, priority_level  -> these are hand-written deterministic
#     functions of is_known_exploited itself (see
#     src/cyber_risk/etl/build_gold_tables.py). Including them, or anything
#     derived from them, would let the model "predict" the target by
#     algebra instead of learning anything.
#   - epss_score, epss_percentile -> EPSS is FIRST-party's own exploitation
#     -probability model. Using its output as an input feature would just
#     be re-packaging another model's prediction, not a genuine standalone
#     signal, and would make it impossible to tell how much of our accuracy
#     is "borrowed" from EPSS.
#
# What is left is exactly the kind of information a triager has the moment
# a CVE is published, before anyone knows whether it will be exploited:
# CVSS vector components, the weakness category (CWE), and how many
# references / affected products NVD has recorded.

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

TARGET_COLUMN = "is_known_exploited"

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
            reference_count,
            affected_entry_count,
            published_month,
            cvss_base_severity,
            attack_vector,
            attack_complexity,
            privileges_required,
            user_interaction,
            cwe_id,
            is_known_exploited
        from mart_vulnerability_priority
        where cvss_base_score is not null
    """

    with duckdb.connect(str(ANALYTICS_DATABASE_PATH)) as connection:
        dataframe = connection.execute(query).fetchdf()

    if dataframe.empty:
        raise ValueError("Training dataframe is empty.")

    return dataframe


def prepare_train_test_split(dataframe: pd.DataFrame):
    features = dataframe[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    target = dataframe[TARGET_COLUMN].astype(int).copy()

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

    # KEV membership is a rare-event / imbalanced target (most CVEs are
    # never observed being exploited). class_weight="balanced_subsample"
    # keeps the trees from just always predicting the majority class.
    # min_samples_leaf is kept at 1 rather than the more typical 5+: with
    # only ~9 positive examples in a training fold, a higher leaf size
    # makes it structurally impossible for any leaf to specialise in the
    # rare class -- it would always be diluted by majority-class rows.
    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=1,
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
        # Binary classification: index 1 is the "known exploited" class.
        class_index = 1 if len(shap_values) > 1 else 0
        absolute_values = np.abs(shap_values[class_index])
    else:
        shap_array = np.asarray(shap_values)

        if shap_array.ndim == 3:
            # (n_samples, n_features, n_classes) -> take the positive class
            if shap_array.shape[1] == len(feature_names):
                absolute_values = np.abs(shap_array[:, :, -1])
            elif shap_array.shape[2] == len(feature_names):
                absolute_values = np.abs(shap_array[:, -1, :])
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

    print("\n===== Train Exploitation-Likelihood Classifier =====")
    print(
        "Target: is_known_exploited (CISA KEV membership) -- predicted "
        "from static CVSS/CWE metadata ONLY. EPSS score, risk_score and "
        "priority_level are intentionally excluded; see the comment block "
        "at the top of this file for why."
    )

    dataframe = load_training_data()

    print(f"\nTraining rows: {len(dataframe):,}")
    print("\nTarget distribution:")
    print(dataframe[TARGET_COLUMN].value_counts().to_string())

    positive_rate = float(dataframe[TARGET_COLUMN].mean())
    print(f"\nPositive (known exploited) rate: {positive_rate:.4%}")

    features_train, features_test, target_train, target_test = prepare_train_test_split(
        dataframe
    )

    model_pipeline = build_model_pipeline()

    mlflow.set_tracking_uri(MLRUNS_DIR.as_uri())
    mlflow.set_experiment("cyber-risk-exploitation-likelihood-classifier")

    with mlflow.start_run(run_name="random_forest_exploitation_likelihood"):
        mlflow.log_param("model_type", "RandomForestClassifier")
        mlflow.log_param("target_column", TARGET_COLUMN)
        mlflow.log_param("random_state", RANDOM_STATE)
        mlflow.log_param("test_size", TEST_SIZE)
        mlflow.log_param("numeric_features", NUMERIC_FEATURES)
        mlflow.log_param("categorical_features", CATEGORICAL_FEATURES)
        mlflow.log_param("positive_rate", round(positive_rate, 4))

        model_pipeline.fit(features_train, target_train)

        predictions = model_pipeline.predict(features_test)
        predicted_probabilities = model_pipeline.predict_proba(features_test)[:, 1]

        accuracy = accuracy_score(target_test, predictions)
        balanced_accuracy = balanced_accuracy_score(target_test, predictions)
        macro_f1 = f1_score(target_test, predictions, average="macro")
        weighted_f1 = f1_score(target_test, predictions, average="weighted")

        # For a rare positive class, accuracy is close to meaningless (a
        # model that always predicts "not exploited" would already score
        # ~(1 - positive_rate)). ROC-AUC and average precision (area under
        # the precision-recall curve) are the metrics that actually show
        # whether the model separates the two classes.
        roc_auc = roc_auc_score(target_test, predicted_probabilities)
        average_precision = average_precision_score(
            target_test, predicted_probabilities
        )

        baseline_accuracy_if_always_majority_class = float(
            max(target_test.mean(), 1 - target_test.mean())
        )

        metrics = {
            "training_rows": int(len(features_train)),
            "test_rows": int(len(features_test)),
            "positive_rate_train": round(float(target_train.mean()), 4),
            "positive_rate_test": round(float(target_test.mean()), 4),
            "baseline_accuracy_always_majority_class": round(
                baseline_accuracy_if_always_majority_class, 4
            ),
            "accuracy": round(float(accuracy), 4),
            "balanced_accuracy": round(float(balanced_accuracy), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "roc_auc": round(float(roc_auc), 4),
            "average_precision": round(float(average_precision), 4),
            "classes": sorted(target_train.unique().tolist()),
        }

        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                mlflow.log_metric(metric_name, metric_value)

        # A single train/test split evaluates ROC-AUC/average precision on
        # only ~3 positive examples in the held-out set -- with a sample
        # that small, those numbers are close to noise (a different random
        # split could easily swing ROC-AUC from ~0.3 to ~0.7 by luck alone).
        # Stratified k-fold cross-validation pools out-of-fold predictions
        # across all 12 positive examples in the full dataset instead of
        # just the ones in one test split, which is the more statistically
        # honest way to check whether this model has learned anything.
        full_features = dataframe[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        full_target = dataframe[TARGET_COLUMN].astype(int)

        cv_splitter = StratifiedKFold(
            n_splits=5, shuffle=True, random_state=RANDOM_STATE
        )
        cv_probabilities = cross_val_predict(
            build_model_pipeline(),
            full_features,
            full_target,
            cv=cv_splitter,
            method="predict_proba",
            n_jobs=-1,
        )[:, 1]

        metrics["cv_folds"] = cv_splitter.get_n_splits()
        metrics["cv_roc_auc_out_of_fold"] = round(
            float(roc_auc_score(full_target, cv_probabilities)), 4
        )
        metrics["cv_average_precision_out_of_fold"] = round(
            float(average_precision_score(full_target, cv_probabilities)), 4
        )

        mlflow.log_metric("cv_roc_auc_out_of_fold", metrics["cv_roc_auc_out_of_fold"])
        mlflow.log_metric(
            "cv_average_precision_out_of_fold",
            metrics["cv_average_precision_out_of_fold"],
        )

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
            artifact_path="exploitation_likelihood_classifier",
        )

        mlflow.log_artifact(str(METRICS_PATH))
        mlflow.log_artifact(str(CLASSIFICATION_REPORT_PATH))
        mlflow.log_artifact(str(CONFUSION_MATRIX_PATH))
        mlflow.log_artifact(str(FEATURE_IMPORTANCE_PATH))
        mlflow.log_artifact(str(FEATURE_IMPORTANCE_PLOT_PATH))
        mlflow.log_artifact(str(SHAP_IMPORTANCE_PLOT_PATH))

    print("\n===== Model Metrics =====")
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
