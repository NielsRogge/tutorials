import argparse
import anyio
import os

from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition, query, AssistantMessage, ResultMessage, TextBlock
from claude_agent_sdk.types import McpStdioServerConfig


async def database_manager_example(prompt: str):
    """Example with MongoDB MCP."""
    print("=== MongoDB MCP Example ===")

    # Get connection string from environment variable
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    if not connection_string:
        raise ValueError(
            "MONGODB_CONNECTION_STRING environment variable not set. "
            "Please create a .env file or set the environment variable."
        )

    options = ClaudeAgentOptions(
        # subagents
        agents={
            "database_reader": AgentDefinition(
                description="Reads a MongoDB database",
                prompt="You are a database reader. You are able to list all databases and collections in an existing MongoDB database instance, count the number of documents in a collection, and get the schema and storage size of a collection.",
                tools=["list-databases", "list-collections", "count", "collection-schema", "collection-storage-size"],
                model="sonnet"
            ),
            "database_writer": AgentDefinition(
                description="Writes to a MongoDB database",
                prompt="You are a database writer. You are able to insert, update, or delete data in an existing MongoDB database instance. You are also able to create search indexes on the database.",
                tools=["insert-many", "create-index", "update-many", "drop-database", "drop-collection"],
                model="sonnet"
            ),
            "database_querier": AgentDefinition(
                description="Queries a MongoDB database",
                prompt="You are a database querier. You are able to query a MongoDB database instance and return the results in a structured format.",
                tools=["find"],
                model="sonnet"
            ),
        },
        mcp_servers={
            "mongodb": McpStdioServerConfig(
                command="npx",
                args=["-y", "mongodb-mcp-server@latest"],
                env={
                    "MDB_MCP_CONNECTION_STRING": connection_string
                }
            )
        },
        permission_mode='bypassPermissions',  # Automatically grant permissions for all tools
        setting_sources=["user", "project"],  # Insert the CLAUDE.md file into the system prompt
    )

    async for message in query(
        prompt=prompt,
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
        elif isinstance(message, ResultMessage) and message.total_cost_usd and message.total_cost_usd > 0:
            print(f"\nCost: ${message.total_cost_usd:.4f}")
    print()


async def main(prompt: str):
    """Run the multiple agents example."""
    await database_manager_example(prompt=prompt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=str, required=False, default="Return all collections in the database")
    args = parser.parse_args()
    anyio.run(main, args.prompt)