# Document OCR API

FastAPI-based OCR service for extracting text and structured data from identity documents.

## Features

- **Image OCR**: Extract text from images using EasyOCR (supports 80+ languages)
- **PDF OCR**: Extract text from PDFs using OCRmyPDF/Tesseract
- **Document Extraction**: Extract structured fields from ID documents using Claude Haiku Vision
- **API Key Authentication**: Secure endpoints with API key

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth required) |
| `/ocr/image` | POST | Extract raw text from image |
| `/ocr/pdf` | POST | Extract raw text from PDF |
| `/ocr/extract/image` | POST | Extract structured document fields |
| `/docs` | GET | Swagger UI documentation |

## Authentication

All `/ocr/*` endpoints require an API key in the header:

```
X-API-Key: your-api-key-here
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | API key for authentication |
| `ANTHROPIC_API_KEY` | Claude API key for document extraction |

## Local Development

### Prerequisites

- Python 3.11+
- Tesseract OCR installed
- Anthropic API key

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Set Environment Variables

```bash
# Windows PowerShell
$env:API_KEY="your-api-key"
$env:ANTHROPIC_API_KEY="your-anthropic-key"

# Linux/Mac
export API_KEY=your-api-key
export ANTHROPIC_API_KEY=your-anthropic-key
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
docker run -p 8080:8080 \
  -e API_KEY=your-api-key \
  -e ANTHROPIC_API_KEY=your-anthropic-key \
  ocr-api
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
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars API_KEY=your-key,ANTHROPIC_API_KEY=your-key
```

## Usage Examples

### Extract structured fields from ID document

```bash
curl -X POST "http://localhost:8080/ocr/extract/image" \
  -H "X-API-Key: your-api-key" \
  -F "file=@id-card.png"
```

**Response:**
```json
{
  "success": true,
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Michael Doe",
  "document_number": "D12345678",
  "date_of_birth": "01/15/1990",
  "issue_date": "03/20/2020",
  "expiry_date": "03/20/2030",
  "gender": "M",
  "address": "123 Main St, City, State 12345",
  "processing_time_seconds": 1.5
}
```

### Extract raw text from image

```bash
curl -X POST "http://localhost:8080/ocr/image" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.png"
```

### Extract raw text from PDF

```bash
curl -X POST "http://localhost:8080/ocr/pdf" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf"
```

## Required Fields

The `/ocr/extract/image` endpoint validates these required fields:
- `first_name`
- `last_name`
- `document_number`
- `date_of_birth`
- `expiry_date`

If any required field is missing, `success` will be `false` and `missing_fields` will list them.

## Cost

Uses Claude 3 Haiku Vision: ~$0.0005 per document (~$15/month for 1,000 docs/day)

Claude Models
Most Expensive: claude-opus-4-5-20251101
export CLAUDE_VISION_MODEL_MOBILE="claude-sonnet-4-5-20250929"
export CLAUDE_VISION_MODEL_DESKTOP="claude-opus-4-5-20251101"


local deployment
$env:CLAUDE_VISION_MODEL_MOBILE="claude-sonnet-4-20250514"
$env:CLAUDE_VISION_MODEL_DESKTOP="claude-opus-4-5-20251101"
