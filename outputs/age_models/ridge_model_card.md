# Age model: ridge

Generated: 2026-06-30T14:33:12.519196Z

## Training Data

data/raw/gse40279/GSE40279_average_beta_GSM989827-GSM989990.txt.gz

## Target

age

## Metrics

- mae: 7.7135
- r2: 0.5077

## Limitations

- Trained on whole-blood DNA methylation (Illumina 27k array, GSE40279).
- Cohort is ~65% Caucasian-European, ~35% Hispanic-Mexican (ages 19–101).
- Chronological age prediction is tissue-type dependent.
- External validation is required before any forensic interpretation.
