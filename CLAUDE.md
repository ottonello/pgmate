This is a CLI tool that is meant to ease SQL queries generation for PostgreSQL.

Requirements:
- Strands conversational agent with memory (locally stored, per database)
- Uses a dotenv file, or existing env vars as configuration
- Model and provider are configurable (defaults to OpenAI)
- Connects to the configured postgresql database and schema/schemas
- Tool to extracts the table information, relationships etc.
- This table information is used as context for the agent
- The user can ask the agent to generate and refine queries from the knowledge base
- The user can ask about relationships, suggested improvements

Procedure:
- Generate an execution plan, save it to PLAN.md
- Plan ahead of every step and update the plan if changes were required
- Ask user to verify or when there are questions/doubts
- Test your changes, ask the user to add a .env file with the required config vars so the app can connect to the database
- After every successful change, commit to git
