#!/bin/bash

# Start FastAPI backend directly. FastAPI will now serve the React + Vite 
# compiled SPA static files if present in frontend/dist.
echo "Starting FastAPI backend..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
