# Azure RAGcelerator

A production-ready Retrieval Augmented Generation (RAG) solution hosted on Azure. Upload documents, automatically process them into searchable chunks with vector embeddings, and interact through a conversational chat interface.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Blob Storage   │────▶│  Azure Function  │────▶│  Cognitive Search   │
│  (documents)    │     │  (Event Grid)    │     │  (hybrid index)     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                               │                          │
                               ▼                          │
                        ┌──────────────────┐              │
                        │  Azure OpenAI    │              │
                        │  (embeddings)    │              │
                        └──────────────────┘              │
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│     User        │────▶│  Container App   │◀─────────────┘
│                 │◀────│  (Streamlit UI)  │
└─────────────────┘     └──────────────────┘
```

### Components

- **Azure Blob Storage**: Document upload and storage
- **Azure Functions**: Event-driven document processing pipeline
- **Azure OpenAI**: Embedding generation (text-embedding-ada-002) and chat completion
- **Azure Cognitive Search**: Hybrid search (keyword + vector) with semantic ranking
- **Azure Container Apps**: Streamlit-based chat interface
- **Entra ID**: Authentication for the UI

## Quick Start

### Prerequisites

- Python 3.11+
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://www.terraform.io/downloads)
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local)
- Docker (for containerized UI)

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Adam-CGI/azure_ragcellerator.git
cd azure_ragcellerator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infra

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var="environment=dev"

# Apply the infrastructure
terraform apply -var="environment=dev"

# Export outputs for local development
export STORAGE_CONNECTION_STRING=$(terraform output -raw storage_connection_string)
export SEARCH_ENDPOINT=$(terraform output -raw search_endpoint)
export SEARCH_API_KEY=$(terraform output -raw search_api_key)
export OPENAI_ENDPOINT=$(terraform output -raw openai_endpoint)
export OPENAI_API_KEY=$(terraform output -raw openai_api_key)
```

### Run Locally

**Document Processor (Azure Functions):**

```bash
cd src/processor
func start
```

**Streamlit UI:**

```bash
cd src/ui
streamlit run app.py
```

### Test the Pipeline

```bash
# Upload a test PDF
az storage blob upload \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --container-name documents \
  --name test.pdf \
  --file path/to/test.pdf

# The Function will automatically process the document
# Then open the UI at http://localhost:8501 to query it
```

## Project Structure

```
azure-ragcelerator/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml            # Tests and linting
│   └── deploy.yml        # Infrastructure and app deployment
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md   # Detailed architecture
│   ├── DEPLOYMENT.md     # Deployment guide
│   └── AUTH_SETUP.md     # Authentication setup
├── infra/                 # Terraform infrastructure
│   ├── main.tf           # Main configuration
│   ├── variables.tf      # Variable definitions
│   ├── outputs.tf        # Output values
│   ├── storage.tf        # Storage account
│   ├── cognitive_search.tf
│   ├── function_app.tf
│   ├── container_apps.tf
│   └── event_grid.tf
├── src/
│   ├── processor/         # Azure Function app
│   │   ├── config.py     # Configuration
│   │   ├── models.py     # Data models
│   │   ├── function_app.py
│   │   ├── storage/      # Blob operations
│   │   ├── extractors/   # Text extraction
│   │   ├── splitters/    # Text chunking
│   │   ├── embeddings/   # Vector generation
│   │   └── indexers/     # Search indexing
│   └── ui/                # Streamlit app
│       ├── app.py        # Main UI
│       ├── config.py     # Configuration
│       └── search_service.py
├── tests/                 # Unit and integration tests
├── Dockerfile            # UI container
├── requirements.txt      # Python dependencies
└── README.md
```

## Configuration

All configuration is done through environment variables. See `env.example` for a template:

| Variable | Description |
|----------|-------------|
| `STORAGE_CONNECTION_STRING` | Azure Storage connection string |
| `SEARCH_ENDPOINT` | Cognitive Search endpoint URL |
| `SEARCH_API_KEY` | Cognitive Search admin key |
| `OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `OPENAI_API_KEY` | Azure OpenAI API key |
| `EMBEDDING_MODEL` | Embedding model deployment name (default: text-embedding-ada-002) |
| `CHAT_MODEL` | Chat model deployment name (default: gpt-35-turbo) |

## Development

```bash
# Run tests
pytest tests/

# Run linter
ruff check src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/
```

## Deployment

Push to `main` triggers automatic deployment via GitHub Actions:

1. **CI Pipeline**: Runs tests and linting
2. **Deploy Pipeline**: 
   - Applies Terraform infrastructure
   - Builds and pushes UI Docker image
   - Updates Container App
   - Deploys Function App code

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for manual deployment instructions and GitHub Secrets setup.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed system design
- [Deployment](docs/DEPLOYMENT.md) - CI/CD and manual deployment
- [Authentication](docs/AUTH_SETUP.md) - Entra ID configuration

## License

MIT License - see [LICENSE](LICENSE) for details.

