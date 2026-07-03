# Phenotype Predictor API Documentation

The REST API is built with FastAPI and runs on `http://127.0.0.1:8000`.

## 1. Predictions

### `POST /api/v1/predict/raw`
Submit a raw, unaligned DNA sequence string to be processed by the biological extraction engine and the machine learning inference models.

**Headers:**
*   `Authorization`: `Bearer <token>`
*   `Content-Type`: `application/json`

**Request Body:**
```json
{
  "sequence": "GCTGGCCCTGGGGCTGTGCTCTTCACCCTGATCTTCGTGTCCGTGTACCGCGTGTTC..."
}
```

**Response:** `200 OK`
```json
{
  "samples": [
    {
      "sample_id": "seq_1",
      "predictions": {
        "age": {
          "estimate": null,
          "confidence_interval": null
        }
      },
      "hard_labels": {
        "eye_color": "Brown",
        "hair_color": "Black",
        "skin_color": "Dark",
        "ancestry": "EUR"
      },
      "confidence": {
        "eye_color": 0.89,
        "hair_color": 0.92,
        "skin_color": 0.81,
        "ancestry": 0.99
      },
      "coverage": {
        "snps_provided": 41,
        "snps_used": 41,
        "snps_missing": []
      },
      "feature_importances": {
        "eye_color": {
          "rs12913832_A": 0.45,
          "rs16891982_G": 0.12
        }
      },
      "model_versions": {
        "eye_color": "1.0-RF",
        "ancestry": "1.0-RF"
      },
      "provenance": {
        "timestamp": "2026-07-03 14:38:00 UTC",
        "software_version": "1.0.0",
        "git_commit": "8f4d2ab",
        "training_dataset": "HIrisPlex-2025"
      }
    }
  ]
}
```

---

## 2. Case Management (Phase 2 - Planned)

### `GET /api/v1/cases`
Retrieves all cases assigned to the authenticated investigator.

**Headers:**
*   `Authorization`: `Bearer <token>`

**Response:** `200 OK`
```json
[
  {
    "id": "case_26_0147",
    "name": "Case 26-0147",
    "created_at": "2026-07-03T12:00:00Z",
    "status": "Open",
    "predictions_count": 2
  }
]
```

### `POST /api/v1/cases/{case_id}/upload`
Uploads a `.vcf` or `.csv` evidence file directly into a case folder for batch analysis.

**Headers:**
*   `Authorization`: `Bearer <token>`
*   `Content-Type`: `multipart/form-data`

**Form Data:**
*   `file`: The `.vcf` file object.

**Response:** `202 Accepted`
```json
{
  "message": "File accepted for processing. Analysis job started.",
  "job_id": "job_94819"
}
```
