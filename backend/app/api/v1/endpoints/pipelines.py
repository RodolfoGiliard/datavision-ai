from fastapi import APIRouter, status
from datetime import datetime
from app.schemas.pipeline import PipelineCreate, PipelineResponse

router = APIRouter()

@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
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

