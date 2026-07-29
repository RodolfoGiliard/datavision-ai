from fastapi import FastAPI
from app.api.v1.api import api_router

app = FastAPI(
    title="DataVision AI API",
    version="0.1.0",
    description="API do DataVision AI - Plataforma Analytics com IA Local"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Health"])
def read_root():
    return {"status": "online", "message": "DataVision AI API rodando com sucesso!"}

