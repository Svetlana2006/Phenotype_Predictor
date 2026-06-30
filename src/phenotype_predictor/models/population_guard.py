from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


@dataclass
class PopulationRisk:
    label: str
    nearest_group: str
    distance: float
    threshold: float

    @property
    def is_out_of_distribution(self) -> bool:
        return self.distance > self.threshold


class PopulationGuard:
    """Simple centroid-distance guard for training-population mismatch."""

    def __init__(self, quantile: float = 0.95):
        self.quantile = quantile
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.centroids: dict[str, np.ndarray] = {}
        self.thresholds: dict[str, float] = {}
        self.feature_names: list[str] = []

    def fit(self, x: pd.DataFrame, groups: pd.Series) -> "PopulationGuard":
        self.feature_names = list(x.columns)
        values = self.scaler.fit_transform(self.imputer.fit_transform(x))
        group_values = pd.Series(groups).reset_index(drop=True)
        for group in sorted(group_values.dropna().unique()):
            idx = group_values == group
            group_matrix = values[idx.to_numpy()]
            centroid = group_matrix.mean(axis=0)
            distances = np.linalg.norm(group_matrix - centroid, axis=1)
            self.centroids[str(group)] = centroid
            self.thresholds[str(group)] = float(np.quantile(distances, self.quantile))
        return self

    def assess(self, x: pd.DataFrame) -> list[PopulationRisk]:
        x = x.reindex(columns=self.feature_names)
        values = self.scaler.transform(self.imputer.transform(x))
        risks = []
        for row in values:
            distances = {group: float(np.linalg.norm(row - centroid)) for group, centroid in self.centroids.items()}
            nearest = min(distances, key=distances.get)
            risks.append(
                PopulationRisk(
                    label="high" if distances[nearest] > self.thresholds[nearest] else "normal",
                    nearest_group=nearest,
                    distance=distances[nearest],
                    threshold=self.thresholds[nearest],
                )
            )
        return risks
