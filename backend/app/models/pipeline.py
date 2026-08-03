from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=False)
    data_limit = Column(Integer, default=1000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

