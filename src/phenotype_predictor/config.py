from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MODEL_DIR = PROJECT_ROOT / "models"


@dataclass(frozen=True)
class TaskSpec:
    name: str
    target: str
    kind: str
    metric: str


TASKS = {
    "age": TaskSpec("age", "age", "regression", "mae"),
    "ancestry": TaskSpec("ancestry", "ancestry", "classification", "balanced_accuracy"),
    "eye_color": TaskSpec("eye_color", "eye_color", "classification", "balanced_accuracy"),
    "hair_color": TaskSpec("hair_color", "hair_color", "classification", "balanced_accuracy"),
    "skin_color": TaskSpec("skin_color", "skin_color", "classification", "balanced_accuracy"),
}
