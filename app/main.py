from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="MindUp API")

app.include_router(api_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "MindUp Backend Running"}