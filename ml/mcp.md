## MCP

<https://www.kdnuggets.com/build-your-first-mcp-server-in-python-stateless-spec-edition>

<https://sreenathmenon.com/blog/2026-06-30-mcp-the-port-that-let-ai-touch-the-world/>
<img width="1171" height="1278" alt="image" src="https://github.com/user-attachments/assets/cb38b5c3-b3ad-4360-865a-3aaafe9e6709" />

 <img width="1102" height="1057" alt="image" src="https://github.com/user-attachments/assets/6c49d52f-abb2-452d-86d8-f512086dbba8" />

 <img width="1111" height="702" alt="image" src="https://github.com/user-attachments/assets/fb6fecf3-6a2f-4927-b0a4-9f8665d72d68" />

There is a quieter, more elegant half to this that almost nobody mentions: the client has primitives too. The server can ask the client to do things back. It can request sampling (ask the host’s model to think about something, without the server needing its own model), elicitation (ask the human a clarifying question or for confirmation), and logging. So it is genuinely two-way. The server is not just a vending machine; it can tap the model and the user on the shoulder when it needs them. That bidirectionality is one of the prettiest design choices in the whole thing.

<img width="1063" height="313" alt="image" src="https://github.com/user-attachments/assets/fa1450ee-7b60-4f96-adff-927e593c6923" />



Skills хорошо подходят для локальных, процедурных, основанных на CLI-утилитах сценариев. Например, «возьми ffmpeg, обработай видео, положи результат в этот каталог».
```
MCP лучше подходит там, где нужны:
- авторизация
- RBAC
- аудит действий и observability
- управление доступом к инструментам
- стабильный контракт между агентом и внешней системой
```

<https://news.ycombinator.com/item?id=49779329>

<https://habr.com/ru/companies/otus/articles/1032890/>

<https://habr.com/ru/articles/1082314/>

<https://gofastmcp.com/servers/tools>

<https://habr.com/ru/articles/1044024/>

.mcp.json — это файл конфигурации в корне проекта. В нём ты описываешь какие серверы запускать и с какими параметрами. Claude Code читает этот файл при старте и поднимает все серверы автоматически.
Выглядит это примерно так:
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["/path/to/telegram-mcp/main.py"],
      "env": {
        "SESSION_STRING": "your_session_here"
      }
    }
  }
}
```

<https://news.ycombinator.com/item?id=49906637>

#### https://habr.com/ru/articles/1042470/
FastMCP line: 
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

### Подключение в Claude
В Claude (claude.ai или Claude Desktop): Settings → Connectors → Add custom connector → имя и URL https://mcp.zinin-shturbin.com/mcp. Авторизация тут лишняя (данные публичные, чтение) — подключается одним движением.

#### Test MCP server
```
curl -sD - -X POST https://mcp.zinin-shturbin.com/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2024-11-05","capabilities":{},
                 "clientInfo":{"name":"curl","version":"1"}}}'
```
<https://habr.com/ru/companies/amvera/articles/931874/>
```python
from fastmcp import FastMCP
import json
import datetime

# Создаем сервер
mcp = FastMCP(
    name="Demo Assistant",
    instructions="Ассистент для демонстрации возможностей MCP"
)


# === ИНСТРУМЕНТЫ ===
@mcp.tool
def calculate_age(birth_year: int) -> int:
    """Вычисляет возраст по году рождения"""
    current_year = datetime.datetime.now().year
    return current_year - birth_year

  
@mcp.tool
async def generate_password(length: int = 12) -> str:
    """Генерирует случайный пароль"""
    import random, string
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))

  
# === РЕСУРСЫ ===
@mcp.resource("system://status")
def system_status() -> str:
    """Возвращает статус системы"""
    return json.dumps({
        "status": "online",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0"
    })

    
@mcp.resource("help://{topic}")
def get_help(topic: str) -> str:
    """Возвращает справку по теме"""
    help_docs = {
        "password": "Используйте generate_password для создания безопасных паролей",
        "age": "Используйте calculate_age для вычисления возраста",
        "status": "Проверьте system://status для мониторинга системы"
    }
    return help_docs.get(topic, f"Справка по теме '{topic}' не найдена")

  
# === ПРОМПТЫ ===
@mcp.prompt
def security_check(action: str) -> str:
    """Создает промпт для проверки безопасности действия"""
    return f"""
    Ты специалист по информационной безопасности. 
    Проанализируй это действие на предмет безопасности: {action}
    
    Оцени:
    1. Потенциальные риски
    2. Рекомендации по безопасности  
    3. Альтернативные подходы
    """

  
@mcp.prompt
def explain_result(tool_name: str, result: str) -> str:
    """Объясняет результат работы инструмента"""
    return f"""
    Объясни пользователю простыми словами результат работы инструмента '{tool_name}':
    
    Результат: {result}
    
    Сделай объяснение понятным и полезным.
    """

  
# Запуск сервера
if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

<https://habr.com/ru/companies/avito/articles/1056028/>

<https://realpython.com/python-mcp/>

<https://realpython.com/python-news-august-2026/>

<https://realpython.com/courses/connecting-llms-data-python-mcp-servers/>

<https://modelcontextprotocol.io/>

<https://habr.com/ru/articles/1069588/>

<https://habr.com/ru/companies/amvera/articles/931874/>

<https://www.youtube.com/watch?v=kIjt0Jt94nI&list=PLtPJ9lKvJ4ojl7flbGuiKDm30FPUjHDba> Протокол MCP 

<https://inventwithpython.com/blog/basic-mcp-python-example.html>

<https://habr.com/ru/companies/otus/articles/1032890/>

<https://habr.com/ru/companies/bothub/articles/1035002/>

<https://habr.com/ru/articles/1015072/>

<https://habr.com/ru/articles/1033388/>

<https://habr.com/ru/articles/1027508/>

<https://habr.com/ru/companies/bitrix/articles/1009150/>

<https://news.ycombinator.com/item?id=47380270>

<https://chrlschn.dev/blog/2026/03/mcp-is-dead-long-live-mcp/>

<https://github.com/punkpeye/awesome-mcp-clients>

<https://mcp.so/>

<https://habr.com/ru/articles/890740/>

https://habr.com/ru/articles/862312/

https://habr.com/ru/articles/910524/

https://habr.com/ru/articles/899088/

https://habr.com/ru/articles/893822/

### MCP Host: 
Это приложение, где живет LLM (например, Claude Desktop или Cursor IDE). Хост хочет получить доступ к внешним возможностям/данным

### MCP Client: 
Компонент внутри хоста. Для каждого внешнего сервиса создается клиент, который устанавливает соединение с соответствующим сервером и общается с ним по протоколу MCP

### MCP Server: 
Внешняя программа или сервис, который предоставляет хосту определенные данные или функции по протоколу MCP. Сервер может быть локальным (доступ к файлам на компьютере) или удаленным (обертка над API или, например, БД). Каждый сервер определяет и объявляет, какими ресурсами, инструментами и подсказками он может поделиться с моделью

Общение между клиентом и сервером происходит через стандартные HTTP + JSON-RPC для запросов и Server-Sent Events (SSE) для асинхронщины и стриминга.
MCP определяет четыре основных типа возможностей, которые могут предоставлять серверы:

### 1. Инструменты: активные действия
Инструменты(tools) — это функции, которые модель может вызывать для выполнения конкретных действий: поиск в интернете, отправка email, выполнение вычислений, генерация изображений и т.д.

Ключевая особенность инструментов — они инициируются моделью на основе понимания потребностей пользователя. Например, когда пользователь спрашивает о погоде, модель сама решает, что нужно вызвать инструмент получения метеоданных.

### 2. Ресурсы: источники знаний
Ресурсы(resources) — это пассивные источники данных, к которым модель может обращаться для получения контекста: документы, базы данных, файлы пользователя и т.д.

В отличие от инструментов, ресурсы обычно не выполняют сложных вычислений и используются для расширения контекстуальных знаний модели.

### 3. Промпты: шаблоны взаимодействия
Промпты(prompts) — это предопределенные шаблоны взаимодействия с моделью, которые задают структуру диалога и направляют модель в решении конкретных задач.

Промпты можно сравнить с рабочими инструкциями, которые помогают модели более эффективно решать специализированные задачи: составление резюме, анализ кода, генерация идей и т.д.

### 4. Сэмплинг: рекурсивный интеллект
Сэмплинг(sampling) — это уникальная возможность, позволяющая серверу запрашивать у модели дополнительные размышления или анализ. Это создает своего рода "рекурсивное мышление", где ИИ может анализировать свои собственные выводы.

Сэмплинг открывает двери к созданию по-настоящему автономных ИИ-агентов, способных к многошаговому планированию и самокоррекции.

Протокол четко определяет взаимодействие между компонентами. Вот основные элементы:

### 1 Messages: 
Основа основ в нашем протоколе – диалог.

MCP структурирует его как последовательность сообщений с четкими ролями: user (это мы), assistant (наш ИИ), system (всевозможные системные инструкции) и tool (результат работы внешних сервисов, которые MCP Server). Каждое сообщение содержит текст и опциональные метаданные (время, язык, приоритет и тд). Системные сообщения задают тон и правила игры для модели ("Отвечай, как будто ты – вежливый помощник...", "Отвечай только на основе данных из предоставленных документов...").

Это помогает управлять поведением модели и защищаться от атак вроде prompt-injection (но надо понимать, что почти всегда можно все обойти, когда речь идет про ИИ - так что на сто процентов нельзя быть уверенным, что модель будет следовать этой инструкции).

Модель также может добавлять свои "мысли вслух" или план действий в метаданные ассистентских сообщений (chain of thoughts - цепочка рассуждений)

#### 2 Tools: 
Ну, собственно, это и есть наши внешние сервисы и функции, которые модель может вызывать.

Каждый инструмент описывается сервером: имя, понятное описание (чтобы модель знала, когда его использовать) и схема параметров. То есть, я могу создать инструмент с названием "база экономических данных Японии за 2000-2025 годы" и описать ее так:   
"Обращайся к этому инструменту, если тебе нужны какие-либо данные про экономику Японии за последние 25 лет". 

И мне нужно описать, что данный инструмент умеет отвечать на запросы с такими-то параметрами. Модель, получив список доступных инструментов, сама определяет, какой из них применить для ответа на запрос пользователя. 

Вызов происходит так: модель генерирует ответ типа "Я хочу вызвать инструмент X с параметрами Y".   
MCP-клиент перехватывает такой запрос, передает его нужному MCP-серверу, тот выполняет нужное действие и возвращает результат. 

Результат (например, данные из API или из БД) вставляется обратно в диалог как сообщение от роли tool.   
После этого модель продолжает диалог, уже зная результат.

MCP стандартизирует весь цикл: объявление, вызов, обработка ошибок, получение результата. Это позволяет строить сложные цепочки действий: модель может последовательно вызывать несколько инструментов, а протокол гарантирует корректную передачу данных между шагами. За счет того, что модель вызывает инструменты по своему усмотрению, а не по жесткому скрипту, система получается гибкой и "умной"

#### 3 Memory: 
Мы же хотим, чтобы ассистент помнил важные вещи между сессиями? MCP предлагает решение через так называемые серверы памяти.

Это могут быть сервисы, хранящие заметки, факты или векторные представления данных для семантического поиска по ним. На гитхабе уже есть примеры таких серверов от Anthropic и не только (всякие Memory Bank, Memory Box и тд).   
Модель знает, что может использовать инструменты этих серверов, чтобы запомнить что-то важное (вызвав метод save_memory) или "вспомнить" (вызвав метод search_memory).   
Так LLM обретает долговременную память: разные пользовательские предпочтения, какие-то детали прошлых проектов, важные факты - не теряются. Сами данные хранятся на стороне сервера, что важно для конфиденциальности.

MCP помогает управлять и краткосрочной памятью: если диалог становится слишком длинным, Context Manager может сжимать или суммировать историю, сохраняя самое важное в пределах контекстного окна модели

#### Files & Resources: 
Помимо активных инструментов, модели часто нужен доступ к данным – файлам, записям в базах данных, результатам API-запросов, логам. В контексте MCP это называется ресурсы.  
Сервер объявляет доступные ресурсы, используя URI-схемы (например, file:///path/doc.txt или database://customers/123. 

БД может быть инструментом - это так, если поверх нее есть какое-то API.   
Но может быть и ресурсом в зависимости от удобства применения). 
Модель может запросить содержимое ресурса, как бы делая GET-запрос.   
В отличие от инструментов, ресурсы обычно предназначены только для чтения (у инструментов можно вызывать любые описанные функции, и они могут изменять состояние инструмента как угодно).  
Файловая система – типичный пример ресурса. 
Anthropic выпустила готовый Filesystem MCP-сервер, позволяющий Claude безопасно работать с файлами на компьютере пользователя

#### Prompts: 
Кроме базовой системной инструкции, в MCP есть понятие Prompts – это предопределенные шаблоны взаимодействия для каких-то стандартных задач.   
Эти шаблоны могут комбинироваться, создавая сложные рабочие процессы (workflows).    
Например, шаблон "анализа лога" может включать шаги поиска по логу (в инструменте, например в elasticsearch), суммирование найденного (уже сама модель),  выдача заключения по шаблону. 
MCP позволяет явно объявлять такие последовательности


<https://habr.com/ru/articles/893482/>

<https://habr.com/ru/articles/920972/>

<https://habr.com/ru/articles/916722/>

<https://habr.com/ru/articles/903942/>

<https://blog.cloudflare.com/code-mode/>


## The Model Context Protocol changed in an important way this summer. 
With the 2026-07-28 MCP specification, the protocol core is now stateless: modern clients no longer need to establish a protocol session before making requests, and servers no longer rely on Mcp-Session-Id for ordinary requests. That makes MCP servers much easier to scale behind normal HTTP infrastructure.

 

At the same time, the official Python SDK has moved to v2 as its current stable line and provides a higher-level MCPServer API for defining tools, resources, and prompts with regular Python functions.

 

In this tutorial, we will build a small but complete MCP server in Python, run it over Streamable HTTP, inspect it locally, and connect to it with a Python MCP client. Let's get started.

 
We will create a small developer knowledge-base server.

It will expose three MCP primitives:

Tool:
    search_kb(query, limit)

Resource:
    kb://articles

Prompt:
    draft_support_reply(customer_message)
    
The server will contain no user session state. Every request will contain everything required to process it, which makes it a good example of the new stateless MCP model.

Conceptually:
```
LLM Host
   |
   | MCP request
   v
+-----------------------+
| Python MCP Server     |
|                       |
| search_kb()           |
| kb://articles         |
| draft_support_reply() |
+-----------------------+
```
### Step 1: Creating the Project
The current Python SDK requires Python 3.10 or newer. The official documentation recommends installing the CLI extra because it gives us the development command and MCP Inspector workflow.

Using uv:
```
mkdir first-mcp-server
cd first-mcp-server

uv init
uv add "mcp[cli]"
```
Or with pip:
```
pip install "mcp[cli]"
```
Your project can be as small as:
```
first-mcp-server/
├── server.py
└── client.py
```
No framework boilerplate is required.


### Step 2: Creating Your First MCP Server
Create server.py:
```
from mcp.server import MCPServer

mcp = MCPServer(
    "Developer Support KB",
    instructions=(
        "Use the knowledge-base tools to answer support questions. "
        "Prefer retrieved KB information over guessing."
    ),
)
```
MCPServer is the high-level server API in the current Python SDK. For most servers, this is the API you want. The SDK also exposes a lower-level Server class, but that is intended for cases where you need exact control over schemas, protocol metadata, or custom methods.

Now let's give our server some data.
```json
ARTICLES = [
    {
        "id": "python-env",
        "title": "Creating a Python virtual environment",
        "body": (
            "Create a virtual environment with `python -m venv .venv`, "
            "then activate it before installing dependencies."
        ),
    },
    {
        "id": "reset-password",
        "title": "Resetting your password",
        "body": (
            "Open Account Settings, choose Security, and select "
            "Reset Password. A verification email will be sent."
        ),
    },
    {
        "id": "api-rate-limit",
        "title": "Understanding API rate limits",
        "body": (
            "API rate limits restrict the number of requests allowed "
            "within a time window. Clients should retry using "
            "exponential backoff after receiving a rate-limit response."
        ),
    },
]
```
So far this is just Python.

The interesting part begins when we expose functions through MCP.


### Step 3: Adding an MCP Tool
An MCP tool is a function the model can decide to call.

Add this to server.py:
```python
@mcp.tool()
def search_kb(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Search the support knowledge base.

    Args:
        query: Words or phrases to search for.
        limit: Maximum number of articles to return.
    """
    query = query.lower()

    matches = []

    for article in ARTICLES:
        searchable_text = (
            article["title"] + " " + article["body"]
        ).lower()

        if query in searchable_text:
            matches.append(article)

    return matches[:limit]
```
Notice what we did not write.

There is no JSON Schema.

There is no manually written tool manifest.

There is no argument parser.

The SDK derives the tool definition from the Python function itself. Its type hints become the MCP input schema, and defaults such as:

limit: int = 3
make parameters optional in the generated schema. The official SDK documentation uses exactly this pattern. Conceptually, your function:
```
def search_kb(
    query: str,
    limit: int = 3
)
```
becomes something similar to:
```json
{
  "name": "search_kb",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string"
      },
      "limit": {
        "type": "integer",
        "default": 3
      }
    },
    "required": ["query"]
  }
}
```
This is one of the reasons MCP development in Python feels pleasantly ordinary: your function signature is effectively your interface definition.

### Step 4: Adding a Resource
Tools are actions the model can call.

Resources are different. They expose information that the host application can load into context.

Add:
```
@mcp.resource("kb://articles")
def list_articles() -> str:
    """Return the available knowledge-base articles."""
    lines = []

    for article in ARTICLES:
        lines.append(
            f"{article['id']}: {article['title']}"
        )

    return "\n".join(lines)
```
The resource has the URI:

kb://articles

A client can read it without invoking a tool.
```
Resource ≈ data that can be read
Tool     ≈ function that can perform work
```
The SDK documentation roughly compares resources with GET-like behavior and tools with action-oriented POST-like behavior.


### Step 5: Adding an MCP Prompt
We can also expose a reusable prompt template.
```python
@mcp.prompt()
def draft_support_reply(customer_message: str) -> str:
    """Create a prompt for drafting a concise support response."""

    return f"""
You are a technical support assistant.

Write a concise and helpful response to this customer message:

{customer_message}

Use the support knowledge base when relevant.
Do not invent product policies.
""".strip()
```

Again, this is just a Python function plus a decorator.

Prompts are generally initiated by the user or host rather than autonomously invoked by the model. The current SDK supports tools, resources, and prompts through the same decorator-oriented server interface.

At this point, server.py looks like this:
```python
from mcp.server import MCPServer

mcp = MCPServer(
    "Developer Support KB",
    instructions=(
        "Use the knowledge-base tools to answer support questions. "
        "Prefer retrieved KB information over guessing."
    ),
)

ARTICLES = [
    {
        "id": "python-env",
        "title": "Creating a Python virtual environment",
        "body": (
            "Create a virtual environment with `python -m venv .venv`, "
            "then activate it before installing dependencies."
        ),
    },
    {
        "id": "reset-password",
        "title": "Resetting your password",
        "body": (
            "Open Account Settings, choose Security, and select "
            "Reset Password. A verification email will be sent."
        ),
    },
    {
        "id": "api-rate-limit",
        "title": "Understanding API rate limits",
        "body": (
            "API rate limits restrict the number of requests allowed "
            "within a time window. Clients should retry using "
            "exponential backoff after receiving a rate-limit response."
        ),
    },
]

@mcp.tool()
def search_kb(
    query: str,
    limit: int = 3,
) -> list[dict[str, str]]:
    """Search the support knowledge base."""

    query = query.lower()

    matches = []

    for article in ARTICLES:
        searchable_text = (
            article["title"] + " " + article["body"]
        ).lower()

        if query in searchable_text:
            matches.append(article)

    return matches[:limit]

@mcp.resource("kb://articles")
def list_articles() -> str:
    """Return the available knowledge-base articles."""

    return "\n".join(
        f"{article['id']}: {article['title']}"
        for article in ARTICLES
    )

@mcp.prompt()
def draft_support_reply(
    customer_message: str,
) -> str:
    """Create a support-response prompt."""

    return f"""
You are a technical support assistant.

Write a concise and helpful response to this customer message:

{customer_message}

Use the support knowledge base when relevant.
Do not invent product policies.
""".strip()

if __name__ == "__main__":
    mcp.run("streamable-http")
```

That is a complete network-accessible MCP application.


### Step 6: Running It in Development Mode
For development, the SDK includes a convenient command:
```
uv run mcp dev server.py
```
The MCP development command launches the server with MCP Inspector support, giving you a UI for listing and invoking tools. The official SDK recommends this as the basic development loop.

Open the Inspector URL printed in your terminal.

You should see:

search_kb
under Tools.

Try calling it with:
```
{
  "query": "rate limit"
}
```
The result should contain:
```
[
  {
    "id": "api-rate-limit",
    "title": "Understanding API rate limits",
    "body": "API rate limits restrict ..."
  }
]
```

You now have a working MCP server.


### Step 7: Running It Over Streamable HTTP
For an actual HTTP server, run:

uv run python server.py

By default, your MCP endpoint is exposed at:

http://127.0.0.1:8000/mcp

The SDK's Streamable HTTP server uses /mcp as its default endpoint.

If you prefer running it as a normal ASGI application, replace the __main__ block with:

app = mcp.streamable_http_app()

Then launch it with Uvicorn:

uvicorn server:app

This is particularly useful when MCP is one component inside a larger FastAPI or Starlette deployment. streamable_http_app() returns a standard Starlette-compatible ASGI app.


What Changed in the Stateless MCP Update?
This deserves special attention because a lot of MCP tutorials online now describe the older lifecycle. Under older versions of the protocol, an HTTP client effectively did this:
```
Client
  |
  | initialize
  v
Server
  |
  | Mcp-Session-Id
  v
Client
  |
  | later request + session id
  v
Same logical session
```
This created a multi-instance deployment that often needed sticky routing or shared session infrastructure. The 2026-07-28 protocol changes that.

A modern MCP request is designed to be self-contained:
```
Request 1
   |
   v
Server A

Request 2
   |
   v
Server C

Request 3
   |
   v
Server B
```
No protocol session needs to tie those calls together. The MCP team explicitly describes this as moving from a bidirectional, stateful protocol core to a stateless request/response model. This makes ordinary load balancing much easier.


### Writing a Python Client
Let's verify the server without depending on a third-party AI application.

Create client.py:
```python
import asyncio

from mcp import Client

async def main() -> None:
    async with Client(
        "http://127.0.0.1:8000/mcp"
    ) as client:

        print(
            "Protocol:",
            client.protocol_version,
        )

        tools = await client.list_tools()

        print("\nAvailable tools:")

        for tool in tools.tools:
            print("-", tool.name)

        result = await client.call_tool(
            "search_kb",
            {
                "query": "rate limit",
                "limit": 2,
            },
        )

        print("\nTool result:")

        if result.structured_content:
            print(result.structured_content)
        else:
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())
```
Run the server in one terminal:

uv run python server.py

Then run the client in another:

uv run python client.py

The v2 Client accepts an HTTP URL directly and automatically uses Streamable HTTP. It also exposes the negotiated protocol version, so with a current client/server pair you should see the modern protocol version reported by the connection.

Your output should be similar to mine:

Protocol: 2026-07-28

Available tools:
- search_kb
```  
  {'result': [{
               'id':'api-rate-limit',
              'title': 'Understanding API rate limits',
              'body': 'API rate limits restrict the number of requests allowed within a time window. Clients should retry using exponential backoff after receiving a rate-limit response.'
  }]
  }
```
But What If My Application Actually Needs State?

"Stateless protocol" does not mean your application can never maintain state.

It means MCP itself no longer hides application state inside a protocol session.

Suppose you were building a shopping server. Instead of relying on:

MCP session 42 owns this basket
you could expose:
```
@mcp.tool()
def create_basket() -> dict[str, str]:
    basket_id = create_new_basket()

    return {
        "basket_id": basket_id
    }
```
Then later:
```
@mcp.tool()
def add_item(
    basket_id: str,
    product_id: str,
) -> dict:
    return add_product(
        basket_id,
        product_id,
    )
```
Now the model sees and passes:

basket_id
explicitly.

The MCP maintainers specifically recommend this explicit-handle pattern for application-level state under the new stateless protocol.

It is a subtle but useful architectural shift:

#### Old idea:
protocol remembers state

#### New idea:
application owns state
and identifiers travel explicitly

Scaling the Server
The stateless core becomes particularly valuable when you deploy multiple workers.

For example:

uvicorn server:app --workers 4

A modern MCP request can be handled by any worker because the protocol no longer requires it to return to the worker that handled a previous request.

Conceptually:
```
              +--> Worker 1
Client --> LB +--> Worker 2
              +--> Worker 3
              +--> Worker 4
```
There are additional considerations for advanced features such as multi-round-trip interactions, shared subscription events, authorization, and distributed state, but those are application architecture concerns rather than a requirement of basic MCP tool execution.


Wrapping Up
The practical shift here is smaller than the spec diff makes it look: you still decorate functions with @mcp.tool(), you still return dicts and let the framework build the result, and you still run mcp.run() to serve it. 

What's different is what happens underneath. You don't need any handshake to negotiate, no session to keep warm, no sticky routing to configure. Get comfortable with MCPServer, keep stdout clean, and the rest of the stateless spec mostly stays out of your way.
 
