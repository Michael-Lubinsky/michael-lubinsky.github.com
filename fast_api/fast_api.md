## FastAPI

**FastAPI** is a Python web framework for building APIs. You write ordinary functions with **type hints**, and FastAPI uses those hints to **validate requests, convert data, generate OpenAPI docs and serialize responses**. It's built on two libraries:
- **Starlette**, the ASGI web toolkit (routing, requests, middleware, async).
- **Pydantic**, for data validation and serialization.

It runs on an ASGI server such as **Uvicorn**.

## 1. The smallest app

```python
# main.py
from fastapi import FastAPI

app = FastAPI(title="Comp API")

@app.get("/health")
def health():
    return {"status": "ok"}       # dicts and lists become JSON automatically
```

```bash
pip install "fastapi[standard]"
fastapi dev main.py          # auto-reload for development
# or: uvicorn main:app --reload
```

Open **http://localhost:8000/docs** for Swagger UI, generated from your code. This is one of FastAPI's biggest selling points.

## 2. Where request data comes from

FastAPI decides where each parameter comes from by **its type and whether its name appears in the path**:

```python
from typing import Annotated
from fastapi import Query, Path

@app.get("/companies/{cik}/executives")
def list_execs(
    cik: Annotated[str, Path(pattern=r"^\d{10}$")],    # in the path → path param
    fiscal_year: int | None = None,                     # simple type → query param
    limit: Annotated[int, Query(ge=1, le=500)] = 50,    # query param with limits
):
    ...
# GET /companies/0000320193/executives?fiscal_year=2025&limit=10
```

- `fiscal_year=abc` → FastAPI returns **422** automatically, with a clear error. You write no validation code.
- `"2025"` is converted to the integer `2025` for you.

**Request body** = a Pydantic model:

```python
from pydantic import BaseModel, Field
from datetime import date

class CompRecord(BaseModel):
    executive: str = Field(min_length=1)
    fiscal_year: int = Field(ge=2000, le=2100)
    salary: float = Field(ge=0)
    bonus: float = 0
    filed_on: date | None = None

@app.post("/comp", status_code=201)
def create(record: CompRecord):          # a Pydantic type → read from the JSON body
    return record
```

## 3. Response models: control what goes out

```python
class CompOut(BaseModel):
    id: int
    executive: str
    total: float

@app.get("/comp/{id}", response_model=CompOut)
def get_comp(id: int):
    row = fetch_row(id)          # may contain extra columns, e.g. internal notes
    return row                   # filtered and validated to CompOut's fields only
```

`response_model` acts as a **security filter**: fields not in the model are never sent. That matters for sensitive compensation data. Mentioning this shows you think about data exposure.

## 4. Errors and status codes

```python
from fastapi import HTTPException

@app.get("/comp/{id}")
def get_comp(id: int):
    row = fetch_row(id)
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return row
```

The conventions: **201** created, **202** accepted for async work (like the Excel endpoint), **400** bad input, **401/403** auth, **404** not found, **409** conflict, **422** validation (automatic), **503** a dependency is down.

You can also map your own exceptions to responses in one place:

```python
@app.exception_handler(ExcelProcessingError)
def excel_error(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

## 5. Dependency injection with `Depends` (the core idea)

A **dependency** is a function whose result is passed into your endpoint. You use it for DB connections, the current user, settings and pagination. Code before `yield` is setup; code after is cleanup.

```python
import psycopg
from fastapi import Depends, Header

def get_db():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn                     # given to the endpoint
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()                   # always runs after the response

def require_api_key(x_api_key: str = Header()):
    if x_api_key != settings.api_key:
        raise HTTPException(401, "Invalid API key")

DB = Annotated[psycopg.Connection, Depends(get_db)]

@app.get("/comp/{id}", dependencies=[Depends(require_api_key)])
def get_comp(id: int, db: DB):
    return db.execute("SELECT ... WHERE id = %s", (id,)).fetchone()
```

Why it's useful:
- **One place** handles connection, transaction and cleanup logic.
- Dependencies can depend on other dependencies (auth → user → permissions).
- **Testing:** you can swap any dependency for a fake (section 10).

## 6. `def` vs `async def` (the most common interview trap)

| You write | FastAPI does | Use when |
| --- | --- | --- |
| `def endpoint()` | Runs it in a **thread pool** | You call **blocking** libraries: psycopg (sync), openpyxl, requests |
| `async def endpoint()` | Runs it **on the event loop** | Everything inside is awaitable: `asyncpg`, async psycopg, `httpx.AsyncClient` |

**The trap:** a blocking call inside `async def` (for example `time.sleep` or a sync DB query) **freezes the event loop**, and every other request waits. If you aren't sure, use plain `def`. The pipeline I built uses `def` endpoints for exactly this reason: it uses sync psycopg.

For heavy CPU work or long jobs, neither is right. Send the work to **Celery**, as the pipeline does.

## 7. Background work: three options

| Option | When |
| --- | --- |
| `BackgroundTasks` (built in) | Small fire-and-forget work after the response, such as sending an email. It runs in the same process, so it's **lost if the process restarts** and has no retries. |
| Celery / another task queue | Anything long, important or retryable, like processing Excel files. |
| `asyncio.create_task` | Rarely. Easy to lose track of tasks and errors. |

```python
from fastapi import BackgroundTasks

@app.post("/notify")
def notify(bg: BackgroundTasks):
    bg.add_task(send_email, "consultant@x.com")   # runs after the response is sent
    return {"queued": True}
```

## 8. Organizing a real project

```
app/
  main.py            # create the app, include routers, lifespan
  config.py          # settings (pydantic-settings, read from env vars)
  db.py              # connection or pool, get_db dependency
  routers/
    comp.py          # APIRouter(prefix="/comp", tags=["comp"])
    filings.py
  schemas.py         # Pydantic models (request/response)
  services/          # business logic, no FastAPI imports → easy to test
```

```python
# routers/comp.py
from fastapi import APIRouter
router = APIRouter(prefix="/comp", tags=["compensation"])

@router.get("/{id}")
def get_comp(id: int): ...

# main.py
app.include_router(comp.router, prefix="/v1")      # → /v1/comp/{id}
```

**Settings:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    excel_base_dir: str = "/data"

settings = Settings()       # reads DATABASE_URL etc. from the environment or a .env file
```

## 9. Lifespan and middleware

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    app.state.pool = ConnectionPool(DATABASE_URL)   # on startup
    yield
    app.state.pool.close()                            # on shutdown

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def timing(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Elapsed-ms"] = f"{(time.perf_counter()-start)*1000:.1f}"
    return response
```

Middleware is the place for request logging, request IDs, timing and CORS (`CORSMiddleware`).

## 10. Testing

```python
from fastapi.testclient import TestClient
from app.main import app, get_db

def fake_db():
    yield FakeConnection()

app.dependency_overrides[get_db] = fake_db      # swap in the fake DB
client = TestClient(app)

def test_validation():
    r = client.post("/comp", json={"executive": "", "fiscal_year": 1990, "salary": -1})
    assert r.status_code == 422

def test_not_found():
    assert client.get("/comp/999").status_code == 404
```

`dependency_overrides` is the main reason dependency injection matters. You can test endpoints without a real database, auth or Celery.

## 11. Security (relevant to SOC 2)

- **Authentication:** an API-key header dependency (internal services), or OAuth2/JWT with `fastapi.security.OAuth2PasswordBearer`.
- **Authorization:** a dependency that checks the user's role or client access, and returns 403.
- **Limit the output:** `response_model` so internal fields never leak.
- **Validate the input:** Pydantic constraints, plus checks like the path validation in the Excel API.
- **SQL:** always use parameterized queries (`%s`), never f-strings.
- **Docs:** turn off `/docs` in production if the API isn't public (`FastAPI(docs_url=None)`).

## 12. Running it on-prem

```bash
# Several worker processes behind nginx
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
# or simply
uvicorn app.main:app --workers 4 --host 127.0.0.1 --port 8000
```

Run it as a **systemd** service with nginx in front for TLS, timeouts and request size limits (Excel uploads).

## FastAPI vs Django, since Compensia uses both

| | FastAPI (SEC Companion) | Django (Data Hub) |
| --- | --- | --- |
| Focus | APIs | Full web apps: admin, ORM, auth, templates |
| Validation | Pydantic, from type hints | Forms / DRF serializers |
| Database | Bring your own (psycopg, SQLAlchemy) | Built-in ORM + migrations |
| Async | Async throughout | Partial async support |
| Docs | Automatic OpenAPI | Needs DRF plus extras |
| Admin UI | None | Built in, and very useful for internal tools |

**Interview line:** "FastAPI suits a focused API service like SEC Companion. Django suits a data-management app with an admin interface, like Data Hub. The concepts carry over: request validation, dependency/middleware layers, and a thin endpoint calling a service layer."

## Five likely questions with short answers

1. **"`def` or `async def`?"** `def` whenever you call blocking libraries; FastAPI runs those in a thread pool. Use `async def` only when everything inside is awaitable. Blocking inside `async def` stalls every request.
2. **"How do you manage DB connections?"** A connection pool created in the lifespan, handed out by a `Depends` dependency with `yield`, which commits or rolls back and returns the connection to the pool.
3. **"How do you handle long-running requests?"** Return 202 with a task id, process the work in Celery, and provide a status endpoint. That's exactly your pipeline.
4. **"How do you test endpoints?"** `TestClient` plus `dependency_overrides`, keeping business logic in plain functions that are unit-tested without HTTP.
5. **"How do you secure it?"** Auth via dependencies, role checks, `response_model` filtering, Pydantic validation, parameterized SQL, and secrets from the environment.

## Practice (about 30 minutes, using your pipeline)

1. Open the `excel_pipeline` project and run it. Visit `/docs` and try the endpoints there.
2. Add `GET /tasks?status=FAILURE&limit=20` with query parameter validation (`Query(ge=1, le=100)`).
3. Add an `X-API-Key` header dependency to `/process`.
4. Convert the connection-per-call code to a `psycopg_pool.ConnectionPool` created in the lifespan and handed out through `Depends`.
5. Write two tests with `TestClient`: a relative path returns 400, and an unknown task id returns 404.

If you do steps 3 and 4 yourself, you'll have hands-on examples of dependency injection, lifespan and security to talk about.
<https://habr.com/ru/articles/1005390/>

<https://habr.com/ru/articles/1044300/>

<https://medium.com/@shouke.wei/fastapi-fastapi-new-launch-a-new-fastapi-project-in-seconds-00c450254c00>

<https://github.com/ydjin0602/fastapi-template>

<https://habr.com/ru/articles/1031190/> Fast API , Docker

<https://levelup.gitconnected.com/7-fastapi-extensions-so-powerful-i-stopped-using-flask-forever-9c6e9a4fbb5a>

<https://github.com/jaehyeon-kim/nicegui-fastapi-template>

<https://www.honeybadger.io/blog/fastapi-error-handling/>

<https://habr.com/ru/articles/970798/>

<https://habr.com/ru/articles/972642/>


<https://habr.com/ru/articles/983254/>

<https://github.com/offerrall/FuncToWeb>   
<https://realpython.com/get-started-with-fastapi/>  
<https://medium.com/@CodeWithHannan/python-for-data-apis-building-robust-backends-with-fastapi-ecfe096663c4>  
<https://fastlaunchapi.dev/blog/how-fastapi-works/>  
<https://fastlaunchapi.dev/blog/how-to-structure-fastapi/> 
<https://realpython.com/fastapi-python-web-apis/>  

<https://fastlaunchapi.dev/blog/async-secure-scalable-fastapi>

<https://habr.com/ru/articles/1044536/>


### Litestar

<https://www.b-list.org/weblog/2025/aug/06/litestar/>
