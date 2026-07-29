from fastapi import FastAPI, status
from datetime import datetime
from app.schemas.pipeline import PipelineCreate, PipelineResponse

app = FastAPI(title="DataVision AI API", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "DataVision AI API funcionando perfeitamente!"}

@app.post("/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(pipeline: PipelineCreate):
    fake_db_pipeline = {
        "id": 1,
        "name": pipeline.name,
        "description": pipeline.description,
        "source_type": pipeline.source_type,
        "data_limit": pipeline.data_limit,
        "created_at": datetime.now()
    }
    return fake_db_pipeline

