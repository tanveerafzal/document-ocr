import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ocr, health
from app.middleware import RequestLoggingMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build number from environment variable
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "dev")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("#" * 80)
    logger.info(f"#################### BUILD NUMBER: {BUILD_NUMBER} ####################")
    logger.info("#" * 80)
    logger.info(f"OCR API Service starting...")
    logger.info(f"Build: {BUILD_NUMBER}")
    yield
    # Shutdown
    logger.info(f"OCR API Service shutting down (build: {BUILD_NUMBER})")


app = FastAPI(
    title="OCR API",
    description="Extract text from images and PDFs using EasyOCR and OCRmyPDF",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware (only if DATABASE_URL is set)
if os.environ.get("DATABASE_URL"):
    logger.info(f"DATABASE_URL found, enabling request logging middleware")
    app.add_middleware(RequestLoggingMiddleware)
else:
    logger.warning("DATABASE_URL not set - request logging disabled")

app.include_router(health.router)
app.include_router(ocr.router)


@app.get("/")
async def root():
    return {
        "message": "OCR API Service",
        "build": BUILD_NUMBER,
        "docs": "/docs",
        "health": "/health"
    }
