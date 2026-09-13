# UMB Course Assistant (In Progress)

An intelligent academic advising assistant for the University of Massachusetts Boston (UMB), designed to help students navigate course selections, prerequisites, schedules, and degree planning.

---

## Architecture Overview

The system uses a decoupled, hybrid retrieval architecture:

```text
umb-app/
├── data/                          # Data directory
│   ├── courses.db                 # SQLite (courses, offerings, sections,etc...)
│   └── chroma_db/                 # Chroma vector store (course embeddings)
│
├── pipeline/                      # ETL pipeline (writes to data/)
│   ├── scraping/                  # Scrapes & parses UMB course catalog
│   └── vectordb/                  # Generates Gemini embeddings for Chroma DB
│
├── umb-assistant/                 # Core AI engine (reads from data/)
│   └── src/umb_assistant/
│       ├── core/                  # Shared Gemini client, config, & connections
│       ├── services/              # Read-only search & vector retrieval
│       └── agent/                 # AdvisingAgent, tools, & system prompts
│
├── backend/                       # (Upcoming) FastAPI application
└── frontend/                      # (Upcoming) Web interface
```

---

## Key Features

* **Hybrid Retrieval (SQL + Vector)**:
  * **Deterministic SQL**: Fast and accurate lookups for strict facts like prerequisites, section times, locations, and instructors.
  * **Semantic Vector Search**: Powered by Gemini embeddings and ChromaDB for discovering courses by interest, career goal, or topic.
* **Strict Grounding & Anti-Hallucination Guardrails**:
  * Agent is strictly constrained to cite only verified data returned by tool calls.
  * Explicit fallback directives to human academic advisors when information is unavailable.
  * Prompt-injection defense that isolates untrusted student inputs.


---

## Tech Stack

* **LLM & Embeddings**: Google Gemini (`gemini-3.8-flash`, `gemini-embedding-001`) via Google GenAI SDK
* **Vector Store**: ChromaDB
* **Relational Database**: SQLite
* **Data Ingestion**: BeautifulSoup4, Requests
* **Environment**: Python 3.14

---

## License
MIT

