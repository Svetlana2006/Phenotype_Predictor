import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.ml_service import get_predictor
from app.schemas.predict import PredictionResponse
from app.core.security import get_current_user
from app.core.database import get_db
from app.db_models.user import User
from app.db_models.prediction import Prediction

router = APIRouter(tags=["Predict"])

@router.post("/predict", response_model=PredictionResponse)
async def predict_phenotypes(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Currently only CSV files are supported.")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        if df.empty:
            raise HTTPException(400, "Uploaded CSV file is empty.")
        
        # Read the first sample in the file
        row = df.iloc[0]
        
        # Extract SNP dosages 
        snp_dosages = {}
        for col in df.columns:
            if col.lower() != "sampleid" and pd.notna(row[col]):
                try:
                    snp_dosages[col] = int(row[col])
                except ValueError:
                    pass
        
        predictor = get_predictor()
        result = predictor.predict(snp_dosages)
        result_dict = result.to_dict()
        
        # Save prediction history to database
        db_prediction = Prediction(
            user_id=current_user.id,
            snps_provided=result.snps_provided,
            result_json=result_dict
        )
        db.add(db_prediction)
        db.commit()
        
        return result_dict
        
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")
