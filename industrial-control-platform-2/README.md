# Industrial Control Platform Module

This directory contains the main full-stack industrial control application in the repository. It is the execution layer responsible for device coordination, conveyor control, robot-arm control, visual tracking, and dashboard interaction.

## Contents

- `backend/`: Flask APIs, device services, tracking logic, and integration endpoints
- `frontend/`: Vue 3 dashboard and operator-facing control views
- `hardware/`: Arduino firmware used by the platform
- `public/`: static frontend assets
- `requirements.txt`: Python dependencies for the backend
- `package.json`: frontend dependencies and build scripts

## Quick Start

```bash
pip install -r requirements.txt
npm install
copy .env.example .env
python backend/app.py
npm run dev
```

See the repository root [README.md](../README.md) for the full project overview, demo assets, and OCR microservice context.
