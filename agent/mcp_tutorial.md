# Learn MCP (Model Context Protocol) with Python on macOS

This tutorial builds an MCP server, tests it with MCP Inspector, and calls it from Python. It uses the established `FastMCP` API in the official Python MCP SDK. Check the installed SDK documentation if you are using a newer major version.

## 1. MCP in a nutshell

MCP standardizes communication between AI hosts/clients and servers exposing **tools**, **resources**, and **prompts**. Messages use JSON-RPC 2.0. Local servers commonly communicate over **stdio**; remote servers commonly use **Streamable HTTP**.

A typical exchange is: `initialize` → `notifications/initialized` → `tools/list` → `tools/call`.

## 2. Set up Python

```bash
mkdir -p mcp-tutorial
cd mcp-tutorial
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'mcp[cli]' pytest
```

The examples below target the `FastMCP` interface available in the official MCP Python SDK 1.x. For reproducibility, use a compatible 1.x release:

```bash
python -m pip install 'mcp[cli]>=1.0,<2.0'
```

## 3. Create an MCP server

Save as **server.py**:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MyPythonServer")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


@mcp.resource("info://server")
def server_info() -> str:
    """Return information about this server."""
    return "Python MCP tutorial server"


@mcp.prompt()
def explain_math(operation: str) -> str:
    """Generate a prompt explaining a mathematical operation."""
    return f"Explain the {operation} operation with examples."


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Do not write debugging output to standard output when using stdio: it is reserved for protocol messages. Use stderr for diagnostics.

## 4. Test with MCP Inspector

Install Node.js if necessary:

```bash
brew install node
```

Launch Inspector:

```bash
mcp dev server.py
```

Open the URL printed in Terminal, connect, inspect **Tools**, **Resources**, and **Prompts**, and call `add` with `a=10`, `b=20`. The result should be 30.

Alternatively, Inspector can launch the Python server directly:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server.py
```

## 5. Write a Python MCP client over stdio

Save as **client.py**:

```python
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_path = Path(__file__).with_name("server.py")
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(" -", tool.name)

            result = await session.call_tool(
                "add", arguments={"a": 10, "b": 20}
            )
            print("Result:", result.content)


if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
python client.py
```

You should see `add`, `multiply`, and a tool result containing `30`.

## 6. Add a pytest integration test

Save as **test_server.py**:

```python
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def call_add():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py"))],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(
                "add", arguments={"a": 10, "b": 20}
            )


def test_add():
    result = asyncio.run(call_add())
    assert not result.isError
    assert any("30" in getattr(item, "text", "") for item in result.content)
```

Run:

```bash
pytest -v
```

## 7. See the JSON-RPC layer

The protocol includes requests such as:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {"a": 10, "b": 20}
  }
}
```

For a stdio server, each JSON-RPC message is sent as a line of JSON. The SDK handles initialization, serialization, message routing, and validation. Use Inspector to see the real exchange rather than sending `tools/call` before initialization.

## 8. Try Streamable HTTP

Create **http_server.py**:

```python
from server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Run:

```bash
python http_server.py
```

With default FastMCP settings, the endpoint is commonly `http://127.0.0.1:8000/mcp`. Check the startup output and your SDK version. In Inspector, choose **Streamable HTTP** and connect to the endpoint.

## 9. Suggested learning exercises

1. Add a `divide(a, b)` tool and test division by zero.
2. Add a resource that exposes a local read-only JSON dataset.
3. Compare tool discovery (`tools/list`) with a traditional REST API's OpenAPI schema.
4. Capture the initialization handshake and inspect protocol-version negotiation.
5. Build a read-only Databricks MCP server with `list_tables`, `describe_table`, and a carefully restricted `execute_select_query` tool. Use proper authorization and query limits.
6. Connect your server to an MCP-compatible AI host and inspect which tools it chooses.

## References

- MCP documentation: https://modelcontextprotocol.io/
- Official Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP Inspector: https://github.com/modelcontextprotocol/inspector
- Python SDK docs: https://py.sdk.modelcontextprotocol.io/

---

**Note:** This is a standalone, version-pinned tutorial. It uses the documented 1.x `FastMCP` / `ClientSession` APIs instead of mixing examples from different SDK major versions. All code blocks in this file have real newline characters and preserve Python indentation.
