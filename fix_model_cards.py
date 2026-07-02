"""Write the missing model cards for the 3 real age models already in outputs/age_models/."""
import sys
sys.path.insert(0, "src")

import joblib
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from phenotype_predictor.reporting import write_model_card

df = pd.read_csv("outputs/gse40279_age_table.csv")
drop_cols = [c for c in ["sample_id", "gender", "ethnicity", "tissue"] if c in df.columns]
feat = df.drop(columns=drop_cols)
X = feat.drop(columns=["age"])
y = feat["age"]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

print("Writing model cards for real age models...")
for name in ["ridge", "random_forest", "svr"]:
    model_path = Path("outputs/age_models") / (name + ".joblib")
    m = joblib.load(model_path)
    pred = m.predict(X_te)
    metrics = {
        "mae": float(mean_absolute_error(y_te, pred)),
        "r2":  float(r2_score(y_te, pred)),
    }
    card_path = Path("outputs/age_models") / (name + "_model_card.md")
    write_model_card(
        card_path,
        "Age model: " + name,
        "data/raw/gse40279/GSE40279_average_beta_GSM989827-GSM989990.txt.gz",
        "age",
        metrics,
        [
            "Trained on whole-blood DNA methylation (Illumina 27k array, GSE40279).",
            "Cohort: 164 samples, ~65% Caucasian-European, ~35% Hispanic-Mexican, ages 28-101.",
            "Feature set: 5,000 CpG sites (subset of full 27k array).",
            "Chronological age prediction is tissue-type dependent.",
            "External validation required before any forensic or clinical interpretation.",
        ],
    )
    print("  " + name + "  MAE=" + str(round(metrics["mae"], 2)) + " yrs  R2=" + str(round(metrics["r2"], 4)) + "  -> card written")

print()
print("All 3 model cards saved to outputs/age_models/")
