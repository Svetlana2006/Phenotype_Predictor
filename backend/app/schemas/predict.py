from typing import Any, Dict, List
from pydantic import BaseModel

class SinglePrediction(BaseModel):
    sample_id: str
    predictions: Dict[str, Any]
    feature_importances: Dict[str, Dict[str, float]]
    hard_labels: Dict[str, str]
    coverage: Dict[str, Any]
    model_versions: Dict[str, str]
    provenance: Dict[str, str]

class BatchPredictionResponse(BaseModel):
    samples: List[SinglePrediction]
