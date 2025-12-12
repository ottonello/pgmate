"""Strands conversational agent for PostgreSQL query generation."""

import json
from pathlib import Path
from typing import Optional

from strands import Agent, AnthropicClient, OpenAIClient

from .config import LLMConfig


class PGMateAgent:
    """Conversational agent for PostgreSQL query generation and assistance."""

    def __init__(
        self,
        llm_config: LLMConfig,
        schema_context: str,
        database_id: str,
        memory_dir: Path,
    ):
        """Initialize PGMate agent.

        Args:
            llm_config: LLM configuration
            schema_context: Database schema formatted for LLM
            database_id: Unique identifier for the database
            memory_dir: Directory for storing conversation memory
        """
        self.llm_config = llm_config
        self.schema_context = schema_context
        self.database_id = database_id
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / f"{database_id}.json"

        # Initialize LLM client
        if llm_config.provider == "openai":
            self.client = OpenAIClient(
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
        elif llm_config.provider == "anthropic":
            self.client = AnthropicClient(
                api_key=llm_config.api_key,
                model=llm_config.model,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Load conversation history
        history = self._load_memory()

        # Initialize Strands agent
        self.agent = Agent(
            client=self.client,
            system=system_prompt,
            history=history,
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt with schema context.

        Returns:
            System prompt for the agent
        """
        return f"""You are PGMate, an expert PostgreSQL assistant. Your role is to help users write, optimize, and understand SQL queries for their database.

You have access to the following database schema:

{self.schema_context}

Your capabilities include:
1. Generating SQL queries based on natural language requests
2. Explaining complex queries and their results
3. Suggesting query optimizations and best practices
4. Explaining table relationships and data models
5. Helping with JOIN operations, aggregations, and subqueries
6. Suggesting appropriate indexes for performance

Guidelines:
- Always generate valid PostgreSQL SQL syntax
- Include comments in complex queries to explain logic
- Suggest EXPLAIN ANALYZE for performance analysis when relevant
- Consider NULL handling and edge cases
- Recommend proper indexing strategies when discussing performance
- Use CTEs (WITH clauses) for better readability when appropriate
- Be mindful of SQL injection and recommend parameterized queries when relevant

When generating queries:
- Use clear, descriptive aliases
- Format queries for readability with proper indentation
- Add helpful comments for complex logic
- Consider performance implications

When the user asks about relationships, provide clear explanations of how tables are connected and what the foreign keys mean in business terms.
"""

    def _load_memory(self) -> list:
        """Load conversation history from disk.

        Returns:
            List of conversation messages
        """
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    data = json.load(f)
                    return data.get("history", [])
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_memory(self):
        """Save conversation history to disk."""
        try:
            with open(self.memory_file, "w") as f:
                json.dump(
                    {
                        "database_id": self.database_id,
                        "history": self.agent.history,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            print(f"Warning: Failed to save conversation memory: {e}")

    def chat(self, message: str) -> str:
        """Send a message to the agent and get response.

        Args:
            message: User message

        Returns:
            Agent response
        """
        response = self.agent.run(message)

        # Save updated conversation history
        self._save_memory()

        return response

    def clear_memory(self):
        """Clear conversation history."""
        self.agent.history = []
        self._save_memory()

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation.

        Returns:
            Summary of conversation length
        """
        num_messages = len(self.agent.history)
        return f"Conversation contains {num_messages} messages"

    def export_history(self, output_file: Optional[Path] = None) -> str:
        """Export conversation history to a file.

        Args:
            output_file: Optional path to export file

        Returns:
            Path to exported file
        """
        if output_file is None:
            output_file = Path(f"pgmate_conversation_{self.database_id}.json")

        with open(output_file, "w") as f:
            json.dump(
                {
                    "database_id": self.database_id,
                    "provider": self.llm_config.provider,
                    "model": self.llm_config.model,
                    "history": self.agent.history,
                },
                f,
                indent=2,
            )

        return str(output_file)
