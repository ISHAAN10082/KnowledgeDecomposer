# IntelliDoc Extractor - Document Intelligence System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced, local-first document intelligence pipeline that ingests business documents (PDFs, images), performs OCR, classifies them, and extracts structured data using a self-correcting, vision-enabled LLM. This system is designed to turn unstructured documents like invoices into actionable, validated JSON data.

## 🚀 Features

- **Multi-format Document Ingestion**: Handles PDF (native & scanned), PNG, JPG with robust parsing.
- **Advanced Image Pre-processing**: Automatically de-skews and sharpens document images with OpenCV to improve OCR accuracy.
- **High-Accuracy OCR**: Integrates the EasyOCR engine for reliable text extraction from scanned documents.
- **Intelligent Document Classification**: Uses a fast LLM to categorize documents (e.g., 'invoice', 'resume') before processing.
- **Multi-Modal LLM Extraction**: Leverages a vision-enabled model (LLaVA) to understand document layouts and tables visually.
- **Self-Correcting Extraction Loop**: If initial extraction fails Pydantic validation (e.g., totals don't add up), the system re-prompts the LLM with the specific error, asking it to correct its own mistake.
- **Schema-Driven & Validated Output**: Uses Pydantic schemas to enforce a strict, validated JSON output for structured data.
- **Explainable AI**: The final output includes an overall confidence score and field-level justifications, explaining where the model found the data.
- **Local-First & Private**: Powered by Ollama, all processing and model inference happens on your local machine.
- **Web Interface & API**: Comes with a FastAPI backend and a polished Gradio UI for easy interaction and demonstration.

## 🏗️ Architecture

### Core Components

```
IntelliDoc/
├── 📁 api/              # FastAPI server
├── 📁 ui/               # Gradio web interface
├── 📁 intellidoc/        # Core library
│   ├── 📁 core/         # Core validation logic
│   ├── 📁 extract/      # Classifier, Extractor, and Schemas
│   ├── 📁 ingestion/    # Document parsing and OCR
│   ├── 📁 models/       # Ollama LLM client and prompts
│   ├── 📁 preprocessing/ # Image pre-processing (OpenCV)
│   ├── 📁 storage/      # Vector store (ChromaDB for deduplication)
│   └── 📁 utils/        # Monitoring and helper utilities
└── 📁 data/             # Sample documents for testing
```

### Processing Pipeline

1.  **File Ingestion** → PDF or image file is uploaded.
2.  **Image Pre-processing** → (If image/scanned) De-skewing & sharpening.
3.  **OCR** → (If image/scanned) Text is extracted.
4.  **Document Classification** → A fast LLM determines the document type (e.g., `invoice`).
5.  **Vision-Enabled Extraction** → A multi-modal LLM analyzes the document image and text to extract data against a Pydantic schema.
6.  **Validation & Self-Correction** → The extracted data is validated. If it's inconsistent (e.g., math errors), the extractor re-prompts the LLM with the error to fix it.
7.  **Final Output** → A validated JSON object is returned with confidence scores and justifications.

## 📦 Installation

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) (for local LLM inference)
- 8GB+ RAM recommended (16GB+ for larger models)

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd intellidoc-extractor # Or your project name
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install and Configure Ollama

```bash
# Download from https://ollama.ai/
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service in the background
ollama serve &

# Pull the required models
ollama pull llava:7b  # Primary vision model for extraction
ollama pull phi3:mini   # Fast validation model for classification
```

## 🎯 Quick Start

The best way to run the system is through the interactive web UI.

### 1. Start the API Server

In your first terminal window, run:
```bash
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```
The API will be available at `http://localhost:8000/docs`.

### 2. Start the Web UI

In a second terminal window, run:
```bash
python ui/app.py
```
The UI will be available at `http://localhost:7860`.

## 📊 Usage

1.  Open your browser to `http://localhost:7860`.
2.  Upload an invoice document (PDF or an image file like PNG/JPG).
3.  The UI will display the original document on the left and the extracted, structured JSON data on the right.
4.  Below the main view, you will see the AI's confidence score and a field-by-field justification for the extracted data.

---

**IntelliDoc Extractor** - Transform your documents into structured, reliable data. 🧠✨ 