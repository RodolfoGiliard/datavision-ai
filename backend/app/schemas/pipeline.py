from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, description="Nome do pipeline de dados")
    description: Optional[str] = Field(None, max_length=200, description="Descricao opcional do pipeline")
    source_type: str = Field(..., description="Tipo da fonte de dados: csv, postgresql, mysql")
    data_limit: int = Field(default=1000, ge=1, le=100000, description="Limite de linhas para processamento")

class PipelineResponse(PipelineCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

