# MQTT Setup And Integration Guide

This guide explains how MQTT fits into the industrial control platform and how to run a local broker for testing. It is linked from the root [README.md](../README.md), the platform [README.md](README.md), and the OCR module [README.md](../ocr_project/README.md).

## Role In The System

MQTT is used as a decoupled communication layer for telemetry, tracking results, system status, control commands, OCR events, and alert messages. REST APIs and Socket.IO are still used by the dashboard, but MQTT makes it easier to connect additional clients, testing tools, or external industrial components without coupling them directly to the web backend.

## Relevant Code

- Backend MQTT service: [backend/services/mqtt_service.py](backend/services/mqtt_service.py)
- Tracking MQTT publishing hook: [backend/services/tracking_service.py](backend/services/tracking_service.py)
- Frontend MQTT API: [frontend/src/api/mqttApi.ts](frontend/src/api/mqttApi.ts)
- Frontend environment template: [.env.example](.env.example)

## Default Broker Settings

Backend defaults:

```text
host: localhost
port: 1883
client_id prefix: conveyor_tracking_system
```

Frontend environment placeholder:

```text
VITE_MQTT_URL=ws://localhost:8083/mqtt
```

The current frontend MQTT API also contains a local development configuration using `localhost:1883`. If a browser client needs direct MQTT-over-WebSocket access, configure the broker with a WebSocket listener such as `8083` and align the frontend connection settings.

## Backend Topics

The backend MQTT service defines these conveyor-oriented topics:

```text
conveyor/tracking/video
conveyor/tracking/objects
conveyor/tracking/stats
conveyor/system/status
conveyor/control/commands
conveyor/alerts/errors
```

## Frontend Topics

The frontend MQTT API defines dashboard-facing topics:

```text
camera/video_frame
camera/video_frame_binary
tracking/object_data
tracking/object_detected
tracking/object_lost
tracking/stats
system/status
ocr/triggered
ocr/result
control/command
```

## Option 1: Run Mosquitto On Windows

1. Download Mosquitto from <https://mosquitto.org/download/>.
2. Install it with the Windows service option enabled.
3. Start the service from an administrator terminal:

```cmd
net start mosquitto
```

4. Check the service:

```cmd
sc query mosquitto
```

## Option 2: Run Mosquitto With Docker

```bash
docker pull eclipse-mosquitto
docker run -d --name mosquitto -p 1883:1883 -p 8083:8083 eclipse-mosquitto
```

For browser MQTT-over-WebSocket tests, provide a Mosquitto configuration that enables a WebSocket listener. A minimal local-development configuration is:

```text
listener 1883
protocol mqtt
allow_anonymous true

listener 8083
protocol websockets
allow_anonymous true
```

Mount that configuration into the container if WebSocket access is required.

## Option 3: Install On Linux Or macOS

Ubuntu or Debian:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

macOS with Homebrew:

```bash
brew install mosquitto
brew services start mosquitto
```

## Connection Checks

In one terminal, subscribe to a test topic:

```bash
mosquitto_sub -h localhost -p 1883 -t "test/topic"
```

In another terminal, publish a message:

```bash
mosquitto_pub -h localhost -p 1883 -t "test/topic" -m "Hello MQTT"
```

You can also run the project test helpers when available:

```bash
python backend/test_mqtt_broker.py
python backend/test_mqtt_integration.py
```

## Troubleshooting

- Connection refused: confirm the broker is running and listening on `1883`.
- Browser MQTT failure: confirm the broker has a WebSocket listener, usually `8083`, and that the frontend URL matches it.
- Port already in use: check `netstat -ano | findstr 1883` on Windows or `lsof -i :1883` on Unix-like systems.
- Authentication failure: either configure valid credentials in the broker and client settings or enable anonymous access for local-only testing.
- Firewall issues: allow local traffic for the selected MQTT and WebSocket ports.

## Local Run Order

1. Start the MQTT broker.
2. Start the Flask backend:

```bash
python backend/app.py
```

3. Start the Vue frontend:

```bash
npm run dev
```

4. Start the OCR service only when OCR endpoints are needed:

```bash
cd ..\ocr_project
uvicorn main:app --host 127.0.0.1 --port 8000
```
