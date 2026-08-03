from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.pipeline import Pipeline
from app.schemas.pipeline import PipelineCreate, PipelineResponse
from app.services.ai_service import AIService

router = APIRouter()

@router.post("/", response_model=PipelineResponse, status_code=201)
def create_pipeline(pipeline: PipelineCreate, db: Session = Depends(get_db)):
    db_pipeline = Pipeline(**pipeline.model_dump())
    db.add(db_pipeline)
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline

@router.get("/", response_model=List[PipelineResponse])
def read_pipelines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Pipeline).offset(skip).limit(limit).all()

@router.post("/{pipeline_id}/analyze")
def analyze_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado")
    
    insight = AIService.generate_pipeline_insight(
        pipeline_name=pipeline.name,
        source_type=pipeline.source_type,
        description=pipeline.description or ""
    )
    
    return {
        "pipeline_id": pipeline.id,
        "pipeline_name": pipeline.name,
        "ai_analysis": insight
    }

