# PGMate Implementation Plan

## Overview
Build a CLI tool for PostgreSQL query generation using Strands conversational agent with memory.

## Phase 1: Project Setup & Dependencies
- [ ] Add required dependencies to pyproject.toml:
  - `psycopg2-binary` or `psycopg[binary]` for PostgreSQL connection
  - `python-dotenv` for environment configuration
  - `strands` SDK for conversational agent
  - `openai` (default provider)
  - `anthropic` (optional provider)
  - `click` or `typer` for CLI interface
- [ ] Create `.env.example` file with template configuration
- [ ] Create basic project structure (modules/packages)

## Phase 2: Configuration Management
- [ ] Create `config.py` module to:
  - Load environment variables from .env file
  - Define configuration schema (database connection, LLM provider, model)
  - Validate required configurations
  - Support defaults (OpenAI as default provider)

## Phase 3: Database Connection & Schema Extraction
- [ ] Create `database.py` module to:
  - Establish PostgreSQL connection using config
  - Extract schema information:
    - Tables and views
    - Columns (names, types, constraints)
    - Primary keys
    - Foreign keys and relationships
    - Indexes
  - Format schema info for agent context
  - Handle multiple schemas if specified

## Phase 4: Strands Agent Setup
- [ ] Create `agent.py` module to:
  - Initialize Strands agent with:
    - Configurable LLM provider (OpenAI default)
    - Configurable model
    - Database schema as context
  - Implement memory storage:
    - Store per database (use database name/connection string hash)
    - Local file-based storage (JSON/SQLite)
    - Load and persist conversation history
  - Define agent tools:
    - Schema query tool
    - Relationship exploration tool
    - Query validation tool (optional)

## Phase 5: CLI Interface
- [ ] Create interactive CLI in `main.py`:
  - Welcome message and help text
  - Load configuration on startup
  - Connect to database and extract schema
  - Initialize agent with schema context
  - Conversation loop:
    - Accept user input
    - Send to agent
    - Display agent responses
    - Handle special commands (/help, /exit, /clear, etc.)
  - Graceful error handling and shutdown

## Phase 6: Testing & Validation
- [ ] Test database connection with user's .env configuration
- [ ] Test schema extraction with actual database
- [ ] Test agent conversation and query generation
- [ ] Test memory persistence across sessions
- [ ] Validate different LLM providers work correctly

## Phase 7: Documentation
- [ ] Update README.md with:
  - Installation instructions
  - Configuration guide
  - Usage examples
  - Features list
- [ ] Add inline code documentation

## Implementation Notes
- Commit after each successful phase/feature
- Ask user for verification when needed
- Request .env file setup before testing database connectivity
- Update this plan if changes are required during implementation

## Current Status
Phase 1 in progress
