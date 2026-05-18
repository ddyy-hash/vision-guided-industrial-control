# OCR Microservice

This module is a standalone OCR and energy-label recognition service used by the industrial control platform. It provides HTTP endpoints for image OCR, base64 OCR, and energy-label analysis.

## Responsibilities

- Run OCR through a local PaddleOCR-json runtime
- Apply optional YOLO-assisted region extraction before OCR
- Expose FastAPI endpoints for OCR and energy-label detection
- Return debug artifacts for inspection and integration testing

## Layout

```text
ocr_project/
  main.py                 FastAPI entry point
  core/config.py          Runtime path and service configuration
  routers/                OCR and energy-detection API routes
  services/               Image preprocessing and energy-label logic
  ocr_engine/             OCR runtime wrapper and helpers
  models/                 Local YOLO model for energy-label detection
  static/                 UI and sample images
  templates/              Lightweight HTML interface
  requirements.txt        Python dependencies for this module
```

## Runtime Dependency

The repository does not vendor the full `paddleocr_json` runtime directory because it contains large third-party binaries. To run the service locally, place the runtime under:

```text
ocr_project/paddleocr_json/
```

You can also point the service to an external runtime with environment variables:

```text
PADDLEOCR_JSON_DIR
PADDLEOCR_EXE_PATH
PADDLEOCR_MODEL_DIR
```

## Quick Start

```bash
cd ocr_project
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Example Endpoints

- `POST /api/ocr/image`
- `POST /api/ocr/base64`
- `GET /api/ocr/health`
- `POST /api/energy/detect`
