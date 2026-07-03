import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report
import os

print("Loading 1KG data for Sparse Ancestry Model...")

# Load the compiled 1KG ancestry table which has all 2500 SNPs
anc_df = pd.read_csv('outputs/igsr_ancestry_table.csv')
y = anc_df['super_population']

# We only want to train on the 41 HIrisPlex features
hirisplex_df = pd.read_csv('data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv')

# Ensure the samples match up by aligning sample_id
# The hirisplex table has an unnamed column 0 for sample names.
hirisplex_df = hirisplex_df.rename(columns={hirisplex_df.columns[0]: 'sample_id'})

merged = pd.merge(anc_df[['sample_id', 'super_population']], hirisplex_df, on='sample_id', how='inner')
y = merged['super_population']
X = merged.drop(columns=['sample_id', 'super_population'])

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print("Training Sparse Ancestry Random Forest on 41 HIrisPlex AIMs...")
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('clf', RandomForestClassifier(n_estimators=300, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1))
])

pipeline.fit(X_train, y_train)

# Evaluate
print("Evaluation on Test Set:")
preds = pipeline.predict(X_test)
print(classification_report(y_test, preds))

# Save the model
os.makedirs('outputs/ancestry_models', exist_ok=True)
joblib.dump(pipeline, 'outputs/ancestry_models/sparse_ancestry.joblib')

# Save the exact feature names used for the sparse model
with open('outputs/ancestry_models/sparse_features.txt', 'w') as f:
    f.write(','.join(X.columns))

print("Saved sparse_ancestry.joblib!")
