# InSolare LLM Document Processing

This project provides an LLM-based application for understanding, classifying, and extracting relevant information from tender and legal documents in the renewable energy sector.

## Project Structure

- **data_pipeline/**
  Contains modules for data ingestion and preprocessing (OCR, text normalization, and document chunking).

- **model_training/**
  Configurations, training scripts, and datasets for fine-tuning the LLM using Hugging Face transformers.

- **api/**
  RESTful API built with FastAPI for processing documents and integrating with InSolare systems.

- **tests/**
  Unit tests for preprocessing, model inference, and API endpoints.

- **docs/**
  Documentation including API specifications and data dictionary.

- **.github/workflows/**
  CI/CD pipelines for automated retraining and deployment.

## Setup

1. Clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   <!-- uvicorn api.src.main:app --reload
   python -m unittest discover tests -->