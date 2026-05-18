# Vision-Guided Industrial Control Platform

An industrial automation showcase project that integrates a Vue 3 control dashboard, a Flask backend, YOLO-based visual tracking, robot-arm control, conveyor automation, and PLC or Arduino-assisted hardware coordination.

This repository is organized as a portfolio-ready project for CV and technical review. In addition to the runnable codebase, it includes demo media, exported presentation slides, Arduino firmware, and reference documents that show the hardware setup and system outcomes.

## Demo And Showcase Assets

- Full demo video: [docs/media/demo_video.mp4](docs/media/demo_video.mp4)
- Embedded presentation clip: [docs/media/presentation_clip.mp4](docs/media/presentation_clip.mp4)
- Competition paper PDF: [docs/reference/competition-paper.pdf](docs/reference/competition-paper.pdf)
- Competition paper DOCX: [docs/reference/competition-paper.docx](docs/reference/competition-paper.docx)
- Conveyor firmware: [hardware/arduino/belt/belt.ino](hardware/arduino/belt/belt.ino)
- Robot-arm firmware: [hardware/arduino/robot_arm/robotarm0724.ino](hardware/arduino/robot_arm/robotarm0724.ino)

## Project Snapshot

- Real-time visual tracking with YOLO and DeepSORT for object localization and motion continuity.
- Conveyor and robot-arm coordination through backend APIs and hardware control modules.
- PLC-centered system orchestration with Arduino-based device control for selected hardware components.
- Energy-label recognition workflow for industrial inspection scenarios.
- Portfolio assets bundled into the repository, including diagrams, presentation slides, firmware, and demo videos.

## Visual Preview

### Project Cover

![Project cover](docs/media/slides/slide-01-cover.png)

### Cross-Domain System Integration

![System integration slide](docs/media/slides/slide-05-system-integration.png)

### End-To-End Workflow

![Workflow slide](docs/media/slides/slide-06-workflow.png)

### Hardware And Results

![Results slide](docs/media/slides/slide-13-results.png)

### PLC And Hardware Selection

![Hardware selection slide](docs/media/slides/slide-15-hardware-selection.png)

### Overall Architecture

![Architecture slide](docs/media/slides/slide-19-architecture.png)

## Technical Scope

### Software

- Frontend: Vue 3, TypeScript, Vite, Element Plus, Pinia, ECharts, Three.js
- Backend: Flask, Flask-SocketIO, Flask-CORS, PySerial
- Vision: OpenCV, Ultralytics YOLO, DeepSORT, NumPy, Pillow
- Messaging: Socket.IO and MQTT

### Hardware

- XINJE PLC-based conveyor control workflow
- Arduino firmware for conveyor and robot-arm control
- Serial communication for robotic actuators and industrial peripherals
- Camera-based inspection and tracking pipeline

## Repository Structure

```text
industrial-control-platform-2/
  backend/                     Flask APIs, device services, tracking services
  frontend/src/                Vue application source
  backend/model/               Demo model and dataset template
  hardware/arduino/            Arduino firmware used by the project
  docs/media/                  Demo videos and exported presentation slides
  docs/reference/              Competition paper and supporting material
  RUN_GUIDE.md                 Runtime setup notes
  MQTT_INSTALLATION_GUIDE.md   MQTT setup notes
  PROJECT_DEPENDENCIES.md      Dependency overview
```

## Quick Start

1. Install Python dependencies.

```bash
pip install -r requirements.txt
```

2. Install frontend dependencies.

```bash
npm install
```

3. Create the local environment file.

```bash
copy .env.example .env
```

4. Start the backend service.

```bash
python backend/app.py
```

5. Start the frontend.

```bash
npm run dev
```

The default local endpoints are:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`

## Build And Verification

Useful commands before publishing or demoing the project:

```bash
python -m compileall -q backend
npm run build
npm audit --audit-level=moderate
```

## Additional Notes

- Local secrets, databases, caches, `node_modules`, and production builds are intentionally ignored.
- The bundled YOLO model at `backend/model/best.pt` is kept in the repository so the project can be reviewed and demoed more easily.
- The original competition slide deck is not committed because the raw `.pptx` exceeds GitHub's single-file limit. Exported slide images and the competition paper are included instead.

## Intellectual Property Notice

This repository is published for portfolio and technical review purposes. The project includes technology related to pending patent applications. No patent license is granted by making this repository publicly available.

All rights are reserved unless a separate written license is provided.
