from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR


@dataclass
class TrainResult:
    model_name: str
    metrics: dict[str, float]
    model_path: Path | None = None


def _preprocessor(x: pd.DataFrame) -> ColumnTransformer:
    numeric = list(x.select_dtypes(include=[np.number]).columns)
    categorical = [c for c in x.columns if c not in numeric]
    return ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ]
    )


def train_regressors(
    x: pd.DataFrame,
    y: pd.Series,
    output_dir: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> list[TrainResult]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, random_state=random_state)

    candidates = {
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(n_estimators=200, random_state=random_state, n_jobs=-1),
        "svr": SVR(C=10.0, epsilon=0.1),
    }
    results = []
    for name, estimator in candidates.items():
        pipe = Pipeline([("prep", _preprocessor(x)), ("model", estimator)])
        pipe.fit(x_train, y_train)
        pred = pipe.predict(x_test)
        metrics = {"mae": float(mean_absolute_error(y_test, pred)), "r2": float(r2_score(y_test, pred))}
        path = output_dir / f"{name}.joblib"
        joblib.dump(pipe, path)
        results.append(TrainResult(name, metrics, path))
    return results


def train_classifiers(
    x: pd.DataFrame,
    y: pd.Series,
    output_dir: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> list[TrainResult]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stratify = y if y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=random_state, n_jobs=-1, class_weight="balanced"),
    }
    results = []
    for name, estimator in candidates.items():
        pipe = Pipeline([("prep", _preprocessor(x)), ("model", estimator)])
        pipe.fit(x_train, y_train)
        pred = pipe.predict(x_test)
        metrics = {"balanced_accuracy": float(balanced_accuracy_score(y_test, pred))}
        path = output_dir / f"{name}.joblib"
        joblib.dump(pipe, path)
        results.append(TrainResult(name, metrics, path))
    return results
