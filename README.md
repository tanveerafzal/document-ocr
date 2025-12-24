# OCR API

FastAPI-based OCR service for extracting text from images and PDFs.

## Features

- **Image OCR**: Extract text from images using EasyOCR (supports 80+ languages)
- **PDF OCR**: Extract text from PDFs using OCRmyPDF/Tesseract
- **JSON Response**: Returns text, confidence scores, bounding boxes, and page info

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ocr/image` | POST | Extract text from image |
| `/ocr/pdf` | POST | Extract text from PDF |
| `/docs` | GET | Swagger UI documentation |

## Local Development

### Prerequisites

- Python 3.11+
- Tesseract OCR installed
- OCRmyPDF installed

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Server

```bash
uvicorn app.main:app --reload
```

## Docker

### Build

```bash
docker build -t ocr-api .
```

### Run

```bash
docker run -p 8080:8080 ocr-api
```

## Deploy to Google Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/ocr-api

# Deploy to Cloud Run
gcloud run deploy ocr-api \
  --image gcr.io/PROJECT_ID/ocr-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

## Usage Examples

### Extract text from image

```bash
curl -X POST "http://localhost:8080/ocr/image" \
  -F "file=@document.png" \
  -F "languages=en"
```

### Extract text from PDF

```bash
curl -X POST "http://localhost:8080/ocr/pdf" \
  -F "file=@document.pdf" \
  -F "force_ocr=false"
```

## Response Format

```json
{
  "success": true,
  "filename": "document.png",
  "file_type": "image",
  "text": "Extracted text here...",
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted text here...",
      "confidence": 0.95,
      "blocks": [
        {
          "text": "Word",
          "confidence": 0.98,
          "bounding_box": {
            "x_min": 10,
            "y_min": 20,
            "x_max": 50,
            "y_max": 40
          }
        }
      ]
    }
  ],
  "processing_time_seconds": 2.34
}
```
