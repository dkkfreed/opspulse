from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from app.config import get_settings
from app.database import create_tables
from app.api.endpoints import workforce, tickets, analytics, ingestion

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="OpsPulse API",
    description="Workforce and Market Intelligence Platform",
    version=settings.version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting OpsPulse API...")
    create_tables()
    logger.info("Database tables ensured.")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": settings.version, "app": settings.app_name}


app.include_router(workforce.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
