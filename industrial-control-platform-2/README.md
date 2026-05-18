# Industrial Control Platform Module

This directory contains the main full-stack control platform for the vision-guided industrial line. It is responsible for the dashboard, backend APIs, conveyor control, robot-arm control, visual tracking, device coordination, MQTT communication, and Arduino firmware used by the demonstration system.

Related documentation:

- Overall project overview: [../README.md](../README.md)
- OCR microservice: [../ocr_project/README.md](../ocr_project/README.md)
- MQTT setup and validation: [MQTT_INSTALLATION_GUIDE.md](MQTT_INSTALLATION_GUIDE.md)

## Module Responsibilities

- Provide a Vue 3 dashboard for monitoring, tracking visualization, and device operation.
- Expose Flask APIs for conveyor control, robot-arm control, tracking, OCR proxy calls, pipeline control, and device management.
- Publish realtime state through Socket.IO for dashboard interaction.
- Support MQTT-based telemetry and command channels for decoupled integration.
- Keep Arduino firmware for conveyor and robot-arm control under the same module as the platform that drives it.

## Layout

```text
industrial-control-platform-2/
  backend/                   Flask backend, APIs, services, models, tests
  backend/api/               Route modules for devices, tracking, OCR, and pipeline control
  backend/services/          Device, MQTT, and tracking service implementations
  backend/model/             Demo model and dataset template
  frontend/src/              Vue 3 application source
  hardware/arduino/belt/     Conveyor firmware
  hardware/arduino/robot_arm Robot-arm firmware
  MQTT_INSTALLATION_GUIDE.md MQTT broker setup guide
  RUN_GUIDE.md               Local run notes from the original project
  PROJECT_DEPENDENCIES.md    Dependency notes from the original project
```

## Runtime Architecture

- Frontend: Vue 3, TypeScript, Vite, Element Plus, Pinia, ECharts, Three.js
- Backend: Flask, Flask-SocketIO, Flask-CORS, PySerial
- Vision: OpenCV, Ultralytics YOLO, DeepSORT, NumPy, Pillow
- Communication: REST APIs, Socket.IO events, MQTT topics
- Hardware: PLC-centered workflow plus Arduino firmware for selected components

## MQTT Integration

MQTT is used for decoupled realtime data and command exchange. The backend service defines conveyor-oriented topics such as:

- `conveyor/tracking/video`
- `conveyor/tracking/objects`
- `conveyor/tracking/stats`
- `conveyor/system/status`
- `conveyor/control/commands`
- `conveyor/alerts/errors`

The frontend MQTT API also defines dashboard-facing topics for video frames, object data, tracking status, control commands, OCR triggers, and OCR results. See [frontend/src/api/mqttApi.ts](frontend/src/api/mqttApi.ts) and [backend/services/mqtt_service.py](backend/services/mqtt_service.py) for the concrete topic definitions.

For local setup, install or run a broker before testing MQTT features:

```bash
mosquitto -p 1883
```

Full broker setup is documented in [MQTT_INSTALLATION_GUIDE.md](MQTT_INSTALLATION_GUIDE.md).

## Quick Start

```bash
pip install -r requirements.txt
npm install
copy .env.example .env
python backend/app.py
npm run dev
```

Default endpoints:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`
- MQTT broker: `localhost:1883`
- Frontend MQTT WebSocket placeholder: `ws://localhost:8083/mqtt` in [.env.example](.env.example)

## Firmware

- Conveyor firmware: [hardware/arduino/belt/belt.ino](hardware/arduino/belt/belt.ino)
- Robot-arm firmware: [hardware/arduino/robot_arm/robotarm0724.ino](hardware/arduino/robot_arm/robotarm0724.ino)

## OCR Connection

OCR is not embedded directly into this module. The backend proxies OCR requests to the standalone service under [../ocr_project](../ocr_project/README.md). The relevant integration code is in [backend/api/energy_ocr.py](backend/api/energy_ocr.py).

Run the OCR service separately when OCR endpoints are needed:

```bash
cd ..\ocr_project
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Verification

```bash
python -m compileall -q backend
npm run build
```
