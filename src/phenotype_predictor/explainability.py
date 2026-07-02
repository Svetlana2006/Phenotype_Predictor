"""
Explainability module — feature importance per phenotype prediction.

Provides:
  - get_top_snps()       : top-N SNPs by RF feature importance (no SHAP needed)
  - get_importance_table(): full importance table as DataFrame
  - ExplainedPrediction  : result dataclass with importances per trait

This is Module 6 of the platform (the "Why?" panel).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class TraitImportance:
    """Feature importances for one trait."""
    trait: str
    top_snps: list[dict]          # [{"rsid": ..., "gene": ..., "importance": ...}]
    all_importances: dict[str, float]  # feature_name -> importance score

    def to_dict(self) -> dict:
        return {
            "trait": self.trait,
            "top_snps": self.top_snps,
        }


@dataclass
class ExplainedPrediction:
    """Full explainability result for all traits."""
    eye_color:  Optional[TraitImportance] = None
    hair_color: Optional[TraitImportance] = None
    skin_color: Optional[TraitImportance] = None
    ancestry:   Optional[TraitImportance] = None

    def to_dict(self) -> dict:
        return {
            trait: imp.to_dict()
            for trait, imp in {
                "eye_color":  self.eye_color,
                "hair_color": self.hair_color,
                "skin_color": self.skin_color,
                "ancestry":   self.ancestry,
            }.items()
            if imp is not None
        }


# ── Core functions ────────────────────────────────────────────────────────────

def get_feature_importances(
    model_path: str | Path,
    feature_names: list[str],
    top_n: int = 10,
    gene_map: Optional[dict[str, str]] = None,
) -> TraitImportance:
    """
    Load a RandomForest model and extract feature importances.

    Parameters
    ----------
    model_path : path to .joblib model file
    feature_names : ordered list of feature column names
    top_n : how many top features to return
    gene_map : optional dict of feature_name -> gene name for display

    Returns
    -------
    TraitImportance with top_n most important SNPs
    """
    pipe = joblib.load(Path(model_path))

    # Navigate through Pipeline to get the RF estimator
    if hasattr(pipe, "named_steps"):
        # Find the step that has feature_importances_
        estimator = None
        for name, step in pipe.named_steps.items():
            if hasattr(step, "feature_importances_"):
                estimator = step
                break
        if estimator is None:
            raise ValueError(f"No RandomForest found in pipeline: {model_path}")
    elif hasattr(pipe, "feature_importances_"):
        estimator = pipe
    else:
        raise ValueError(f"Model at {model_path} has no feature_importances_")

    importances = estimator.feature_importances_
    n = min(len(importances), len(feature_names))
    importances = importances[:n]
    feature_names = feature_names[:n]

    # Sort by importance descending
    sorted_idx = np.argsort(importances)[::-1]
    all_imp = {feature_names[i]: round(float(importances[i]), 6)
               for i in sorted_idx}

    # Build top-N list
    top_list = []
    for i in sorted_idx[:top_n]:
        fname = feature_names[i]
        rsid  = fname.rsplit("_", 1)[0] if "_" in fname else fname
        entry = {
            "feature":    fname,
            "rsid":       rsid,
            "importance": round(float(importances[i]), 6),
            "importance_pct": round(float(importances[i]) * 100, 2),
        }
        if gene_map and rsid in gene_map:
            entry["gene"] = gene_map[rsid]
        top_list.append(entry)

    # Get trait name from path
    trait = Path(model_path).parent.name

    return TraitImportance(
        trait=trait,
        top_snps=top_list,
        all_importances=all_imp,
    )


def get_hirisplex_gene_map() -> dict[str, str]:
    """Return rsID -> gene name map for all HIrisPlex-S markers."""
    return {m.rsid: m.gene for m in HIRISPLEX_S_MARKERS}


def explain_all(
    outputs_dir: str | Path = "outputs",
    top_n: int = 10,
) -> ExplainedPrediction:
    """
    Load all RF pigmentation models and extract feature importances.

    Parameters
    ----------
    outputs_dir : root outputs directory
    top_n : number of top SNPs to return per trait

    Returns
    -------
    ExplainedPrediction with importances for all traits
    """
    base     = Path(outputs_dir)
    pig_dir  = base / "pigmentation_models"
    features = [m.feature_name for m in HIRISPLEX_S_MARKERS]
    gene_map = get_hirisplex_gene_map()

    result = ExplainedPrediction()

    for trait_attr, trait_dir_name in [
        ("eye_color",  "eye_color"),
        ("hair_color", "hair_color"),
        ("skin_color", "skin_color"),
    ]:
        model_path = pig_dir / trait_dir_name / "random_forest.joblib"
        if model_path.exists():
            try:
                imp = get_feature_importances(model_path, features, top_n, gene_map)
                setattr(result, trait_attr, imp)
            except Exception as e:
                print(f"  Warning: could not load importances for {trait_dir_name}: {e}")

    return result


def importance_dataframe(outputs_dir: str | Path = "outputs") -> pd.DataFrame:
    """
    Return a tidy DataFrame of all SNP importances across all traits.
    Useful for generating heatmaps and comparison tables.

    Columns: trait, rsid, feature, gene, importance, importance_pct
    """
    explained = explain_all(outputs_dir)
    rows = []
    for trait_attr in ["eye_color", "hair_color", "skin_color"]:
        imp: Optional[TraitImportance] = getattr(explained, trait_attr)
        if imp is None:
            continue
        for entry in imp.top_snps:
            rows.append({
                "trait":          trait_attr,
                "rsid":           entry["rsid"],
                "feature":        entry["feature"],
                "gene":           entry.get("gene", ""),
                "importance":     entry["importance"],
                "importance_pct": entry["importance_pct"],
            })
    return pd.DataFrame(rows)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys

    outputs = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    top_n   = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Loading feature importances from {outputs}/ (top {top_n} SNPs per trait)...\n")
    result = explain_all(outputs, top_n=top_n)

    for trait_attr in ["eye_color", "hair_color", "skin_color"]:
        imp: Optional[TraitImportance] = getattr(result, trait_attr)
        if imp is None:
            print(f"{trait_attr}: model not found\n")
            continue
        print(f"{'='*50}")
        print(f"Trait: {trait_attr}")
        print(f"{'='*50}")
        for entry in imp.top_snps:
            gene = f"  [{entry.get('gene','')}]" if entry.get("gene") else ""
            print(f"  {entry['rsid']:<15}  {entry['importance_pct']:6.2f}%{gene}")
        print()

    # Save full table
    df = importance_dataframe(outputs)
    out_path = Path(outputs) / "feature_importances.csv"
    df.to_csv(out_path, index=False)
    print(f"Full importance table saved: {out_path}")
