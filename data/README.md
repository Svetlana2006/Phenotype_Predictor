# Data Directory

Large public datasets should not be committed here.

Recommended layout:

```text
data/
  raw/
    gse40279/
    igsr/
    pgp/
  processed/
    age/
    ancestry/
    multitask/
  external/
    hirisplex/
```

Use `sample_id` as the join key whenever combining genotype and phenotype tables.
