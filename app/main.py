from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ocr, health

app = FastAPI(
    title="OCR API",
    description="Extract text from images and PDFs using EasyOCR and OCRmyPDF",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ocr.router)


@app.get("/")
async def root():
    return {
        "message": "OCR API Service",
        "docs": "/docs",
        "health": "/health"
    }
