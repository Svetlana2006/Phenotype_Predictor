import io
import traceback
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from ..services.ml_service import get_predictor
from ..schemas.predict import BatchPredictionResponse
from ..core.security import get_current_user
from ..core.database import get_db
from ..db_models.user import User
from ..db_models.prediction import Prediction

router = APIRouter(tags=["Predict"])


@router.post("/predict", response_model=BatchPredictionResponse)
async def predict_phenotypes(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(400, "Currently only CSV files are supported.")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        if df.empty:
            raise HTTPException(400, "Uploaded CSV file is empty.")
        
        # Limit to 50 sequences max per API call to ensure responsiveness
        if len(df) > 50:
            print(f"Limiting {len(df)} rows to 50 for API responsiveness.")
            df = df.head(50)
            
        predictor = get_predictor()
        results_list = []
        
        # Iterate over EVERY row in the CSV (batch processing)
        for index, row in df.iterrows():
            snp_dosages = {}
            for col in df.columns:
                if col.lower() != "sampleid" and pd.notna(row[col]):
                    try:
                        snp_dosages[col] = int(row[col])
                    except ValueError:
                        pass
            
            result = predictor.predict(snp_dosages)
            result_dict = result.to_dict()
            
            # Extract sample ID if provided, otherwise auto-generate
            if "SampleID" in df.columns:
                sample_id = str(row["SampleID"])
            else:
                sample_id = f"Sample_{index+1}"
            
            result_dict["sample_id"] = sample_id
            
            results_list.append(result_dict)
            
            # Save each prediction history to database
            db_prediction = Prediction(
                user_id=current_user.id,
                snps_provided=result.snps_provided,
                result_json=result_dict
            )
            db.add(db_prediction)
            
        db.commit()
        return {"samples": results_list}
        
    except Exception as e:
        traceback.print_exc()
        print(f"Backend Prediction Error: {str(e)}")
        raise HTTPException(500, f"Error processing batch file: {str(e)}")
