from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from app.api import predict, auth
from app.services.ml_service import get_predictor
from app.core.database import engine
from app.db_models.base import Base
# Import models to ensure they register with SQLAlchemy Base
import app.db_models.user
import app.db_models.prediction

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create database tables
    print("Setting up database...")
    Base.metadata.create_all(bind=engine)
    
    # Load all 10 ML models directly into memory on startup
    print("Initializing PhenotypePredictor ML Engine...")
    get_predictor()
    yield
    print("Shutting down...")

app = FastAPI(title="Phenotype Predictor API", lifespan=lifespan)

# Allow frontend Next.js app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(predict.router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "healthy", "models_loaded": get_predictor() is not None}
