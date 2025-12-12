"""Main CLI interface for PGMate."""

import sys
from pathlib import Path

import click

from .agent import PGMateAgent
from .config import Config
from .database import DatabaseSchemaExtractor


@click.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to .env file (default: .env in current directory)",
)
def cli(env_file: Path = None):
    """PGMate - PostgreSQL query generation assistant.

    An interactive CLI tool that uses AI to help you write, optimize,
    and understand SQL queries for your PostgreSQL database.
    """
    click.echo("🐘 PGMate - PostgreSQL Query Assistant")
    click.echo("=" * 50)

    # Load configuration
    try:
        config = Config.from_env(str(env_file) if env_file else None)
        click.echo(f"✓ Configuration loaded")
        click.echo(f"  Database: {config.database.database}")
        click.echo(f"  Schema: {config.database.schema}")
        click.echo(f"  LLM Provider: {config.llm.provider} ({config.llm.model})")
    except ValueError as e:
        click.echo(f"✗ Configuration error: {e}", err=True)
        click.echo("\nPlease create a .env file with required configuration.")
        click.echo("See .env.example for template.")
        sys.exit(1)

    # Connect to database and extract schema
    click.echo("\nConnecting to database...")
    try:
        with DatabaseSchemaExtractor(config.database) as db:
            database_id = db.get_database_id()
            schema_context = db.format_schema_for_llm()
            click.echo(f"✓ Connected to database")

            # Show schema summary
            schema = db.extract_schema()
            num_tables = len(schema["tables"])
            num_relationships = len(schema["relationships"])
            click.echo(f"  Tables: {num_tables}")
            click.echo(f"  Relationships: {num_relationships}")

    except Exception as e:
        click.echo(f"✗ Database connection error: {e}", err=True)
        sys.exit(1)

    # Initialize agent
    click.echo("\nInitializing AI assistant...")
    try:
        agent = PGMateAgent(
            llm_config=config.llm,
            schema_context=schema_context,
            database_id=database_id,
            memory_dir=config.memory_dir,
        )
        click.echo(f"✓ Assistant ready")
        click.echo(f"  Memory: {config.memory_dir / database_id}.json")
    except Exception as e:
        click.echo(f"✗ Agent initialization error: {e}", err=True)
        sys.exit(1)

    # Start interactive session
    click.echo("\n" + "=" * 50)
    click.echo("Type your questions or requests. Special commands:")
    click.echo("  /help     - Show this help message")
    click.echo("  /clear    - Clear conversation history")
    click.echo("  /export   - Export conversation to file")
    click.echo("  /schema   - Show database schema")
    click.echo("  /exit     - Exit PGMate")
    click.echo("=" * 50 + "\n")

    # Main conversation loop
    while True:
        try:
            user_input = click.prompt("\nYou", type=str, prompt_suffix=": ")

            if not user_input.strip():
                continue

            # Handle special commands
            if user_input.startswith("/"):
                command = user_input.lower().strip()

                if command == "/exit":
                    click.echo("\nGoodbye! 👋")
                    break

                elif command == "/help":
                    click.echo("\nSpecial commands:")
                    click.echo("  /help     - Show this help message")
                    click.echo("  /clear    - Clear conversation history")
                    click.echo("  /export   - Export conversation to file")
                    click.echo("  /schema   - Show database schema")
                    click.echo("  /exit     - Exit PGMate")
                    continue

                elif command == "/clear":
                    agent.clear_memory()
                    click.echo("✓ Conversation history cleared")
                    continue

                elif command == "/export":
                    output_file = agent.export_history()
                    click.echo(f"✓ Conversation exported to {output_file}")
                    continue

                elif command == "/schema":
                    click.echo("\n" + schema_context)
                    continue

                else:
                    click.echo(f"Unknown command: {command}")
                    click.echo("Type /help for available commands")
                    continue

            # Send message to agent
            try:
                response = agent.chat(user_input)
                click.echo(f"\nPGMate: {response}")
            except Exception as e:
                click.echo(f"✗ Error getting response: {e}", err=True)

        except (KeyboardInterrupt, EOFError):
            click.echo("\n\nGoodbye! 👋")
            break
        except Exception as e:
            click.echo(f"✗ Unexpected error: {e}", err=True)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
