from fastapi import FastAPI

app = FastAPI(title="DataVision AI API", version="0.1.0")

@app.get("/")
def read_root():
    return {"message": "DataVision AI API funcionando perfeitamente!"}

