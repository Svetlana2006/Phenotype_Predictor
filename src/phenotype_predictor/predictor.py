"""
Unified PhenotypePredictor — the Fusion Engine (Module 4).

Loads all trained models at startup and runs every phenotype prediction
on a single input sample in one call. This is the core class that the
FastAPI backend and CLI both wrap.

Usage:
    from phenotype_predictor.predictor import PhenotypePredictor

    predictor = PhenotypePredictor.load("outputs/")
    result = predictor.predict(snp_dosages={"rs12913832": 2, "rs1426654": 0, ...})
    print(result.eye_color)   # {"blue": 0.92, "brown": 0.08, ...}
    print(result.confidence)  # {"eye_color": 0.92, "hair_color": 0.87, ...}
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS
from phenotype_predictor.explainability import get_feature_importances

# Configure professional logger for the PhenotypePredictor engine
logger = logging.getLogger("PhenotypePredictor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class PhenotypeResult:
    """Full prediction result for one sample."""

    # Probabilities per class (dict of label -> probability)
    eye_color:  dict[str, float] = field(default_factory=dict)
    hair_color: dict[str, float] = field(default_factory=dict)
    skin_color: dict[str, float] = field(default_factory=dict)
    ancestry:   dict[str, float] = field(default_factory=dict)

    # Age prediction (regression)
    age_estimate: Optional[float] = None
    age_range:    Optional[tuple[float, float]] = None  # (lo, hi) 80% interval

    # Feature Importances (Top SNPs) driving the prediction for each trait
    feature_importances: dict[str, dict[str, float]] = field(default_factory=dict)

    # Per-trait confidence = max probability
    confidence: dict[str, float] = field(default_factory=dict)

    # SNP coverage info
    snps_provided: int = 0
    snps_used:     int = 0
    snps_missing:  list[str] = field(default_factory=list)

    # Model versions used
    model_versions: dict[str, str] = field(default_factory=dict)

    def hard_labels(self) -> dict[str, str]:
        """Return the single best-guess label per trait."""
        out: dict[str, str] = {}
        for trait, probs in {
            "eye_color":  self.eye_color,
            "hair_color": self.hair_color,
            "skin_color": self.skin_color,
            "ancestry":   self.ancestry,
        }.items():
            if probs:
                out[trait] = max(probs, key=probs.get)
        if self.age_estimate is not None:
            out["age"] = str(round(self.age_estimate, 1))
        return out

    def to_dict(self) -> dict:
        return {
            "predictions": {
                "eye_color":  {"probabilities": self.eye_color,  "confidence": self.confidence.get("eye_color"), "feature_importances": self.feature_importances.get("eye_color", {})},
                "hair_color": {"probabilities": self.hair_color, "confidence": self.confidence.get("hair_color"), "feature_importances": self.feature_importances.get("hair_color", {})},
                "skin_color": {"probabilities": self.skin_color, "confidence": self.confidence.get("skin_color"), "feature_importances": self.feature_importances.get("skin_color", {})},
                "ancestry":   {"probabilities": self.ancestry,   "confidence": self.confidence.get("ancestry"), "feature_importances": self.feature_importances.get("ancestry", {})},
                "age": {
                    "estimate": self.age_estimate,
                    "range":    list(self.age_range) if self.age_range else None,
                },
            },
            "feature_importances": self.feature_importances,
            "hard_labels":   self.hard_labels(),
            "coverage": {
                "snps_provided": self.snps_provided,
                "snps_used":     self.snps_used,
                "snps_missing":  self.snps_missing,
            },
            "model_versions": self.model_versions,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ── Main predictor class ──────────────────────────────────────────────────────

class PhenotypePredictor:
    """
    Fusion Engine: loads all trained models and predicts all phenotypes
    from a single SNP dosage dictionary.

    Parameters
    ----------
    models_dir : Path
        Root outputs directory containing age_models/, ancestry_models/,
        pigmentation_models/ subdirectories.
    model_variant : str
        Which model to use for each trait, e.g. "logistic_regression"
        or "random_forest". Defaults to "logistic_regression" (best for
        most traits).
    """

    VERSION = "1.0.0"

    _PIGMENTATION_FEATURES = [m.feature_name for m in HIRISPLEX_S_MARKERS]

    _ANCESTRY_FEATURES: list[str] = []   # loaded from saved column list

    def __init__(
        self,
        eye_model,
        hair_model,
        skin_model,
        ancestry_model,
        sparse_ancestry_model,
        age_model,
        ancestry_features: list[str],
        sparse_ancestry_features: list[str],
        age_features: list[str],
        model_variant: str = "logistic_regression",
    ):
        self._eye      = eye_model
        self._hair     = hair_model
        self._skin     = skin_model
        self._ancestry = ancestry_model
        self._sparse_ancestry = sparse_ancestry_model
        self._age      = age_model
        self._ancestry_features = ancestry_features
        self._sparse_ancestry_features = sparse_ancestry_features
        self._age_features      = age_features
        self._variant           = model_variant

    @classmethod
    def load(
        cls,
        outputs_dir: str | Path = "outputs",
        model_variant: str = "logistic_regression",
    ) -> "PhenotypePredictor":
        """
        Load all models from the outputs directory structure.

        Expected layout:
            outputs/
              pigmentation_models/eye_color/logistic_regression.joblib
              pigmentation_models/hair_color/logistic_regression.joblib
              pigmentation_models/skin_color/logistic_regression.joblib
              ancestry_models/logistic_regression.joblib
              age_models/ridge.joblib
        """
        base = Path(outputs_dir)

        def _load(path: Path):
            if not path.exists():
                raise FileNotFoundError(f"Model not found: {path}")
            return joblib.load(path)

        pig = base / "pigmentation_models"
        eye_model      = _load(pig / "eye_color"  / f"{model_variant}_v1.0.joblib")
        hair_model     = _load(pig / "hair_color" / f"{model_variant}_v1.0.joblib")
        skin_model     = _load(pig / "skin_color" / f"{model_variant}_v1.0.joblib")
        ancestry_model = _load(base / "ancestry_models" / f"{model_variant}_v1.0.joblib")
        sparse_ancestry_model = _load(base / "ancestry_models" / "sparse_ancestry_v1.0.joblib")
        age_model      = _load(base / "age_models" / "ridge_v1.0.joblib")

        # Load ancestry feature list (saved alongside the ancestry table)
        anc_table  = base / "igsr_ancestry_table.csv"
        anc_df     = pd.read_csv(anc_table, nrows=0)
        drop = {"sample_id", "population", "super_population"}
        ancestry_features = [c for c in anc_df.columns if c not in drop]
        
        # Load sparse ancestry features
        with open(base / "ancestry_models" / "sparse_features.txt") as f:
            sparse_ancestry_features = f.read().strip().split(',')

        # Age features = all columns except metadata
        age_table = base / "gse40279_age_table.csv"
        age_df    = pd.read_csv(age_table, nrows=0)
        age_drop  = {"sample_id", "age", "gender", "ethnicity", "tissue"}
        age_features = [c for c in age_df.columns if c not in age_drop]

        return cls(
            eye_model=eye_model,
            hair_model=hair_model,
            skin_model=skin_model,
            ancestry_model=ancestry_model,
            sparse_ancestry_model=sparse_ancestry_model,
            age_model=age_model,
            ancestry_features=ancestry_features,
            sparse_ancestry_features=sparse_ancestry_features,
            age_features=age_features,
            model_variant=model_variant,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_pig_vector(self, snp_dosages: dict[str, int]) -> pd.DataFrame:
        """
        Build a 1-row DataFrame of HIrisPlex dosage features from raw dosages.
        Missing SNPs are left as NaN to trigger pipeline median imputation.
        """
        row = {}
        for marker in HIRISPLEX_S_MARKERS:
            # Accept both rsID_Allele format and plain rsID
            val = snp_dosages.get(marker.feature_name,
                  snp_dosages.get(marker.rsid, None))
            row[marker.feature_name] = int(val) if val is not None else float('nan')
        return pd.DataFrame([row])

    def _make_ancestry_vector(self, snp_dosages: dict[str, int], sparse: bool = False) -> pd.DataFrame:
        features = self._sparse_ancestry_features if sparse else self._ancestry_features
        row = {f: snp_dosages.get(f, snp_dosages.get(f.split("_")[0], float('nan')))
               for f in features}
        return pd.DataFrame([row])

    @staticmethod
    def _proba_dict(pipeline, X: pd.DataFrame) -> dict[str, float]:
        proba = pipeline.predict_proba(X)[0]
        classes = pipeline.classes_
        return {str(c): round(float(p), 4) for c, p in zip(classes, proba)}

    # ── Public predict method ─────────────────────────────────────────────────

    def predict(
        self,
        snp_dosages: dict[str, int | float],
        methylation_betas: Optional[dict[str, float]] = None,
    ) -> PhenotypeResult:
        """
        Run all phenotype models on a single sample.

        Parameters
        ----------
        snp_dosages : dict
            Mapping of rsID (or rsID_Allele) -> dosage (0/1/2).
            Missing SNPs default to 0 (homozygous ref).
        methylation_betas : dict, optional
            CpG site -> beta value (0-1). Required for age prediction.
            If None, age prediction is skipped.

        Returns
        -------
        PhenotypeResult with all predictions populated.
        """
        result = PhenotypeResult()
        result.model_versions = {
            "eye_color":  self.VERSION,
            "hair_color": self.VERSION,
            "skin_color": self.VERSION,
            "ancestry":   self.VERSION,
            "age":        self.VERSION,
        }

        # ── Coverage analysis ─────────────────────────────────────────────────
        snps_count = len(snp_dosages)
        result.snps_provided = snps_count
        logger.info(f"Starting prediction pipeline. SNPs provided: {snps_count}")

        all_pig_rsids = {m.rsid for m in HIRISPLEX_S_MARKERS}
        all_pig_feat  = {m.feature_name for m in HIRISPLEX_S_MARKERS}
        provided = set(snp_dosages.keys())
        used     = provided & (all_pig_rsids | all_pig_feat)
        missing  = all_pig_rsids - {k.split("_")[0] for k in provided}

        result.snps_used     = len(used)
        result.snps_missing  = sorted(missing)

        # ── Pigmentation predictions ──────────────────────────────────────────
        X_pig = self._make_pig_vector(snp_dosages)

        eye_probs  = self._proba_dict(self._eye,  X_pig)
        hair_probs = self._proba_dict(self._hair, X_pig)
        skin_probs = self._proba_dict(self._skin, X_pig)

        result.eye_color  = eye_probs
        result.hair_color = hair_probs
        result.skin_color = skin_probs

        result.confidence["eye_color"]  = max(eye_probs.values())
        result.confidence["hair_color"] = max(hair_probs.values())
        result.confidence["skin_color"] = max(skin_probs.values())
        
        # Calculate Explainability for Pigmentation
        pig_features = X_pig.columns.tolist()
        result.feature_importances["eye_color"] = get_feature_importances(self._eye, pig_features)
        result.feature_importances["hair_color"] = get_feature_importances(self._hair, pig_features)
        result.feature_importances["skin_color"] = get_feature_importances(self._skin, pig_features)

        # ── Ancestry prediction ───────────────────────────────────────────────
        try:
            # Dynamically select the robust ancestry model based on data density
            sparse_mode = snps_count < 100
            
            if sparse_mode:
                logger.warning(f"Sparse DNA detected ({snps_count} SNPs). Activating HIrisPlex fallback model.")
            
            X_anc = self._make_ancestry_vector(snp_dosages, sparse=sparse_mode)
            model_to_use = self._sparse_ancestry if sparse_mode else self._ancestry
            
            anc_probs = self._proba_dict(model_to_use, X_anc)
            result.ancestry = anc_probs
            result.confidence["ancestry"] = max(anc_probs.values())
            
            # Calculate Explainability for Ancestry
            anc_features = X_anc.columns.tolist()
            result.feature_importances["ancestry"] = get_feature_importances(model_to_use, anc_features)
        except Exception:
            result.ancestry = {}

        # ── Age prediction (requires methylation data) ────────────────────────
        if methylation_betas is not None:
            try:
                age_row = {f: methylation_betas.get(f, float("nan"))
                           for f in self._age_features}
                X_age = pd.DataFrame([age_row])
                age_pred = float(self._age.predict(X_age)[0])
                result.age_estimate = round(age_pred, 1)
                # Simple ±10yr range (replace with calibrated interval later)
                result.age_range = (max(0, age_pred - 10), age_pred + 10)
            except Exception:
                pass

        return result

    # ── Convenience: predict from file ───────────────────────────────────────

    def predict_from_csv(self, csv_path: str | Path) -> PhenotypeResult:
        """
        Predict from a CSV file with columns: SampleID, rs*_Allele, ...

        The file should be in the same format as hirisplex_webtool_input.csv.
        Only the first sample row is used.
        """
        df = pd.read_csv(Path(csv_path))
        if df.empty:
            raise ValueError("CSV file is empty.")
        row = df.iloc[0]
        snp_dosages = {col: int(row[col]) for col in df.columns
                       if col != "SampleID" and col in row and pd.notna(row[col])}
        return self.predict(snp_dosages)

    def __repr__(self) -> str:
        return (
            f"PhenotypePredictor(version={self.VERSION}, "
            f"variant={self._variant}, "
            f"traits=[eye, hair, skin, ancestry, age])"
        )
