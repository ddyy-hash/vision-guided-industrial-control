# Industrial Control Platform

A full-stack industrial automation demo for conveyor tracking, robot-arm control, device monitoring, and energy-label recognition. The project combines a Flask backend, a Vue 3 control dashboard, WebSocket/MQTT communication, YOLO-based object tracking, and serial-device integration.

## Highlights

- Real-time conveyor and robot-arm control APIs.
- Vue 3 dashboard for equipment status, pipeline control, and energy detection.
- WebSocket updates for tracking frames, device state, and pipeline events.
- YOLO + DeepSORT tracking workflow with a bundled demo model.
- Serial communication support for hardware tests and Windows COM-port diagnostics.
- GitHub-ready project hygiene: ignored local secrets, database files, generated builds, and Python caches.

## Tech Stack

- Frontend: Vue 3, Vite, TypeScript, Element Plus, Pinia, ECharts, Three.js.
- Backend: Flask, Flask-SocketIO, Flask-CORS, PySerial.
- Vision: OpenCV, Ultralytics YOLO, DeepSORT, NumPy, Pillow.
- Messaging: Socket.IO and MQTT.

## Project Layout

```text
industrial-control-platform-2/
  backend/              Flask API, device services, tracking services
  backend/model/        YOLO model and dataset config
  frontend/src/         Vue application source
  public/               Static public assets
  requirements.txt      Python dependencies
  package.json          Frontend dependencies and scripts
  vite.config.ts        Vite build configuration
```

## Quick Start

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Install frontend dependencies:

```bash
npm install
```

3. Create local environment config:

```bash
copy .env.example .env
```

4. Start the backend:

```bash
python backend/app.py
```

5. Start the frontend:

```bash
npm run dev
```

The Vite development server uses `http://localhost:3000` by default. The Flask backend uses `http://localhost:5000`.

## Build

```bash
npm run build
```

The production frontend build is written to `dist/`.

## Repository Notes

- `.env`, local databases, pairing records, `node_modules/`, `dist/`, and Python cache files are intentionally ignored.
- The demo YOLO model at `backend/model/best.pt` is about 18 MB. Keep it in Git only if you want the repository to run out of the box; otherwise move it to a release asset or Git LFS.
- `backend/model/data1.yaml` is a training dataset template. Update `path` before training with your own dataset.

## Intellectual Property Notice

This repository is published for portfolio and technical review purposes. The project includes technology related to pending patent applications. No patent license is granted by making this repository publicly available.

All rights are reserved unless a separate written license is provided.

## Verification

Useful checks before publishing:

```bash
python -m compileall -q backend
npm run build
```
