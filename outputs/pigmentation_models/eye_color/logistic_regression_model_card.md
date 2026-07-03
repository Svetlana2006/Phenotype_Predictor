# Eye Color model: logistic_regression

Generated: 2026-07-03T05:47:15.883193Z

## Training Data

data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv

## Target

eye_color

## Metrics

- balanced_accuracy: 1.0000

## Limitations

- Labels derived from HIrisPlex-S webtool predictions (erasmusmc.nl).
- Genotypes: 1000 Genomes Phase 3, 2,504 samples from 5 super-populations.
- Features: 41 HIrisPlex-S SNP dosages (0/1/2 per effect allele).
- Labels represent model predictions, not self-reported phenotypes.
- Performance reflects how well the model replicates HIrisPlex-S.
- Skin color has strong population structure bias — interpret with caution.
