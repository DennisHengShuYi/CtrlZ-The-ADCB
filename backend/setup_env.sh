#!/bin/bash
set -eo pipefail

echo "==> Configuring backend Python environment..."
cd /Users/laiminhan/Desktop/VS/CtrlZ-The-ADCB/backend

if [ -d "venv" ]; then
    echo "==> Removing existing virtual environment..."
    rm -rf venv
fi

echo "==> Creating new virtual environment..."
python3 -m venv venv

echo "==> Activating virtual environment..."
source venv/bin/activate

echo "==> Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "==> Installing dependencies safely..."
# Explicit pip installs handling cryptography constraints
pip install "cryptography"
pip install fastapi "uvicorn[standard]" python-dotenv httpx pyjwt "supabase>=2.0.0" google-generativeai reportlab pydantic

echo "==> Environment ready."
