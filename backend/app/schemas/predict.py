from typing import Any, Dict
from pydantic import BaseModel

class PredictionResponse(BaseModel):
    predictions: Dict[str, Any]
    top_snps: Dict[str, float]
    hard_labels: Dict[str, str]
    coverage: Dict[str, Any]
    model_versions: Dict[str, str]
