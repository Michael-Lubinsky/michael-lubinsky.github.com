# Learn MCP (Model Context Protocol) with Python on MacBook

The best way to understand MCP is to implement a small MCP server and client in Python, run them locally on your MacBook, and inspect the messages they exchange.

Since you already have Python experience, I suggest learning MCP from the protocol level rather than starting with an AI agent framework.

We'll build a working example using the official Python MCP SDK.

## 1. What is MCP?

MCP (Model Context Protocol) is an open protocol that standardizes communication between AI applications and external tools, data sources, and services.

For example, imagine you have an AI assistant that needs to query a Databricks database.

AI Application (MCP Host)

Claude Desktop, VS Code, or custom Python application

MCP Client

MCP Server (Python)

Exposes tools, resources, and prompts

Python connector / SQL API

Databricks

Tables, queries, and metadata

The MCP server is an adapter between the AI application and your existing systems. It does not require an LLM inside the server.

### Three main MCP capabilities

| Capability | Purpose                           | Example              |
| ---------- | --------------------------------- | -------------------- |
| Tools      | Execute operations                | `execute_sql(query)` |
| Resources  | Expose readable data              | `schema://telemetry` |
| Prompts    | Provide reusable prompt templates | `analyze_telemetry`  |

The client discovers these capabilities and decides how to use them, often under the control of an AI application.

## 2. How MCP works internally

MCP uses JSON-RPC 2.0 messages. JSON-RPC is a request-response protocol with method names, parameters, and identifiers.

For example, a client may send:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 10,
      "b": 20
    }
  }
}
```

The server might respond:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "30"
      }
    ],
    "isError": false
  }
}
```

You do not have to implement JSON-RPC parsing yourself. The MCP Python SDK handles message framing, serialization, and dispatching.

MCP supports local communication using stdio (standard input/output) and remote communication using Streamable HTTP.

For learning, we'll start with stdio because it needs no web server or network configuration.

## 3. Install MCP on your MacBook

Open Terminal and create a new project:

```bash
mkdir mcp-tutorial
cd mcp-tutorial

python3 --version
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install "mcp[cli]" pytest anyio
```

The current official MCP Python SDK v2 requires Python 3.11 or newer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://py.sdk.modelcontextprotocol.io\&sz=32)

MCP Python SDK



We'll create three files:

```
mcp-tutorial/
├── server.py
├── client.py
└── test_server.py
```

## 4. Write your first MCP server

Create `server.py`:

```
from mcp.server import MCPServermcp = MCPServer("MyPythonServer")@mcp.tool()def add(a: int, b: int) -> int:    """Add two integers."""    return a + b@mcp.tool()def multiply(a: int, b: int) -> int:    """Multiply two integers."""    return a * b@mcp.resource("info://server")def server_info() -> str:    """Return information about this server."""    return "Python MCP tutorial server"@mcp.prompt()def explain_math(operation: str) -> str:    """Create a prompt explaining a math operation."""    return f"Explain the {operation} operation with examples."if __name__ == "__main__":    mcp.run()
```

Notice that the code looks like ordinary Python.

The decorators register the three MCP capabilities, while the SDK automatically generates tool schemas from type annotations and function descriptions.

The current v2 SDK uses `MCPServer`. Older tutorials may use `FastMCP` from `mcp.server.fastmcp`, which belongs to the v1 API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://py.sdk.modelcontextprotocol.io\&sz=32)

MCP Python SDK+1



## 5. Test your server with MCP Inspector

The official MCP Inspector is particularly useful for learning because it lets you inspect and call MCP methods without involving an LLM.

First, verify that Node.js and `npx` are installed:

```
node --version
npx --version
```

If needed, install Node.js using Homebrew:

```
brew install node
```

Then run:

```
mcp dev server.py
```

This launches MCP Inspector. Open the local URL printed in Terminal.

[How to use MCP Inspector. This article is part of my MCP… | by Laurent Kubaski | Medium](https://images.openai.com/static-rsc-4/p14uE7bH6MIwlPSUS8Z2OVsPV82IXO3rjQtpAUaCOOYuACfs077NNYOdcwb4pYHmoxrHIBliWcMCkEmbeLcxsJkhKOC0nj4_ZG-_U35dsbmtdOLEL-f9tm_AktXdn5WLnhe3gT13cZulGpWHmAPeWglw-9zUkVPYM-txi_ZcO0A?purpose=inline)

[Securing MCP Servers with Spring AI](https://images.openai.com/static-rsc-4/uHYjP9jv20cw50omgZGgepDnqNEjt1ltovLtGPyrt1jIMPpVUyZl_ezhkcbhxZo8VjLc66fPIP753sUu9Ej2r9fL_ybISOHFFT18hTSq17mFZk7HfraH5Bi6_YDaZ0AkB0j011ggymLsALBs57H5JtHzz6gHeWo8kP2VnJ8m7VI?purpose=inline)

[MCP实战：基于MCP和deepseek搭建天气查询Agent（附完整项目源码）\_mcp deepseek-CSDN博客](https://images.openai.com/static-rsc-4/nZO53JtafxdvptPeSX1g2gLVkjmR2q2rFAKtcqFG48rnPkD-JSJ0OotGMVlqmJsrWdNpgdEY3NwdOKCcuklvjtORWdFsMTggh59a1ubupzxQ4tAknnWkkHHJj63UukRbgSx6Ha5XRj09VEzC6jr1kJLVtJVWV6GlOOjvHP1WED4?purpose=inline)

7

In Inspector, connect to the server and select the Tools tab. You should see `add` and `multiply`.

Select `add`, enter `a = 10` and `b = 20`, and execute the tool.

Expected result:

```
30
```

Also explore the Resources and Prompts tabs.

The Inspector provides both a browser interface and command-line testing capabilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 6. Write your own Python MCP client

Now let's call the server from another Python program, without Inspector.

Create `client.py`:

```
import asynciofrom mcp import Clientasync def main():    # Connect directly to the server in memory.    from server import mcp    async with Client(mcp) as client:        # Discover tools        tools = await client.list_tools()        for tool in tools:            print("Tool:", tool.name)        # Execute tool        result = await client.call_tool(            "add",            {"a": 10, "b": 20}        )        print("Result:", result.structured_content)if __name__ == "__main__":    asyncio.run(main())
```

Run:

```
python client.py
```

Expected output:

```
Tool: add
Tool: multiply
Result: {'result': 30}
```

This example uses an in-memory connection, supported by the v2 SDK. It is convenient for understanding the API, but it does not exercise the actual stdio transport.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://py.sdk.modelcontextprotocol.io\&sz=32)

MCP Python SDK



For full protocol testing, use Inspector or connect a client to a subprocess or HTTP endpoint.

## 7. Automated testing with pytest

Create `test_server.py`:

```
import pytestfrom mcp import Clientfrom server import mcp@pytest.mark.anyioasync def test_add():    async with Client(mcp) as client:        result = await client.call_tool(            "add",            {"a": 10, "b": 20}        )        assert result.structured_content == {            "result": 30        }@pytest.mark.anyioasync def test_multiply():    async with Client(mcp) as client:        result = await client.call_tool(            "multiply",            {"a": 6, "b": 7}        )        assert result.structured_content == {            "result": 42        }@pytest.fixturedef anyio_backend():    return "asyncio"
```

Execute:

```
pytest -v
```

Expected result:

```
test_server.py::test_add PASSED
test_server.py::test_multiply PASSED

2 passed
```

This verifies the server's tool registration, request dispatch, and result handling.

## 8. Understand the actual MCP protocol lifecycle

When a real MCP client connects to a server, the communication follows this sequence:

Simplified MCP initialization, discovery, and tool execution

The important operations are:

| MCP method                  | Purpose                                     |
| --------------------------- | ------------------------------------------- |
| `initialize`                | Negotiate protocol version and capabilities |
| `notifications/initialized` | Complete initialization handshake           |
| `tools/list`                | Discover available tools                    |
| `tools/call`                | Execute a tool                              |
| `resources/read`            | Read a resource                             |
| `prompts/get`               | Retrieve a prompt                           |

The protocol handles capability negotiation, request IDs, errors, notifications, and tool results.

## 9. Next experiment: expose MCP over HTTP

After understanding local communication, modify the last two lines of `server.py`:

```
if __name__ == "__main__":    mcp.run(        transport="streamable-http",        host="127.0.0.1",        port=8000    )
```

Start the server:

```
python server.py
```

The MCP endpoint is:

```
http://127.0.0.1:8000/mcp
```

You can now use an HTTP MCP client:

```
import asynciofrom mcp import Clientasync def main():    async with Client(        "http://127.0.0.1:8000/mcp"    ) as client:        result = await client.call_tool(            "add",            {"a": 5, "b": 7}        )        print(result.structured_content)asyncio.run(main())
```

The result should be `{'result': 12}`.

Unlike stdio, this uses a network endpoint. Streamable HTTP is the recommended transport for new remotely accessible MCP services.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://py.sdk.modelcontextprotocol.io\&sz=32)

MCP Python SDK



## 10. What I recommend learning next

Here is a practical progression:

Your MCP learning checklist

0 of 6

1\. Implement an MCP server

Tools, resources, prompts

2\. Build a Python MCP client

Discovery and tool calls

3\. Inspect JSON-RPC messages

Initialization, schemas, errors

4\. Test stdio and HTTP transports

Subprocesses and network communication

5\. Build a Databricks MCP server

Read-only SQL, table metadata, authentication

6\. Connect an AI agent

LLM tool selection and execution

For your data engineering background, the most interesting project would be a read-only Databricks MCP server exposing `list_tables`, `describe_table`, and `execute_select_query`. That would let you compare MCP directly with a traditional REST API and with agent frameworks such as LangGraph.

### Official references

- [MCP specification and documentation](https://modelcontextprotocol.io/?utm_source=chatgpt.com)
- [Official Python MCP SDK v2](https://py.sdk.modelcontextprotocol.io/?utm_source=chatgpt.com)
- [Python SDK GitHub repository](https://github.com/modelcontextprotocol/python-sdk?utm_source=chatgpt.com)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector?utm_source=chatgpt.com)

My suggestion: After completing this first example, implement the same simple server without the MCP SDK, using raw JSON-RPC over stdin/stdout. That exercise will make the distinction between the MCP protocol, its transport, and the SDK much clearer.
