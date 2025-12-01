# Using DeepSeek v3.2 and the Claude Agents SDK with MongoDB MCP

This repository showcases how to combine the following amazing pieces of technology:

- [DeepSeek v3.2](https://api-docs.deepseek.com/news/news251201) which just got released on Hugging Face, rivaling the best closed-source models such as GPT-5 and Claude Opus 4.5
- the [Claude Agents SDK](https://platform.claude.com/docs/en/agent-sdk/overview) (formerly called Claude Code SDK)
- the official [MongoDB MCP server](https://fandf.co/3LGhRN8).

## Overview

The MongoDB MCP server allows LLMs like DeepSeek v3.2, Claude to interact with your MongoDB databases directly - querying data, listing collections, analyzing schemas, and more. This integration enables powerful database operations through natural language, having agents automatically writing to a database, and more.

In this tutorial, we make use of the Claude Agents SDK, which is one of the many agent frameworks out there, besides the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), Google's [ADK](https://google.github.io/adk-docs/), [LangGraph](https://www.langchain.com/langgraph), [Agno](https://docs.agno.com/), [Pydantic AI](https://ai.pydantic.dev/) and many more. What's amazing is that you can just replace the Claude model by an open weights model like the brand new [DeepSeek v3.2](https://huggingface.co/collections/deepseek-ai/deepseek-v32) (as explained [here](https://api-docs.deepseek.com/guides/anthropic_api)), the only thing to add is the following:

```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=${YOUR_API_KEY}
export API_TIMEOUT_MS=600000
export ANTHROPIC_MODEL=deepseek-chat
export ANTHROPIC_SMALL_FAST_MODEL=deepseek-chat
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

Usually, I recommend trying out a framework which finds the right level of abstraction: providing the right building blocks for you to build an agent without abstracting away too much which would it make hard to debug. Additionally, I recommend to always use models which correspond to the creators of the framework: if you intend to use Gemini, then Google's ADK is the recommendation. If you intent to use GPT-5, then the OpenAI Agents SDK is the recommendation, and so on. This is because the model providers know their models better than anyone else, so they'll make sure it works best with a framework developed by them.

### Why Claude Agents SDK?

The reason I went for the Claude Agents SDK in this case was because it provides the exact same environment (also called “harness”) around the LLM which powers [Claude Code](https://www.claude.com/product/claude-code), the popular coding tool that competes with Cursor and others. This means that it comes with the same tooling: support for subagents, Skills, memory, hooks, slash commands, and … MCP. The Model Context Protocol by Anthropic enables agents to connect with tools in a standardized way, similar to how HTTP standardizes the way web browsers connect with web servers. By leveraging the Claude Agents SDK, we can benefit from all the [context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) tricks that Anthropic has baked into Claude Code.

### Context engineering trick: subagents

In this tutorial, we make use of [subagents](https://platform.claude.com/docs/en/agent-sdk/subagents), which is one of the popular ways to deal with "context rot" of LLMs. As you might know, current LLM agents (powered by models like Claude, GPT-5, Gemini 3,...) have a major limitation: their context window is limited. Even though model providers claim to support context windows of 200k tokens up to a million and more, in reality the performance starts to degrade once you provide more than a 100k tokens. This makes the LLM quickly get confused, doing the wrong things, choosing the wrong tools, and so on. This problem is known as “context rot” and was first shown by research done at [Chroma](https://research.trychroma.com/context-rot).

By creating various subagents, each of which is specialized to handle one specific task, the main agent (oftentimes called the "orchestrator" agent) will get less confused. By leveraging subagents, the context window of the main agent doesn't get polluted when solving subproblems. It can simply hand off subtasks to different subagents, each of which can leverage specific tools which are tailored towards the task it is solving. Limiting the number of tools has a positive impact on the performance as the main LLM agent will be less confused. I recommend this read to learn more about the rise of subagents: https://www.philschmid.de/the-rise-of-subagents.

In our example, we created 3 subagents, each of which has a different system prompt and which only uses its own set of tools from the MongoDB MCP server:

- a reader agent, able to perform read-only operations on the database
- a writer agent, able to write, update and delete data to and from the database
- a query agent, able to find the most relevant data given a user query.

The official MongoDB MCP server comes with 26 tools by default (they are listed [here](https://github.com/mongodb-js/mongodb-mcp-server?tab=readme-ov-file#%EF%B8%8F-supported-tools)). Rather than having a single agent which has access to all of these tools, we can split it up into specialized subagent, each of which only has access to a select amount of tools required to perform its task, whether it's reading data, writing data or querying data.

## Setup

First, head over to MongoDB to create a new database: https://www.mongodb.com. Click "Get Started" and then create your first cluster. By default, a dummy database called "sample_mflix" is created which contains some sample collections about movies, theaters and comments about those movies.

Next, verify the connection to your database instance by whitelisting your IP address and obtaining the connection string.

1. **Install dependencies:**
   
Next, install this project with the following command:
   
```bash
uv sync
```

2. **Set your MongoDB connection string:**

Next, create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add the following environment variables:

```bash
MONGODB_CONNECTION_STRING=mongodb+srv://your-username:your-password@your-cluster.mongodb.net/
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=your-api-token
API_TIMEOUT_MS=600000
ANTHROPIC_MODEL=deepseek-chat
ANTHROPIC_SMALL_FAST_MODEL=deepseek-chat
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

## Usage

### Run the basic example:

```bash
# Using .env file (recommended)
uv run --env-file .env main.py

# Or with a custom prompt
uv run --env-file .env main.py --prompt "How many movies are in the database?"

uv run --env-file .env main.py --prompt "What are the top 10 most recent movies?"

uv run --env-file .env main.py --prompt "Analyze the schema of all collections in the database"

uv run --env-file .env main.py --prompt "What's the size of the movies collection?"
```

### More fun: adding actual real-world data

Besides the dummy movie data that MongoDB provides, I also experimented with adding real-world data from Hugging Face into MongoDB which the agent can then query. Here I leveraged the [cfahlgren1/hub-stats](https://huggingface.co/datasets/cfahlgren1/hub-stats) dataset which contains useful statistics about models, datasets, papers and more on the hub. One can run the following script to migrate it to MongoDB:

```bash
uv run --env-file .env load_hf_to_mongodb.py
```

Next, you should be able to ask questions like:

```bash
uv run --env-file .env main.py --prompt "Give me the top 10 most popular models on the hub?"
```

## Configuration

The MongoDB MCP server can be configured in two ways:

### Method 1: Environment Variable (Recommended)

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "mongodb": McpStdioServerConfig(
            command="npx",
            args=["-y", "mongodb-mcp-server@latest", "--readOnly"],
            env={
                "MDB_MCP_CONNECTION_STRING": "your-connection-string"
            }
        )
    }
)
```

### Method 2: Command Argument

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "mongodb": McpStdioServerConfig(
            command="npx",
            args=[
                "-y",
                "mongodb-mcp-server@latest",
                "--connectionString",
                "your-connection-string"
            ]
        )
    }
)
```

## Resources

- [Claude Agent SDK Python Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [MongoDB MCP Server Documentation](https://www.mongodb.com/docs/mcp-server/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
