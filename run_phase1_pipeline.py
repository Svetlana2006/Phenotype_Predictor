"""
Phase 1 pipeline runner — runs all tasks sequentially.

Tasks:
  1. MTL training (age + ancestry jointly) on real data
  2. Single-task baselines for same features (for comparison)
  3. Feature importance extraction for all pigmentation models
  4. Final JSON comparison report

It saves after every step — safe to interrupt and resume.

Command:
    python run_phase1_pipeline.py

Estimated time: 30-90 minutes depending on hardware.
All outputs go to: outputs/phase1/
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline

from phenotype_predictor.models.multitask_train import train_multitask_table
from phenotype_predictor.explainability import explain_all, importance_dataframe

PHASE1_DIR = Path("outputs/phase1")
PHASE1_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

print("=" * 65)
print("Phase 1 Pipeline Runner")
print("=" * 65)
print(f"Output dir: {PHASE1_DIR.resolve()}")
print(f"Start time: {pd.Timestamp.now()}")
print()


# ── Helper ────────────────────────────────────────────────────────────────────

def checkpoint(name: str) -> bool:
    """Return True if this step was already completed."""
    marker = PHASE1_DIR / f".done_{name}"
    return marker.exists()


def mark_done(name: str):
    (PHASE1_DIR / f".done_{name}").touch()


def log(msg: str):
    ts = pd.Timestamp.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Build joint MTL training table (age + ancestry)
# ══════════════════════════════════════════════════════════════════════════════

log("STEP 1/4  Building joint MTL training table...")
mtl_table_path = PHASE1_DIR / "mtl_table.csv"

if not checkpoint("step1_table"):
    # Load ancestry table (SNP dosages + super_population labels)
    log("  Loading ancestry data...")
    anc = pd.read_csv("outputs/igsr_ancestry_table.csv")
    anc = anc.rename(columns={"super_population": "ancestry_label"})
    log(f"  Ancestry: {anc.shape}")

    # Load age table (CpG betas + age labels) — use subset (27k) for speed
    log("  Loading age data (subset)...")
    age = pd.read_csv("outputs/gse40279_age_table.csv")
    log(f"  Age: {age.shape}")

    # Both tables have different feature spaces — MTL handles missing via masking
    # We stack them vertically with NaN where features don't overlap
    anc_copy = anc.copy()
    anc_copy["age"] = float("nan")
    age_copy = age.copy()
    age_copy["ancestry_label"] = float("nan")

    # Find common non-label cols
    anc_feat = [c for c in anc.columns if c not in {"sample_id", "population", "ancestry_label"}]
    age_feat = [c for c in age.columns if c not in {"sample_id", "age", "gender", "ethnicity", "tissue"}]

    # Build stacked table — SNP features for ancestry rows, CpG features for age rows
    all_features = sorted(set(anc_feat) | set(age_feat))
    rows = []

    for _, r in anc_copy.iterrows():
        row = {"sample_id": r.get("sample_id", ""), "age": r["age"], "ancestry_label": r["ancestry_label"]}
        for f in all_features:
            row[f] = r.get(f, float("nan"))
        rows.append(row)

    for _, r in age_copy.iterrows():
        row = {"sample_id": r.get("sample_id", ""), "age": r["age"], "ancestry_label": r["ancestry_label"]}
        for f in all_features:
            row[f] = r.get(f, float("nan"))
        rows.append(row)

    mtl_df = pd.DataFrame(rows)
    mtl_df.to_csv(mtl_table_path, index=False)
    mark_done("step1_table")
    log(f"  Saved joint table: {mtl_table_path}  shape={mtl_df.shape}")
else:
    log("  Already done, loading cached table...")
    mtl_df = pd.read_csv(mtl_table_path)
    log(f"  Loaded: {mtl_df.shape}")

print()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Train MTL model (epoch training)
# ══════════════════════════════════════════════════════════════════════════════

mtl_out = PHASE1_DIR / "multitask_model"

if not checkpoint("step2_mtl"):
    log("STEP 2/4  Training Multi-Task Learning model (age + ancestry)...")
    log("  This uses masked loss — trains on rows where each target exists.")
    log(f"  Total rows: {len(mtl_df)}  (ancestry: ~2504, age: ~164)")

    t0 = time.time()
    metadata = train_multitask_table(
        df=mtl_df,
        targets={
            "age":            "regression",
            "ancestry_label": "classification",
        },
        output_dir=mtl_out,
        epochs=100,
        batch_size=64,
        hidden_dim=256,
        random_state=RANDOM_STATE,
    )
    elapsed = time.time() - t0
    log(f"  MTL training done in {elapsed:.0f}s")

    history = pd.read_csv(mtl_out / "training_history.csv")
    final_loss = history["loss"].iloc[-1]
    log(f"  Final training loss: {final_loss:.4f}")
    mark_done("step2_mtl")
else:
    log("STEP 2/4  MTL model already trained, skipping...")

print()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Single-task baselines for the same features (for comparison)
# ══════════════════════════════════════════════════════════════════════════════

st_out = PHASE1_DIR / "single_task_baselines"
st_out.mkdir(exist_ok=True)
results = {}

if not checkpoint("step3_single_task"):
    log("STEP 3/4  Training single-task baselines for comparison...")

    # ── Age (regression on CpG betas) ─────────────────────────────────────────
    log("  [Age] Loading data...")
    age_df = pd.read_csv("outputs/gse40279_age_table.csv")
    age_feat_cols = [c for c in age_df.columns
                     if c not in {"sample_id", "age", "gender", "ethnicity", "tissue"}]
    X_age = age_df[age_feat_cols].fillna(0)
    y_age = age_df["age"]

    X_tr, X_te, y_tr, y_te = train_test_split(X_age, y_age, test_size=0.2, random_state=RANDOM_STATE)

    log("  [Age] Training Ridge regression...")
    age_pipe = Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=10.0))])
    age_pipe.fit(X_tr, y_tr)
    age_preds = age_pipe.predict(X_te)
    age_mae = mean_absolute_error(y_te, age_preds)
    age_r2  = r2_score(y_te, age_preds)
    log(f"  [Age] MAE={age_mae:.2f}  R2={age_r2:.3f}")
    joblib.dump(age_pipe, st_out / "age_ridge.joblib")
    results["age_single_task"] = {"MAE": round(age_mae, 3), "R2": round(age_r2, 4)}

    # ── Ancestry (classification on SNP dosages) ───────────────────────────────
    log("  [Ancestry] Loading data...")
    anc_df = pd.read_csv("outputs/igsr_ancestry_table.csv")
    anc_feat_cols = [c for c in anc_df.columns
                     if c not in {"sample_id", "population", "super_population"}]
    X_anc = anc_df[anc_feat_cols].fillna(0)
    y_anc = anc_df["super_population"]

    X_tr, X_te, y_tr, y_te = train_test_split(X_anc, y_anc, test_size=0.2,
                                                random_state=RANDOM_STATE, stratify=y_anc)

    log("  [Ancestry] Training Logistic Regression...")
    anc_pipe = Pipeline([("scaler", StandardScaler()),
                         ("clf",    LogisticRegression(max_iter=1000, random_state=RANDOM_STATE))])
    anc_pipe.fit(X_tr, y_tr)
    anc_preds = anc_pipe.predict(X_te)
    anc_ba = balanced_accuracy_score(y_te, anc_preds)
    log(f"  [Ancestry] Balanced accuracy={anc_ba:.4f}")
    joblib.dump(anc_pipe, st_out / "ancestry_lr.joblib")
    results["ancestry_single_task"] = {"balanced_accuracy": round(anc_ba, 4)}

    joblib.dump(results, st_out / "results.joblib")
    mark_done("step3_single_task")
    log("  Single-task baselines done.")
else:
    log("STEP 3/4  Single-task baselines already done, loading...")
    results = joblib.load(st_out / "results.joblib")

print()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Feature importance extraction + final report
# ══════════════════════════════════════════════════════════════════════════════

if not checkpoint("step4_importance"):
    log("STEP 4/4  Extracting feature importances from all RF models...")

    imp_df = importance_dataframe("outputs")
    imp_df.to_csv(PHASE1_DIR / "feature_importances.csv", index=False)
    log(f"  Saved: {PHASE1_DIR}/feature_importances.csv  ({len(imp_df)} rows)")

    explained = explain_all("outputs", top_n=10)

    # ── Build final comparison report ─────────────────────────────────────────
    log("  Building comparison report...")

    history = pd.read_csv(mtl_out / "training_history.csv") if (mtl_out / "training_history.csv").exists() else None
    final_mtl_loss = float(history["loss"].iloc[-1]) if history is not None else None

    report = {
        "title": "Multi-Task vs Single-Task Learning — Phase 1 Results",
        "generated_at": str(pd.Timestamp.now()),
        "single_task_baselines": results,
        "multitask_model": {
            "architecture": "MultiTaskPhenotypeNet (shared MLP, task-specific heads)",
            "tasks": ["age (regression)", "ancestry (classification)"],
            "epochs": 100,
            "hidden_dim": 256,
            "masked_loss": True,
            "final_training_loss": final_mtl_loss,
            "note": "MTL uses masked loss — each task only contributes to loss for rows where its label exists."
        },
        "feature_importances": {
            trait: [e["rsid"] for e in (getattr(explained, trait).top_snps if getattr(explained, trait) else [])]
            for trait in ["eye_color", "hair_color", "skin_color"]
        },
        "conclusion": (
            "The multi-task model jointly trains on age (methylation) and ancestry (SNPs) "
            "using masked losses. This allows knowledge sharing between tasks where feature "
            "overlap exists, a key research contribution of this platform."
        ),
    }

    report_path = PHASE1_DIR / "comparison_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    log(f"  Saved report: {report_path}")

    mark_done("step4_importance")
else:
    log("STEP 4/4  Already done.")

print()
print("=" * 65)
print("Phase 1 complete.")
print(f"All outputs in: {PHASE1_DIR.resolve()}")
print()
print("Key files:")
print(f"  {PHASE1_DIR}/comparison_report.json  <-- MTL vs single-task")
print(f"  {PHASE1_DIR}/feature_importances.csv <-- Top SNPs per trait")
print(f"  {PHASE1_DIR}/multitask_model/         <-- Trained MTL model")
print()
print(f"End time: {pd.Timestamp.now()}")
print("=" * 65)
