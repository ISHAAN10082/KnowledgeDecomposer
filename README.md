# LocalKnow - Knowledge Decomposition Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A local-first knowledge contextualization system that ingests heterogeneous documents, performs semantic deduplication, builds a persistent knowledge graph, and exposes a local API and UI for exploration. LocalKnow extracts concepts, principles, and controversies from documents to create a structured knowledge base.

## 🚀 Features

- **Multi-format Document Ingestion**: PDF, DOCX, TXT, Markdown, CSV support with intelligent parsing
- **Semantic Deduplication**: Advanced content deduplication using sentence transformers and cosine similarity
- **Knowledge Graph Building**: Hierarchical knowledge graphs with NetworkX (Neo4j export ready)
- **Concept Extraction**: Robust extraction of STEM concepts using local LLMs
- **First Principles Analysis**: Identification of foundational truths and principles
- **Controversy Detection**: Detection of debates and conflicting viewpoints
- **Local LLM Integration**: Ollama-powered analysis with configurable models
- **Quality Validation**: Confidence scoring and quality assessment
- **Incremental Processing**: Smart checkpointing and resumable pipelines
- **Vector Storage**: ChromaDB for persistent embeddings and similarity search
- **Web Interface**: FastAPI backend with Gradio UI for easy interaction

## 🏗️ Architecture

### Core Components

```
LocalKnow/
├── 📁 api/              # FastAPI server
├── 📁 ui/               # Gradio web interface
├── 📁 localknow/        # Core library
│   ├── 📁 core/         # Validation, quality, resilience
│   ├── 📁 extract/      # Concept, principle, controversy extraction
│   ├── 📁 ingestion/    # Document parsing and chunking
│   ├── 📁 dedup/        # Semantic deduplication
│   ├── 📁 graph/        # Knowledge graph building
│   ├── 📁 models/       # LLM integration (Ollama)
│   ├── 📁 storage/      # Vector store (ChromaDB)
│   ├── 📁 persist/      # Version tracking (SQLite)
│   ├── 📁 pipeline/     # Orchestration engine
│   └── 📁 utils/        # Monitoring and utilities
└── 📁 data/             # Sample documents
```

### Processing Pipeline

1. **Document Validation** → Content validation and file size checks
2. **Version Tracking** → Detect new/modified documents
3. **Parsing & Chunking** → Extract text and split into chunks
4. **Semantic Deduplication** → Remove duplicate content using embeddings
5. **Concept Extraction** → Extract key concepts using LLMs
6. **Principle Analysis** → Identify foundational truths
7. **Controversy Detection** → Find debates and conflicting views
8. **Knowledge Graph Building** → Create hierarchical relationships
9. **Quality Assessment** → Confidence scoring and validation
10. **Persistence** → Store in vector database and knowledge graph

## 📦 Installation

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) (for local LLM inference)
- 8GB+ RAM recommended
- Apple Silicon support optimized

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd decomposer
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install and Configure Ollama

```bash
# macOS
brew install ollama

# Or download from https://ollama.ai/
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve &

# Pull recommended models (adjust sizes based on your hardware)
ollama pull qwen2.5:7b      # Primary model for concept extraction
ollama pull phi3:mini       # Fast validation model
ollama pull deepseek-r1:8b  # Reasoning model for principles
```

### 3. Configure Environment (Optional)

```bash
# Create .env file to customize settings
cat > .env << EOF
# Storage paths
CHROMA_DB_DIR=.chroma
SQLITE_DB_PATH=.localknow/content_versions.db

# Processing parameters
SIMILARITY_THRESHOLD=0.85
MAX_DOC_BYTES=52428800
PIPELINE_WORKERS=8

# API/UI ports
API_HOST=127.0.0.1
API_PORT=8000
UI_PORT=7860
EOF
```

## 🎯 Quick Start

### Command Line Usage

```bash
# Process documents in a directory
python -m localknow.pipeline.orchestrator --input ./data

# Or using the orchestrator directly
python localknow/pipeline/orchestrator.py ./data
```

### API Server

```bash
# Start the FastAPI server
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000

# API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Web UI

```bash
# Start the Gradio interface
python ui/app.py

# UI will be available at http://localhost:7860
```

### API Endpoints

- `GET /health` - System health and resource usage
- `GET /stats` - Detailed system statistics
- `POST /ingest` - Start document processing pipeline
- `GET /results/{job_id}` - Get processing results

## 📊 Usage Examples

### Basic Document Processing

```python
from localknow.pipeline.orchestrator import main as run_pipeline

# Process documents and get results
results = run_pipeline("./path/to/documents")
print(f"Processed {results['summary']['processed']} documents")
print(f"Extracted {results['summary']['concepts']} concepts")
```

### Using Individual Components

```python
from localknow.extract.concepts import RobustConceptExtractor
from localknow.models.ollama_client import OllamaClient

# Extract concepts from text
extractor = RobustConceptExtractor()
concepts = extractor.extract_with_validation("Your text here")

# Direct LLM usage
client = OllamaClient("qwen2.5:7b")
response = client.generate("Explain quantum mechanics")
```

## 🔧 Configuration

### Supported File Formats

| Format | Extension | Features |
|--------|-----------|----------|
| PDF | `.pdf` | Page limit, memory-safe streaming |
| Word | `.docx` | Full document parsing |
| Text | `.txt` | UTF-8 encoding, size limits |
| Markdown | `.md` | HTML conversion |
| CSV | `.csv` | Structured data parsing |

### Model Configuration

The system uses three types of models for different tasks:

- **Primary Model** (`qwen2.5:7b`): Main concept extraction and analysis
- **Validation Model** (`phi3:mini`): Fast validation and quality checks
- **Reasoning Model** (`deepseek-r1:8b`): Deep reasoning for principles

### Performance Tuning

#### Apple Silicon Optimization
- Automatic Metal GPU acceleration
- Optimized thread counts for M1/M2/M3/M4 chips
- 4-bit quantization support for larger models

#### Memory Management
- Document size limits (50MB default)
- Text content limits (1MB per document)
- Batch processing for embeddings
- Smart caching for LLM responses

## 📈 System Monitoring

LocalKnow includes built-in monitoring for:

- Memory usage and availability
- CPU utilization
- Processing throughput
- LLM performance metrics (tokens/second)
- Quality confidence scores

Access monitoring via the `/health` and `/stats` API endpoints.

## 🗃️ Data Storage

### Vector Database (ChromaDB)
- Persistent embeddings for similarity search
- Cross-run deduplication
- Configurable similarity thresholds

### Version Tracking (SQLite)
- Document change detection
- Content versioning
- Processing history

### Knowledge Graph (NetworkX)
- In-memory graph processing
- JSON serialization
- Neo4j export ready

## 🛠️ Development

### Project Structure

```python
# Core data types
@dataclass
class Document:
    document_id: str
    path: str
    content: str
    metadata: Dict[str, Any]

@dataclass
class Concept:
    name: str
    description: str
    confidence: float
    sources: List[str]
```

### Extending the System

1. **Add New File Parsers**: Extend `localknow/ingestion/parsers.py`
2. **Custom Extractors**: Implement new extractors in `localknow/extract/`
3. **Additional Models**: Configure new Ollama models in `localknow/config.py`
4. **Graph Algorithms**: Extend `localknow/graph/builder.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM inference
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [SentenceTransformers](https://www.sbert.net/) for embeddings
- [NetworkX](https://networkx.org/) for graph processing
- [FastAPI](https://fastapi.tiangolo.com/) and [Gradio](https://gradio.app/) for interfaces

## 🔮 Roadmap

- [ ] Neo4j integration for production graphs
- [ ] Advanced PDF repair and OCR
- [ ] Parallel processing optimization
- [ ] Real-time document watching
- [ ] Export formats (GraphML, GEXF)
- [ ] Advanced controversy analysis
- [ ] Citation and lineage tracking
- [ ] Multi-language support
- [ ] Docker containerization
- [ ] Comprehensive test suite

---

**LocalKnow** - Transform your documents into structured knowledge. 🧠✨ 