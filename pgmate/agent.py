"""Strands conversational agent for PostgreSQL query generation."""

from pathlib import Path
from typing import Optional

from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.models.openai import OpenAIModel
from strands.session.file_session_manager import FileSessionManager

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

        # Initialize LLM model
        if llm_config.provider == "openai":
            model = OpenAIModel(
                client_args={"api_key": llm_config.api_key},
                model_id=llm_config.model,
                params={"temperature": 0.7},
            )
        elif llm_config.provider == "anthropic":
            model = AnthropicModel(
                client_args={"api_key": llm_config.api_key},
                model_id=llm_config.model,
                params={"temperature": 0.7},
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Initialize session manager for persistent memory
        self.session_manager = FileSessionManager(
            session_id=database_id,
            storage_dir=str(memory_dir),
        )

        # Initialize Strands agent
        # Disable default printing handler to avoid duplicate output
        self.agent = Agent(
            model=model,
            system_prompt=system_prompt,
            session_manager=self.session_manager,
            callback_handler=None,
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

    def chat(self, message: str) -> str:
        """Send a message to the agent and get response.

        Args:
            message: User message

        Returns:
            Agent response
        """
        # Call the agent (Strands automatically persists via FileSessionManager)
        result = self.agent(message)

        # Extract the text response from the result
        # The result object has the response text
        if hasattr(result, 'content'):
            return result.content
        elif hasattr(result, 'text'):
            return result.text
        else:
            return str(result)

    def clear_memory(self):
        """Clear conversation history."""
        # Clear messages in the agent
        self.agent.messages.clear()

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation.

        Returns:
            Summary of conversation length
        """
        num_messages = len(self.agent.messages)
        return f"Conversation contains {num_messages} messages"

    def export_history(self, output_file: Optional[Path] = None) -> str:
        """Export conversation history to a file.

        Args:
            output_file: Optional path to export file

        Returns:
            Path to exported file
        """
        import json

        if output_file is None:
            output_file = Path(f"pgmate_conversation_{self.database_id}.json")

        # Convert messages to serializable format
        messages_data = []
        for msg in self.agent.messages:
            # Strands messages have role and content attributes
            msg_dict = {
                "role": getattr(msg, "role", "unknown"),
                "content": getattr(msg, "content", str(msg)),
            }
            messages_data.append(msg_dict)

        with open(output_file, "w") as f:
            json.dump(
                {
                    "database_id": self.database_id,
                    "provider": self.llm_config.provider,
                    "model": self.llm_config.model,
                    "messages": messages_data,
                },
                f,
                indent=2,
            )

        return str(output_file)
