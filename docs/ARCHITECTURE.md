# Azure RAGcelerator - Architecture

## System Overview

Azure RAGcelerator is a production-ready Retrieval Augmented Generation (RAG) solution built on Azure services. It enables document upload, automatic processing, and conversational Q&A through a web interface.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Azure RAGcelerator                              │
└─────────────────────────────────────────────────────────────────────────────┘

                                    Upload
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Azure Blob Storage                                   │
│                         ┌─────────────────┐                                  │
│                         │   documents/    │                                  │
│                         │   (PDF files)   │                                  │
│                         └────────┬────────┘                                  │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                           BlobCreated Event
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Event Grid                                         │
│                    ┌────────────────────────┐                               │
│                    │   System Topic         │                               │
│                    │   (Storage Events)     │                               │
│                    └───────────┬────────────┘                               │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Azure Functions (Consumption)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Document Processor                                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │ Download │─▶│ Extract  │─▶│  Split   │─▶│  Embed   │─▶│  Index   │ │ │
│  │  │   Blob   │  │   Text   │  │  Chunks  │  │  Texts   │  │  Search  │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
┌───────────────────────────────┐  ┌───────────────────────────────┐
│       Azure OpenAI            │  │    Azure Cognitive Search     │
│  ┌─────────────────────────┐  │  │  ┌─────────────────────────┐  │
│  │ text-embedding-ada-002  │  │  │  │    rag-documents        │  │
│  │ (1536 dimensions)       │  │  │  │    ├── id               │  │
│  └─────────────────────────┘  │  │  │    ├── content          │  │
│  ┌─────────────────────────┐  │  │  │    ├── contentVector    │  │
│  │ gpt-35-turbo            │  │  │  │    ├── sourcePath       │  │
│  │ (Chat completions)      │  │  │  │    ├── fileName         │  │
│  └─────────────────────────┘  │  │  │    ├── chunkId          │  │
└───────────────────────────────┘  │  │    └── processedAt      │  │
                                   │  └─────────────────────────┘  │
                                   └───────────────────────────────┘
                                                   │
                                                   │ Hybrid Search
                                                   │ (Keyword + Vector)
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Azure Container Apps                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Streamlit UI                                       │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │  Query   │─▶│ Hybrid Search│─▶│ RAG Prompt   │─▶│ Chat Response  │  │ │
│  │  │  Input   │  │  + Ranking   │  │ Construction │  │ + Citations    │  │ │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                    ┌─────────┴──────────┐                                   │
│                    │   Entra ID Auth    │                                   │
│                    │   (Easy Auth)      │                                   │
│                    └────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │
                               User Access
```

## Component Details

### 1. Document Storage (Azure Blob Storage)

- **Purpose:** Store uploaded PDF documents
- **Containers:**
  - `documents/` - Production document uploads
  - `test-data/` - Test documents for development
- **Features:**
  - Blob versioning enabled
  - Soft delete (7 days retention)
  - Private access only

### 2. Event Processing (Event Grid)

- **Purpose:** Trigger document processing on upload
- **Configuration:**
  - System Topic on Storage Account
  - Subscription for `BlobCreated` events
  - Filter for `.pdf` files in `documents/` container
- **Target:** Azure Function App

### 3. Document Processor (Azure Functions)

- **Purpose:** Process documents into searchable chunks
- **Runtime:** Python 3.11 on Consumption plan
- **Pipeline Steps:**
  1. **Download:** Fetch blob content from storage
  2. **Extract:** Parse PDF text using PyPDF2
  3. **Split:** Chunk text (1000 chars, 200 overlap)
  4. **Embed:** Generate vectors via Azure OpenAI
  5. **Index:** Upsert to Cognitive Search

### 4. Embedding Generation (Azure OpenAI)

- **Model:** `text-embedding-ada-002`
- **Dimensions:** 1536
- **Batch Processing:** 16-64 texts per API call
- **Retry Logic:** Exponential backoff on rate limits

### 5. Search Index (Azure Cognitive Search)

- **Tier:** Basic (MVP), Standard (Production)
- **Index Schema:**
  | Field | Type | Features |
  |-------|------|----------|
  | id | String | Key, Filterable |
  | content | String | Searchable |
  | contentVector | Collection(Single) | Vector (1536d) |
  | sourcePath | String | Filterable |
  | fileName | String | Facetable |
  | chunkId | Int32 | Sortable |
  | processedAt | DateTimeOffset | Sortable |

- **Search Capabilities:**
  - Keyword search (BM25)
  - Vector similarity (HNSW)
  - Semantic ranking
  - Hybrid fusion

### 6. Chat Interface (Azure Container Apps)

- **Framework:** Streamlit
- **Features:**
  - Conversation history
  - Hybrid search integration
  - RAG prompt construction
  - Source citations
- **Authentication:** Entra ID (Easy Auth)

## Data Flow

### Document Ingestion Flow

```
1. User uploads PDF to Blob Storage
2. Event Grid fires BlobCreated event
3. Function App receives event
4. Processor downloads and extracts text
5. Text is split into overlapping chunks
6. Azure OpenAI generates embeddings
7. Chunks + embeddings indexed in Cognitive Search
```

### Query Flow

```
1. User enters question in Streamlit UI
2. Query embedded using Azure OpenAI
3. Hybrid search executed (keyword + vector)
4. Top results retrieved with semantic ranking
5. RAG prompt constructed with context
6. Azure OpenAI generates answer
7. Response displayed with source citations
```

## Security Model

### Network Security (MVP)

- All services use public endpoints with API keys
- TLS 1.2+ enforced
- Container App accessible via HTTPS only

### Authentication

- **UI:** Entra ID (Azure AD) via Easy Auth
- **Services:** Managed Identity where possible
- **Secrets:** Connection strings in App Settings

### Post-MVP Enhancements

- Private endpoints for all services
- VNet integration
- Key Vault for secrets
- Conditional Access policies

## Scalability

### Current (MVP)

| Component | Scaling |
|-----------|---------|
| Functions | Consumption (auto-scale) |
| Container Apps | 0-3 replicas |
| Cognitive Search | Basic tier (limited) |

### Production Recommendations

- Upgrade Cognitive Search to Standard tier
- Increase Container App replicas
- Consider Premium Functions plan
- Add CDN for static assets

## Cost Optimization

### Development Environment

- Use Free/Basic tiers where possible
- Scale to 0 when idle
- LRS storage replication

### Production

- Reserved capacity for predictable workloads
- Monitor and optimize query patterns
- Implement caching where applicable

## Monitoring

### Application Insights

- Function execution logs
- Performance metrics
- Error tracking
- Dependency tracing

### Azure Monitor

- Resource health
- Cost tracking
- Alert rules

## Disaster Recovery (Post-MVP)

Not in scope for MVP. Recommendations:

- Geo-redundant storage
- Search replica in secondary region
- Database backups
- Documented recovery procedures



