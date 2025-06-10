#!/bin/bash
# CP Tariff OCR API - Production Startup Script

echo "Starting CP Tariff OCR API (Production Mode)"

# Navigate to backend directory
cd backend

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

echo "Server started at http://0.0.0.0:8000"
echo "API documentation available at http://0.0.0.0:8000/docs"
