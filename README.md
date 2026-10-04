# Documentation Assistant

**Ask questions about LangChain documentation through a retrieval-augmented chat interface.**

Documentation Assistant crawls documentation, splits it into searchable passages, and stores their embeddings in Pinecone. A Streamlit application then connects a LangChain agent to that knowledge base so users can ask questions in natural language and inspect the sources retrieved for each answer.

The repository is named `Documentation-Assistan`; the Python package and commands retain the corresponding `documentation_assistan` spelling.

## Contents

- [Overview](#overview)
- [How it works](#how-it-works)
- [Technology stack](#technology-stack)
- [Requirements](#requirements)
- [Installation and setup](#installation-and-setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Current limitations](#current-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project provides a practical example of **retrieval-augmented generation (RAG)**: relevant documentation is retrieved from a vector database and supplied to a language model as context for its response.

It can help developers explore LangChain concepts, find relevant documentation, and study how crawling, embeddings, retrieval tools, and a conversational interface fit together.

### Features

- **Documentation ingestion:** crawl pages starting from the LangChain Python documentation with Tavily.
- **Text chunking:** split extracted content into overlapping passages with LangChain.
- **Semantic search:** embed content with OpenAI and store vectors in Pinecone.
- **Agent-driven retrieval:** give a LangChain agent a tool for searching the indexed documentation.
- **Source visibility:** preserve source URLs and display retrieved sources alongside chat responses.
- **Interactive interface:** ask questions, review messages, and clear the displayed conversation in Streamlit.
- **Asynchronous indexing:** submit document batches concurrently with per-batch success and failure logs.

The system prompt instructs the agent to retrieve context, cite its sources, and acknowledge when the retrieved documentation does not contain the answer. These are model instructions, not guarantees of correctness.

## How it works

The project has two separate workflows: **ingestion**, which prepares the knowledge base, and **question answering**, which uses it.

### 1. Build the knowledge base

1. Tavily crawls `https://python.langchain.com/` with a maximum depth of `3` and advanced extraction.
2. Pages with missing or empty text are skipped.
3. Each valid page becomes a LangChain `Document`, with its URL stored in `metadata["source"]`.
4. `RecursiveCharacterTextSplitter` creates chunks of up to `4,000` characters with `200` characters of overlap.
5. OpenAI's `text-embedding-3-small` model converts the chunks into vectors.
6. The chunks, metadata, and vectors are added to the existing Pinecone index `langchain-doc-index`.

The main ingestion function submits batches of `500` documents concurrently. The embedding client separately uses a batch size of `50`; these are different settings.

### 2. Answer a question

1. Streamlit passes the user's question to `run_llm(query)`.
2. The backend creates a LangChain agent using OpenAI's `gpt-5.2` model.
3. The agent can call `retrieve_context` to search Pinecone for relevant passages.
4. The retrieval tool returns both text for the model and the original documents as tool artifacts.
5. The backend returns the final answer and the documents collected from tool messages.
6. Streamlit displays the answer and the documents' source URLs in a **Sources** expander.

Questions search the existing index; they do not trigger a fresh Tavily crawl.

## Technology stack

| Component | Technology | Responsibility |
| --- | --- | --- |
| Runtime | Python 3.14+ | Application and ingestion scripts |
| Dependency management | uv | Python environment and locked dependencies |
| User interface | Streamlit | Browser-based chat |
| Agent orchestration | LangChain | Agent execution and retrieval tool |
| Web crawling | Tavily | Documentation discovery and extraction |
| Embeddings | OpenAI `text-embedding-3-small` | Document and query vectors |
| Answer generation | OpenAI `gpt-5.2` | Responses using retrieved context |
| Vector database | Pinecone | Persistent storage and similarity search |
| Environment loading | python-dotenv | Local API key configuration |
| Certificate bundle | certifi | Certificate paths configured during ingestion |

Chroma and Deep Agents are included in the declared dependencies, but the active implementation uses Pinecone and LangChain's `create_agent`. Tavily Map and Extract clients are initialized in the ingestion module; the ingestion workflow itself calls Tavily Crawl.

## Requirements

Before starting, you need:

- **Python 3.14 or newer.** The repository's `.python-version` selects Python 3.14.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for the documented installation workflow.
- **Git** to clone the repository.
- An **OpenAI API key** with access to the configured embedding and chat models and sufficient API quota.
- A **Pinecone API key** and an existing compatible vector index.
- A **Tavily API key** to run ingestion.
- Internet access to the external services.

A local GPU is not required: embeddings and answer generation run through hosted APIs. Provider usage may incur charges. Tavily is needed for ingestion; the chat backend only requires OpenAI and Pinecone once the index is populated.

## Installation and setup

Run all commands from the repository root unless otherwise stated.

### 1. Clone the repository

```bash
git clone https://github.com/Cristobal-Jesus/Documentation-Assistan.git
cd Documentation-Assistan
```

### 2. Install Python and dependencies

```bash
uv python install 3.14
uv sync --locked
```

This uses the committed `uv.lock` to install the project's dependencies into `.venv`. The commands below use `uv run`, so manual environment activation is unnecessary.

### 3. Configure API keys

Create a file named `.env` in the repository root:

```dotenv
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Both the ingestion module and the backend call `load_dotenv()`.

| Variable | Required for | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Ingestion and chat | Embeddings and answer generation |
| `PINECONE_API_KEY` | Ingestion and chat | Read and write access to the vector index |
| `TAVILY_API_KEY` | Ingestion | Documentation crawling |

The repository already ignores `.env` files. Keep real credentials out of source code, commits, screenshots, and issue reports.

### 4. Create the Pinecone index

In your [Pinecone console](https://app.pinecone.io/), create a dense vector index with these settings:

| Setting | Value |
| --- | --- |
| Name | `langchain-doc-index` |
| Vector type | Dense |
| Dimension | `1536` |
| Similarity metric | Cosine |

The dimension matches the default output of `text-embedding-3-small`; see the [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings).

Choose a supported cloud and region for your Pinecone account and wait for the index to become ready. The application generates embeddings itself, so configure an index that accepts externally generated vectors rather than relying on Pinecone-hosted embedding generation.

**The code connects to an existing index; it does not create one.** Both ingestion and retrieval use the same hardcoded index name. No explicit namespace is configured.

### 5. Ingest the documentation

```bash
uv run python src/documentation_assistan/ingestion.py
```

Use this direct script command: the module currently imports its adjacent logger with `from logger import ...`.

The terminal reports extracted documents, generated chunks, and indexing results. Check that:

- At least one document and one chunk were produced.
- Every indexing batch succeeded.
- The Pinecone index contains vectors after ingestion.

A final `PIPELINE COMPLETE` banner alone does not prove that every batch succeeded: individual failures are logged and the script can continue.

You only need ingestion to populate or refresh the knowledge base, not before each chat session. Re-running it may insert duplicate content because the script does not supply stable document IDs or implement deduplication.

### 6. Start the chat application

The frontend imports `backend.core` from `src/backend`. Add `src` to Python's module search path before launching Streamlit.

**Windows PowerShell**

```powershell
$env:PYTHONPATH = (Resolve-Path ./src).Path
uv run streamlit run main.py
```

**macOS / Linux**

```bash
PYTHONPATH="$PWD/src" uv run streamlit run main.py
```

Open the local URL printed by Streamlit, normally [http://localhost:8501](http://localhost:8501).

The console entry point `documentation-assistan` declared in `pyproject.toml` currently points to a missing package-level `main` function. Use the script and Streamlit commands above.

## Usage

### Ask questions in the browser

Enter a self-contained question, for example:

- "What are Deep Agents in LangChain?"
- "How do I define a tool for a LangChain agent?"
- "What is the difference between a retriever and a vector store?"
- "How can I use Pinecone with LangChain?"

Answers depend on the pages actually present in the index. Expand **Sources** to inspect the retrieved URLs and verify relevant details in the original documentation.

Use **Clear chat** in the sidebar to reset the displayed messages. This does not delete the Pinecone index.

**Conversation behavior:** Streamlit retains the visible conversation in session state, but the backend receives only the latest question. Earlier messages are not passed to the agent, so follow-up questions should repeat any necessary context.

### Run the backend directly

A small command-line example is included in the backend:

```bash
uv run python src/backend/core.py
```

It asks `"what are deep agents?"` and prints the returned dictionary. It requires the same populated index and OpenAI/Pinecone credentials as the web application.

### Use the backend from Python

With `src` on your Python path:

```python
from backend.core import run_llm

result = run_llm("How do LangChain retrieval tools work?")

print(result["answer"])

for document in result["context"]:
    print(document.metadata.get("source", "Unknown"))
```

The return value contains:

| Key | Contents |
| --- | --- |
| `answer` | Content of the agent's final message |
| `context` | Retrieved LangChain `Document` objects collected from tool artifacts |

Sources may appear more than once if multiple retrieved chunks come from the same page or if the agent makes multiple retrieval calls.

## Configuration

Most behavior is currently configured in Python source rather than through environment variables or command-line options.

| Setting | Current value | Location |
| --- | --- | --- |
| Crawl starting URL | `https://python.langchain.com/` | `src/documentation_assistan/ingestion.py` |
| Crawl maximum depth | `3` | `tavily_crawl.invoke(...)` |
| Extraction depth | `advanced` | `tavily_crawl.invoke(...)` |
| Text chunk size | `4000` characters | `RecursiveCharacterTextSplitter` |
| Chunk overlap | `200` characters | `RecursiveCharacterTextSplitter` |
| Embedding model | `text-embedding-3-small` | Ingestion and backend |
| Embedding client batch size | `50` | Ingestion's `OpenAIEmbeddings` |
| Indexing batch size used by `main()` | `500` documents | `index_documents_async(...)` call |
| Pinecone index name | `langchain-doc-index` | Ingestion and backend |
| Chat model | `gpt-5.2` | `src/backend/core.py` |
| Retrieval count requested in code | `4` | `retrieve_context` |
| Agent instructions | LangChain-specific retrieval and citation prompt | `run_llm` |
| Page title and chat text | LangChain Documentation Helper | `main.py` |

The retrieval implementation passes `k=4` to the retriever's `invoke` call. To explicitly configure the search count when modifying the backend, set it on the retriever:

```python
retriever = vectorestore.as_retriever(search_kwargs={"k": 4})
retrieve_docs = retriever.invoke(query)
```

This is a suggested configuration change, not an additional setup step or a description of a code change already included in this repository.

### Adapt the project to another documentation site

1. Change the crawl URL and, if needed, the crawl settings.
2. Use a separate Pinecone index to keep unrelated documentation collections separate.
3. Update the index name in both ingestion and the backend.
4. Adjust the system prompt, tool description, and Streamlit labels for the new documentation.
5. Run ingestion and inspect the results before asking questions.

Keep the embedding model consistent between indexing and querying. If you change the embedding model or vector dimensions, rebuild the knowledge base in a compatible index.

The `TavilyMap` client has separate settings in the module, but that client is not called by the current ingestion workflow. Changing its settings will not configure `TavilyCrawl`.

## Project structure

| Path | Purpose |
| --- | --- |
| `main.py` | Streamlit chat interface, session state, and source display |
| `src/backend/core.py` | Model setup, Pinecone retrieval tool, and `run_llm` |
| `src/backend/__init__.py` | Backend package marker |
| `src/documentation_assistan/ingestion.py` | Crawl, document conversion, chunking, embeddings, and indexing |
| `src/documentation_assistan/logger.py` | Colored terminal logging helpers |
| `src/documentation_assistan/__init__.py` | Application package marker |
| `pyproject.toml` | Project metadata, dependencies, and build configuration |
| `uv.lock` | Locked dependency resolution |
| `.python-version` | Selected Python version |
| `.gitignore` | Exclusions for credentials, environments, caches, and generated files |
| `README.md` | Setup and usage documentation |

## Current limitations

- **No conversational memory in the backend:** each question starts a new agent invocation with only that question.
- **No automatic refresh:** documentation remains as indexed until ingestion is run again.
- **No deduplication or stale-document cleanup:** repeated crawls can add redundant or outdated content.
- **No bounded indexing concurrency:** all document batches are scheduled together, which may encounter provider rate limits.
- **Partial ingestion can appear complete:** review the batch results rather than relying only on the final banner.
- **Source display is based on retrieval:** the Sources expander lists retrieved documents, not a verified mapping from each answer statement to its evidence.
- **Coverage depends on crawling:** redirects and discovered links can affect which pages are collected; the code does not explicitly restrict crawling to documentation paths.
- **Local development focus:** authentication, persistent chat storage, automated tests, and deployment configuration are not included.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Python version or dependency installation error | Use Python 3.14+ and run `uv sync --locked` from the repository root. |
| `ModuleNotFoundError: No module named 'backend'` | Set `PYTHONPATH` to the repository's `src` directory using the platform-specific launch command. |
| `ModuleNotFoundError: No module named 'logger'` | Run ingestion by its file path, as shown above, rather than as a package module. |
| The `documentation-assistan` command fails | The declared entry point is not implemented. Use the documented script commands. |
| Missing or invalid API key | Check the root `.env` file, key spelling, and the service associated with each key. Restart the app after changes. |
| Pinecone index not found | Create `langchain-doc-index` in the Pinecone project accessible to your API key and wait for it to be ready. |
| Vector dimension mismatch | Use a 1536-dimensional index for the current default embedding configuration. Check that ingestion and retrieval use the same model. |
| OpenAI model access or quota error | Verify API model access, available quota, and billing for the account associated with the API key. |
| Empty or irrelevant answers | Check crawl output, successful indexing batches, and the contents of the selected Pinecone index. |
| Duplicate sources | Several retrieved chunks may share one URL; repeated ingestion can also create duplicate content. |
| Rate-limit errors during ingestion | Reduce concurrent indexing requests in the code and review provider limits before retrying. Smaller batches alone do not cap concurrency. |
| Certificate verification error | Check system certificates, proxy configuration, and trust settings. Ingestion configures certifi paths; do not disable TLS verification as a workaround. |

## Contributing

Issues and pull requests are welcome. For a bug report, include the command used, operating system, Python version, expected behavior, and relevant error output with credentials removed.

For changes affecting retrieval or ingestion, describe how you validated the result and whether reindexing is required. Potential improvements include bounded concurrency, stable document IDs, backend conversation history, an implemented CLI entry point, and automated tests.

## License

No license file is currently included in this repository. No open-source license is specified.

---

Created by [Cristobal-Jesus](https://github.com/Cristobal-Jesus).
