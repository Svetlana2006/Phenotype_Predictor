from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db_models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    snps_provided = Column(Integer)
    result_json = Column(JSON) # Store entire ML result as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
