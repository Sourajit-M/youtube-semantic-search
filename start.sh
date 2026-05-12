#!/bin/bash

# Start FastAPI in the background
echo "Starting FastAPI backend..."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
echo "Waiting for API..."
while ! curl --silent --fail http://localhost:8000/health > /dev/null; do
    printf '.'
    sleep 2
done
echo "API is up!"

# Start Streamlit in the foreground
echo "Starting Streamlit frontend..."
streamlit run main.py --server.port 7860 --server.address 0.0.0.0
