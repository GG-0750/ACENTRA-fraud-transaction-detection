from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.notifications import router as notifications_router
from app.api.transactions import router as transactions_router
from app.api.rules import router as rules_router
from app.core.config import get_settings
from app.seed import initialize_database

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(rules_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_event():
    initialize_database()


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
