## Web UI

<https://github.com/blackboardsh/electrobun>

Electrobun aims to be a complete solution-in-a-box for building,  
updating, and shipping ultra fast, tiny, 
and cross-platform desktop applications written in Typescript.  
Under the hood it uses bun to execute the main process and to bundle webview typescript, 
and has native bindings written in zig.

### DataStar

Datastar is **not a Python web framework** — it's a **frontend JavaScript library** (similar to HTMX) that enables hypermedia-driven, reactive UIs without writing custom JavaScript. 

It works by:

- Using `data-*` HTML attributes to bind reactivity to elements (e.g., `data-text`, `data-on-load`)
- Communicating with the backend via **Server-Sent Events (SSE)** rather than traditional JSON REST calls
- Allowing the backend to push HTML fragments or state signals to the browser, which Datastar then patches into the DOM

The core idea is that your backend drives the UI — you return HTML snippets (or signal updates) over SSE and Datastar applies them reactively, eliminating the need for a separate frontend framework like React or Vue.

---

## What is `datastar-py`?

`datastar-py` is the official Python SDK for working with Datastar. Since Datastar sends responses back to the browser using SSE, the SDK provides helpers for creating those SSE responses, formatting the events, reading signals from the frontend, and generating the `data-*` HTML attributes.

It's **framework-agnostic** at its core but ships with first-class integration helpers for several Python frameworks.

## Relationship to FastAPI and Litestar

The event generator can be used with any framework. 
There are also custom helpers included for FastAPI, FastHTML, Litestar, Django, Quart, Sanic, and Starlette. Framework-specific helpers are kept in their own packages — e.g., `datastar_py.fastapi` or `datastar_py.litestar`.

So the relationship is: **FastAPI and Litestar are your backend HTTP frameworks; `datastar-py` is a library you bolt on to make SSE responses easy.** Here's the pattern:

```python
# FastAPI example
from fastapi import FastAPI
from datastar_py.fastapi import DatastarResponse
from datastar_py import ServerSentEventGenerator as SSE

app = FastAPI()

@app.get("/updates")
async def updates():
    async def stream():
        while True:
            yield SSE.patch_elements("<div id='output'>Hello from server!</div>")
            await asyncio.sleep(1)
    return DatastarResponse(stream())
```

The same pattern works with Litestar — you just import from `datastar_py.litestar` instead.


### The Bigger Picture

| Layer | Role |
|---|---|
| **Litestar / FastAPI** | Python ASGI backend — handles routing, DI, validation |
| **datastar-py** | Python SDK — formats SSE events, reads frontend signals |
| **Datastar JS** | Frontend library — patches DOM based on SSE events |

This stack is an alternative to the typical SPA approach (React/Vue + REST API). Instead of your backend returning JSON that a JS framework renders, your backend returns **HTML fragments over SSE** that Datastar patches directly into the page. It's closer to the HTMX philosophy but leans more into SSE streaming and reactive signals.

---

## FastAPI vs Litestar

If you're choosing a backend for Datastar, the two frameworks differ in that FastAPI is more popular with a larger ecosystem (Pydantic-based, Starlette under the hood),   
while Litestar is about twice as fast as FastAPI because it uses `msgspec` instead of Pydantic for serialization and has less overhead in its request/response cycle. 

For SSE-heavy workloads like Datastar, Litestar's performance advantage could be meaningful since you're maintaining long-lived streaming connections.

https://talkpython.fm/episodes/show/537/datastar-modern-web-dev-simplified

## Web Sockets

https://habr.com/ru/articles/979614/

## Web tools

https://viteplus.dev/

https://cpojer.net/posts/fastest-frontend-tooling

https://docs.expo.dev/get-started/introduction/ for building iOS and Android app

## Web components

https://kumo-ui.com/ 
