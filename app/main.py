from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.api.webhooks import clerk as clerk_webhooks

app = FastAPI(title="MindUp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(clerk_webhooks.router, prefix="/api/webhooks", tags=["webhooks"])

@app.get("/")
def health_check():
    return {"status": "MindUp Backend Running"}