import sys
from pathlib import Path

# Connect the backend to the core ML source code
ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from phenotype_predictor.predictor import PhenotypePredictor

_predictor: PhenotypePredictor | None = None

def get_predictor() -> PhenotypePredictor:
    """Singleton accessor for the loaded ML models to prevent reloading on every request."""
    global _predictor
    if _predictor is None:
        outputs_dir = ROOT_DIR / "outputs"
        print(f"Loading ML models from {outputs_dir}...")
        _predictor = PhenotypePredictor.load(outputs_dir)
        print("Models loaded successfully.")
    return _predictor
