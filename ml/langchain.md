## LangChain LangGraph
https://medium.com/@mganesa-ks/watching-an-ai-agent-think-8a4d3a86c59b

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
llm = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages([
("system", "You are concise."),
("human", "{question}")
])
chain = prompt | llm | StrOutputParser() # This is our chain
print(chain.invoke({"question": "Give me 3 focus tips."})) # making a single
qs = [{"question": q} for q in ["One tactic for RAG?", "Explain LCEL in 1 line."
print(chain.batch(qs))
```
### How pipe operator works 
`|` isn't special syntax Python reserves for pipelines.   
It's the **bitwise OR operator**, and Python lets any class override what it does via operator overloading.

**The mechanism: dunder methods**

When Python sees `a | b`, it doesn't hardcode "bitwise or" — it looks for a method:

```python
a | b  
# is really sugar for:
a.__or__(b)
# or, if that returns NotImplemented, Python tries:
b.__ror__(a)
```

Any class can define `__or__` to do whatever it wants. LangChain's `Runnable` base class does exactly this.

**What LangChain actually does**

Every LCEL component (prompts, models, parsers, retrievers, etc.) inherits from `Runnable`, which defines something like:

```python
class Runnable:
    def __or__(self, other):
        return RunnableSequence(self, other)

    def __ror__(self, other):
        return RunnableSequence(other, self)
```

So when you write:

```python
chain = prompt | model | output_parser
```

Python evaluates it left to right:
1. `prompt | model` → calls `prompt.__or__(model)` → returns a `RunnableSequence(prompt, model)`
2. `(that sequence) | output_parser` → calls `__or__` again → returns `RunnableSequence(prompt, model, output_parser)`

The result is a single new `Runnable` object that, when invoked, calls each step in order, passing each step's output as the next step's input — basically composing functions, but wrapped in an object with `.invoke()`, `.stream()`, `.batch()`, etc.

**Why `__ror__` matters too**

It handles cases where the left operand isn't a `Runnable` — e.g. a plain function or dict:

```python
chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | model
```

Here the dict doesn't know about `__or__`, so Python falls back to `prompt.__ror__(dict)` (LangChain also auto-wraps dicts/functions into `RunnableParallel`/`RunnableLambda` under the hood).

**In short:** `|` is just Python's OR operator, repurposed by operator overloading. LangChain isn't changing Python syntax — it's exploiting a general Python feature (any object can define how it responds to `+`, `|`, `==`, etc.) to make chain-building read like Unix pipes.
<https://habr.com/ru/articles/1068168/>

<https://habr.com/ru/articles/956940/>


###  Как устроен LangChain

Каждый компонент (промпты, модели, парсеры, ретриверы, агенты) в ядре реализует унифицированный интерфейс Runnable, предоставляющий шесть стандартных методов:
```
 invoke(input)          # Синхронное выполнение
 ainvoke(input)         # Асинхронное выполнение
 batch(inputs)          # Синхронная пакетная обработка
 abatch(inputs)         # Асинхронная пакетная обработка
 stream(input)          # Синхронный стриминг
 astream(input)         # Асинхронный стриминг
```

Runnable Protocol — основа всего. Единый интерфейс позволяет легко объединять Runnable-компоненты в цепочки вызовов через оператор |.

### Мир без Runnable:
```python
docs = retriever.invoke(query)
formatted = prompt.format(context=docs, question=query)
response = model.invoke(formatted)
result = parser.invoke(response)
```
### Runnable:
```python
result = (retriever | prompt | model | parser).invoke(query)
```
Такой синтаксис называется LCEL (LangChain Expression Language) и составляет базовый фундамент LangChain.   
Собрав LCEL-цепочку, то можем использовать ее сколько угодно раз, вызывая каким угодно способом из 6 представленных выше способов.

Примеры:
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Простейшая цепочка
chain = (
    ChatPromptTemplate.from_template("{question}") 
    | ChatOpenAI(model="gpt-4o-mini") 
    | StrOutputParser()
)

# Одиночный вызов
chain.invoke({"question": "Почему мне ставят дизлайки на хабре за рекламу? Кого? С кого спросить что б мне хоть заплатили?"})

# Батч
chain.batch([
    {"question": "Придумай необычное имя для кота"}, 
    {"question": "Объясни квантовую физику на пацанском"}
])

# Стриминг
for chunk in chain.stream({"question": "Как заставить робота работать как человек?"}):
    print(chunk, end="")

# Async варианты
await chain.ainvoke(...)
await chain.abatch([...])
async for chunk in chain.astream(...):
    ...
``` 

И важные возможности того, что можно делать с цепочками и не только:

### Паралелльно выполнение (в данном случае трех цепочек)
```python
multi_analysis = RunnableParallel({
    "summary": summary_chain,      # Генерирует краткое резюме
    "sentiment": sentiment_chain,  # Анализирует тональность
    "keywords": keyword_chain      # Извлекает ключевые слова
})

# Условные переходы — роутинг по типу запроса
branch_chain = RunnableBranch(
    (lambda x: "seo" in x.lower(), seo_chain),
    (lambda x: "content" in x.lower(), content_chain),
    general_chain  # по умолчанию
)

# Автоматические retry — повторяет при ошибках (rate limits, timeouts)
chain_with_retry = (prompt | llm | parser).with_retry(
    stop_after_attempt=3,           # Максимум 3 попытки
    wait_exponential_jitter=True    # Экспоненциальная задержка между попытками
)

# Fallback — если все retry не помогли, переключаемся на другую цепочку
main_chain = prompt | ChatOpenAI(model="gpt-4o") | parser
backup_chain = prompt | ChatOpenAI(model="gpt-4o-mini") | parser

safe_chain = main_chain.with_fallbacks([backup_chain])
```

Одна из важных вещей для того, чтобы сложные LLM-based системы работали правильно — это structured outputs.   
Это когда вместо привычный длинной (и не очень полезной целиком) простыни текста LLM возвращает структурированные данные (JSON, таблицы, списки), с которыми уже легко работать программно. 
Стандартом этого является Pydantic.
```python
class TaskPlan(BaseModel):
    title: str
    steps: List[str] = Field(..., min_items=3, description="actionable steps")

structured = ChatOpenAI(model="gpt-4o-mini").with_structured_output(TaskPlan)
plan = structured.invoke("Спланируй мне двадцатиминутную сессию упражнений с собственным весом")
print(plan.model_dump())
# Вывод: {'title': '...', 'steps': ['...', '...', '...']}
```

Под капотом .with_structured_output() то, за что стоит любить фреймворки: 
LangChain абстрагирует различия между провайдерами и использует нативный запрос, если он поддерживается   
(OpenAI function calling API или Anthropic tool use),  
и фолбэк на json-mode или промпт инструкции, если у провайдера такой функциональности нет.

Вызов инструментов LangChain

Инструменты расширяют возможности LLM: поиск в интернете, вычисления, обращение к API. LangChain предоставляет готовые инструменты (Wikipedia, Calculator и другие) и позволяет создавать свои любой сложности через декоратор @tool.
Важно грамотно описать Docstring и очень важно уметь написать его максимально конкретно, одноначно, емко и при том коротко, так как все это подается в контекст и напрямую влияет на правильный вызов этих инструментов системой. 
Где-то уместно описать входящие и выходные параметры, а где-то нет — это уже наука в конкретном случае.
```python
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

@tool
def multiply(a: int, b: int) -> int:
    """Умножает два числа."""  # Docstring супер критически важен
    return a * b

llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools([multiply])  # Передаем инструменты в модель

resp = llm_with_tools.invoke("Сколько будет 23 * 47?")
print(resp.tool_calls)  # [{'name': 'multiply', 'args': {'a': 23, 'b': 47}, 'id': '...'}]
```

Важно: модель не выполняет tool, она только возвращает намерение его вызвать с аргументами. Выполнение — задача уже наша (или агента).
```python
if resp.tool_calls:
    tool_call = resp.tool_calls[0]
    result = multiply.invoke(tool_call["args"])  # Выполняем инструмент
    print(f"Результат: {result}")  # 1081
```

И опять же, если у API LLM есть поддержка инструментов, то она будет сделана нативно (но возвращается все равно намерение а не результат инструмента), а если нет, то через промпт.
```python
from langchain_core.messages import HumanMessage, ToolMessage

messages = [HumanMessage(content="Предскажи курс бразильского реала в 2030 году")]
while True:
    resp = llm_with_tools.invoke(messages)
    if not resp.tool_calls:
        break
    
    for tool_call in resp.tool_calls:
        result = tools_dict[tool_call["name"]].invoke(tool_call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    messages.append(resp)
```

### Использование памяти

Память позволяет хранить текущее взаимодействие и сохранять весь прошлый опыт или важные факты для принятия решения.

В LangChain есть два основных типа:

    -  Short-term (session-based in-memory): сообщения в текущей сессии

    - Long-term (semantic/persistent): факты и контекст в постоянной хранилке
	
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "Отвечай кратко"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])
chain = prompt | ChatOpenAI(model="gpt-4o-mini")

store = {}
def get_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

with_history = RunnableWithMessageHistory(
    chain, 
    lambda cfg: get_history(cfg["configurable"]["session_id"]),
    input_messages_key="input",
    history_messages_key="history"
)

cfg = {"configurable": {"session_id": "user_123"}}
with_history.invoke({"input": "Пользователь любит жарить мясо"}, config=cfg)
with_history.invoke({"input": "Что пользователь любит??"}, config=cfg) 
```

Если нужно что-то постоянно, то можно взять PostgreSQL. Огромный плюс LangChain в развитом коммьюнити, которое написало практически все, что угодно.
```python
def get_history(session_id: str):
    return PostgresChatMessageHistory(
        connection_string="postgresql://...",
        session_id=session_id
    )
```

Память штука очень классная, но всегда встают вечные сложные вопросы что именно туда сохранять, как это потом валидировать и как часто обращаться. Память для агентов очень большая и интересная тема сама по себе.

Мини-выводы про LangChain:

У LangChain большое количество удобных и продуманных штук, которых достаточно чтобы в него запихать не просто линейную логику, но и многие сложные вещи. 
Пописать код для чего-то кастомного — ну да, придется, но в целом все достаточно приятно.


## LangGraph
Но если нужно из коробки сразу все самое сложное, задача решается графами, есть очень сложный план, которого надо придерживаться или есть мультиагентность, то под это подойдет LangGraph.

Для аналогии можно представить LangGraph как блок-схему нашего приложения. К  аждый блок (узел = «node») — это просто маленькая функция на питошке, которая выполняет одну задачу. 
Стрелки (ребра = «edges») говорят, какой блок запускается следующим. 
По блок-схеме как бы перемещается «рюкзачок с данными» (состояние = «state») и в этот рюкзачок можно что-то положить и что-то считать. В чат-ботах там лежит, как правило, список сообщений чата.  
```python
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

class State(TypedDict):
    messages: Annotated[List, add_messages]  # add_messages — reducer, добавляет новые сообщения к списку

llm = ChatOpenAI(model="gpt-4o-mini")

def model_node(state: State):
    reply = llm.invoke(state["messages"])
    return {"messages": [reply]} # Возвращаем только новое сообщение, LangGraph сам добавит его в state

graph = StateGraph(State)
graph.add_node("model", model_node)
graph.add_edge(START, "model")
graph.add_edge("model", END)

app = graph.compile()  # Превращаем граф в Runnable
result = app.invoke({"messages": [HumanMessage(content="Поставьте лайков на хабре по братски")]})
print(result["messages"][-1].content)
```

Граф сначала заполняется (START + nodes+edges + END), а затем его нужно скопилировать. В процессе компиляции происходит все то, что обычно делается при компиляции — валидация, оптимизация и превращение в исполняемую структуру — уже знакомый нам объект Runnable. Дальше все ровно то же самое и оперировать можно уже им.

Одна из главных фич LangGraph — автоматическое сохранение состояния графа после каждого узла (checkpointing).

#### восстановление графа из чекпоинта
```
checkpointer = SqliteSaver.from_conn_string("conversations.db")
graph = StateGraph(...).compile(checkpointer=checkpointer)
```
Это дает три важных преимущества:

    Persistence — можно прервать выполнение и продолжить позже

    Time travel — откат к любому предыдущему шагу

    Вмешательство человека (Human-in-the-loop) — пауза на получение чего-то от пользователя

Фактически, чекпоинтинг заменяет память в LangChain: в памяти находится весь state графа (сообщения, промежуточные результаты, метаданные, счетчики), а не только сообщения.

Ну а на этом самые важные отличия, как будто бы, и заканчиваются.
Итоги LangChain vs LangGraph

LangChain работает с цепочками (chains), LangGraph — с графами состояний (graphs). Неожиданно. Обе сущности (и цепочка и скомпилированный граф) — это Runnable компоненты с единым интерфейсом.

Цепочки хороши для линейных пайплайнов, графы — для сложной мультиагентной оркестрации с циклами и ветвлениями. 
Почти все сложное, что нативно сделано в коробке LangGraph МОЖНО сделать на LangChain, но это будет неудобно (сложная логика), запутанно (вложенные друг в друга RunnableBranch), 
а то и совсем на костылях (типа human-in-the-loop или по простому — запроса данных от пользователя).  
Что выбрать LangChain или LangGraph?

Если у вас вообще возникает такой вопрос, то на 90% ответом будет LangChain.
Таблица принятия решения

Быстрые ответы на самые важные вопросы

    LangChain, LangGraph и прочие Lang — это одно и то же? 

У команды LangChain три проекта: LangChain, LangGraph (оба — разные фреймворки) и LangSmith (трейсинг). Все остальное Lang-что-то сделано сторонними командами, но на базе LangChain/LangGraph.

####    Можно ли встроить LangChain в LangGraph?

Да, любые LangChain компоненты работают в узлах графа:

```python
# LCEL цепочка
chain = prompt | llm | parser

# Как узел графа
def node(state):
    return {"output": chain.invoke(state["input"])}

graph.add_node("chain_node", node)
```

    Насколько переиспользуется код LangChain в LangGraph?

Огромное количество кода переиспользуется (в процентах выразить сложно, но по грубым оценкам это около 70-90%), так как оба используют langchain-core

Модели, промпты, инструменты, retriever'ы, парсеры — без изменений. Меняется слой оркестрации с цепочек на граф и связанные с ним нюансы памяти.

    Насколько LangGraph медленнее LangChain? 

Оба используют одно ядро, а дальше все упирается в сложность задачи. Основное латенси в LLM-приложениях это ̶M̶C̶P̶ ̶(̶н̶е̶т̶,̶ ̶д̶о̶к̶а̶з̶а̶н̶о̶)̶ вызов самой LLM.

    Одинаково ли работает память?

Нет, при одинаковом ядре у них разные подходы к оркестрации. LangChain: классы ConversationBufferMemory (накопление), ConversationSummaryMemory (суммаризации диалогов) — обертки для простых случаев. LangGraph: нативное управление состоянием через State + Checkpointer.

Критерий
	

🦜⛓️ LangChain
	

🕸️ LangGraph

Основной механизм
	

RunnableWithMessageHistory
	

Checkpointing

Что сохраняется
	

Только история сообщений
	

Весь state графа (messages + любые данные)

Когда сохраняется
	

При явном вызове
	

Автоматически после каждого узла

Dev/testing
	

InMemoryChatMessageHistory
	

MemorySaver()

Production
	

PostgresChatMessageHistory, RedisChatMessageHistory
	

SqliteSaver, PostgresSaver

Persistence
	

Требует явной настройки
	

Из коробки через checkpointer

Time travel
	

❌ Нет
	

✅ Откат к любому checkpoint

Human-in-the-loop
	

На костылях
	

✅ Нативно через interrupt_before/after

Управление
	

Ручное (callbacks, get_history)
	

Автоматическое

Применения
	

Простые чаты/ассистенты с небольшой историей
	

Сложные stateful workflows

## LangSmith и LangFuse

С фреймворками — разобрались (надеюсь), переходим к экосистеме.

В любом софте всегда может произойти что-то странное и необъяснимое, а в софте с LLM это фактически базово-ожидаемое поведение. И чтобы такого происходило меньше или чтобы уметь объяснять это необъяснимое, нам необходим трейсинг. Конечно, любой трейсинг можно сделать самостоятельно, но это бывает часто не так-то просто и точно всегда приводит к ухудшению читаемости кода. Поэтому трейсинг из коробки на уровне фреймворка — то, что доктор прописал.

LangChain и LangGraph — это семейство фреймворков, выпущенных одной командой. И эта же команда сделала сервис LangSmith, который нативно умеет все делать на уровне ядра. С ним замечательно все, кроме того, что он платный, SaaS-only и под другие фреймворки все уже не так нативно, а через sdk.

В качестве ответа такому безобразию от сторонней команды появился LangFuse — open-source альтернатива для трейсинга LLM-приложений. Его главное преимущество — on-premise, то есть его можно развернуть у себя. LangFuse работает не на уровне ядра и требует подключения через колбеки или декораторы.

	

LangSmith
	

LangFuse

Подключение
	

.env
	

Callbacks/декораторы

Self-hosting
	

Enterprise
	

✅ Open-source

Фреймворки
	

LangChain/LangGraph
	

Любые

Трейсинг
	

Автоматический
	

Ручной

Datasets & Evaluation
	

✅
	

✅

И, наконец, последние из семейства — для полноты информации.
LangFlow и LangServe, LangSmith Deployment и LangSmith Hub

LangFlow — это сторонний проект, построенный на базе LangChain/LangGraph, но разработанный независимой командой. Это визуальный слой над фреймворками, который позволяет собирать пайплайны и агентов в красивом интерфейсе. Примерно как n8n, dify и другие, но с использованием всей мощи ленгчейн-вселенной.

LangServe — официальный инструмент для превращения любого LangChain Runnable в production-ready REST API. Построен на FastAPI, автоматически генерирует OpenAPI документацию и поддерживает streaming, batching и вот это все. По сути, это автоматический мостик между цепочками/простыми агентами и внешним миром через HTTP.

LangSmith Deployment (ранее LangGraph Platform) — управляемый рантайм специально для long-running агентов. В отличие от LangServe (для простых цепочек), это полноценная инфраструктура с checkpointing, горизонтальным масштабированием, тасками и всеми взрослыми штуками.

LangSmith Hub — централизованный репозиторий промптов от большого комьюнити. Можно публиковать свои промпты, искать готовые решения и все нативно интегрировать в код:
```
from langchain import hub
prompt = hub.pull("username/my-prompt")
 ```



<https://habr.com/ru/companies/amvera/articles/933460/> Part 1

<https://habr.com/ru/companies/amvera/articles/948000/> Part 2

<https://habr.com/ru/companies/amvera/articles/949376/> Part 3

<https://habr.com/ru/search/?q=langGraph&target_type=posts&order=relevance>

  LongSmith Studio: <https://docs.langchain.com/langsmith/studio> Studio

  <https://habr.com/ru/companies/sberbank/articles/941340/>

  <https://habr.com/ru/companies/amvera/articles/931874/> MCP + LangGraph

## Agent Frameworks popularity

LangChain itself remains the most starred framework overall, with extensive tooling for chains, agents, and retrieval. 

Other high-star names in that same ranking include AutoGen, MetaGPT, LlamaIndex, and CrewAI. 
<https://realpython.com/crewai-python/>

Separately, Microsoft AutoGen tops one survey at over 60,000 stars, though notably its development pace has slowed.

## Popularity By actual production adoption (probably the more meaningful metric)

This is where LangGraph pulls ahead of raw-star leaders: LangGraph leads in enterprise adoption with 34.5 million monthly downloads, even though Dify leads in raw GitHub stars at 144k. 

Around 400 companies now use LangGraph Platform in production, including Cisco, Uber, LinkedIn, BlackRock, and JPMorgan. That gap between "stars" and "downloads/production use" is a real signal — stars skew toward what's trending on social media, downloads skew toward what teams actually ship with.

## Where the Claude Agent SDK fits

Claude Agent SDK isn't really competing on the same "framework popularity" axis as LangChain/LangGraph/CrewAI — it's a vendor SDK tied to Claude specifically, not a model-agnostic orchestration layer, and one analysis flags that vendor-SDK star counts are a poor adoption metric compared to model-agnostic frameworks, since npm/PyPI download counts capture vendor SDK usage far better than stars do. 

Its comparison set is really "Claude-committed teams choosing SDK vs. LangGraph vs. going lower-level with the base API," not a broad multi-framework popularity contest.

## The category split (this is the more useful lens than a single ranking)

By 2026 the space has fragmented into distinct lanes rather than one leaderboard:
```
- general-purpose orchestration (LangChain/LangGraph, AutoGen),
- coding agents,
- browser/voice automation,
- visual workflow builders
```
are now separate categories with different leaders.   
Python remains dominant overall,   
while TypeScript has captured the visual-workflow and IDE-extension corners:   
n8n, Flowise, Cline, Vercel AI SDK, Mastra.

Notably, the **Vercel** AI SDK isn't a traditional agent framework like LangGraph or **CrewAI** but is the most-downloaded TypeScript AI toolkit by a wide margin, at roughly 2.8 million weekly npm downloads.   

And TypeScript-native entrants like **Mastra** have crossed roughly 21,000 GitHub stars with enterprise adopters including Marsh McLennan and SoftBank.

LangChain/LangGraph - the explicit state machine, model-agnostic flexibility, and the human-in-the-loop gates  

**CrewAI** and **AutoGen** are the other Python-native names worth knowing exist, but they solve a different problem (role-based multi-agent crews) than what your dashboard pipeline needs.

Based on current sources, here's how these frameworks map to use cases as of mid-2026:

| Use case | Best fit | Why |
|---|---|---|
| **Production system needing durable state, checkpointing, human approval gates** | **LangGraph** | LangGraph wins on production readiness — the combination of durable execution, built-in checkpointing, enterprise-grade observability through LangSmith, and first-class human-in-the-loop support puts it ahead of the other frameworks. |
| **Fast prototyping, team new to agents, want something working same-day** | **CrewAI** | CrewAI has the best tutorials and getting-started experience — you can follow their quickstart and have something working in 30 minutes. CrewAI typically takes 30–60 lines of code to a first working agent, versus 80–150 for LangGraph. |
| **Role-based collaboration (researcher/writer/reviewer style teams)** | **CrewAI** | CrewAI's intuitive "roles + tasks" paradigm is ideal for sequential workflows, and it handles sequential and hierarchical flows out of the box, though complex branching needs workarounds. |
| **Agents that negotiate, critique, or iteratively refine each other's output** | **AG2** (AutoGen successor) | AutoGen/AG2 is best for multi-agent conversation loops — scenarios where agents negotiate, critique, or iteratively refine each other's outputs, like a Coder agent writing and a Reviewer agent pushing back until both agree. Note Microsoft merged original AutoGen with Semantic Kernel into the Microsoft Agent Framework in April 2026 and AutoGen is now in maintenance mode, so **AG2 specifically** (the community fork) is the actively developed line — AG2 introduced event-driven architecture and async message passing as the community-driven successor. |
| **Widest external tool/interoperability coverage (MCP + cross-vendor agents)** | **CrewAI** | CrewAI added native A2A (Agent-to-Agent) protocol support, plugging into the broadest ecosystem of external tools with the least custom code — LangGraph has only basic A2A support through partner integrations, and OpenAI Agents SDK's A2A integration is limited. |
| **Single agent, one or two tools, ship fast, already committed to one model vendor** | **OpenAI Agents SDK** *or* **Claude Agent SDK** | For a single agent that calls one or two tools, the OpenAI Agents SDK or Anthropic Claude Agent SDK is often a faster path in 2026 — both trade fine-grained orchestration control for simplicity, similar to AWS's Strands Agents, while OpenAI's SDK splits the difference with its handoff model. |
| **Deep code-generation/execution loops** | **AutoGen/AG2** | AutoGen excels when agents need to write and execute code. |
| **Type-safety-first development** | **PydanticAI** | PydanticAI is worth evaluating if you're a type-safety purist who wants Pydantic models governing every agent interaction. |
| **Already deep in Google Cloud stack** | **Google ADK** | Google ADK makes sense for teams already deep in the Google ecosystem. |
| **Validate architecture cheaply, then harden for production** | **CrewAI → LangGraph** | A legitimate strategy: start with CrewAI to validate your agent architecture quickly — does the workflow make sense, do the agents produce useful outputs — then migrate production-critical paths to LangGraph for checkpointing, error recovery, and observability. CrewAI's own documentation acknowledges this migration path. |

 

## Version/status notes worth knowing before you commit

- LangGraph never required LangChain, and since v1.0 (October 2025, now at 1.2) the package is fully standalone — you can use any LLM directly without LangChain abstractions.
- CrewAI passed 1.0 and is now at stable branch 1.15.x, handling persistence, partial streaming, and better error recovery than earlier versions.
- CrewAI reached v1.14 with A2A protocol support and enterprise features; AG2 emerged as AutoGen's community-driven successor with event-driven architecture.
- AutoGen's documentation is currently the weakest of the major frameworks because it's in transition from the Microsoft AutoGen branding to the AG2 fork — some docs still point to the old version. If you evaluate AG2, expect some doc friction from that split.

## For your situation specifically

Given the Databricks/analytics-dashboard pipeline we designed earlier — durable state, an explicit human-approval gate before SQL execution and dashboard publish — that's squarely LangGraph's use case per this table, not CrewAI's or AG2's. If you ever build something more exploratory first (e.g., prototyping whether a multi-table-join approach even makes sense before hardening it), CrewAI's fast-iteration model is worth it for that throwaway phase, per the "validate cheap, then migrate" pattern above.

 These are three genuinely different animals, all launched or gaining traction within the past few months — worth laying out what each one actually is before comparing them, since "agent framework" is doing a lot of work covering very different layers.

## What each one is

**Agno** — a Python framework + production runtime for multi-agent systems. It ships two halves: a lightweight Agent class (agents/teams/workflows, 100+ toolkits, memory, knowledge, reasoning, MCP, model-agnostic across 30+ providers) plus AgentOS, a stateless FastAPI runtime with tracing, scheduling, human approval, and RBAC that you deploy in your own cloud. It's the direct successor to phidata, rebranded in January 2025, and has grown to roughly 40,900 GitHub stars with 424 contributors as of mid-2026.

**Vercel's eve** — a TypeScript-only, opinionated open-source agent framework announced at Vercel Ship 2026 (June 17), described on stage as "Next.js for agents." An agent is literally a directory: markdown instructions, TypeScript tools, with durability, sandboxed compute, human-in-the-loop approvals, subagents, and evals built in, running on Vercel's Workflow SDK (checkpointed execution), Vercel Sandbox (isolated microVM execution), and the Vercel AI SDK for model calls. It's paired with a broader commercial platform push (Vercel Agent, Vercel Services, enterprise controls) — the framework is open source, but it's clearly the on-ramp to Vercel's paid infrastructure.

**LangChain Deep Agents** — not a new orchestration engine, but an opinionated harness built on top of LangGraph and `create_agent`, adding the specific capabilities that make agents handle *long-horizon* tasks well: planning (a forced todo-list tool for coherence), a virtual filesystem for persisting findings/context across steps, subagent spawning with isolated context, and Skills (progressive-disclosure domain instructions). It's explicitly modeled on Claude Code's architecture — LangChain has said Deep Agents were heavily influenced by what Claude Code does internally, generalized into a reusable library.

## Comparison table

| Dimension | Agno | Vercel eve | LangChain Deep Agents |
|---|---|---|---|
| **Language** | Python only | TypeScript only | Python (JS/TS via broader LangChain ecosystem) |
| **Layer** | Full framework + production runtime (AgentOS) | Framework + tightly coupled to Vercel's hosting/sandbox/workflow infra | Harness layered on top of LangGraph — not a new runtime |
| **Best use case** | Multi-agent systems needing your own infra control (data stays in your DB, no vendor retention) — e.g., a fleet of RAG/support/analytics agents | Full-stack apps where agents are part of a Next.js/Vercel-deployed product — coding agents, agent-triggered deployments | Long-running, complex single-agent tasks needing planning + memory across many steps — research, coding, deep multi-step analysis |
| **Deployment model** | Self-hosted AgentOS in your own cloud; paid tier only for the hosted control-plane UI | Runs on Vercel's platform (Sandbox, Workflow SDK) — the more you use, the more you're on Vercel's infra | Runs wherever LangGraph runs — self-hosted or LangSmith/LangGraph Platform |
| **Multi-agent support** | Native — "teams" is a first-class primitive alongside agents/workflows | Native — subagents built in | Native — subagent spawning with context isolation is a core feature |
| **Human-in-the-loop** | First-class — tool confirmations, approval workflows | First-class — built into the framework | Inherited from LangGraph's checkpointing/interrupt model |
| **MCP support** | Native, extensive | Not emphasized in announcements (Vercel AI SDK has its own tool-calling model) | Native — full MCP support documented |
| **Observability** | Native Tracing stored entirely in your own infra — no third-party vendor, no compliance/retention risk | Ties into Vercel's own traces/alerts (Vercel Agent uses these to investigate issues) | LangSmith integration (external, hosted by LangChain unless self-hosted) |
| **Maturity/momentum** | ~40k stars, 5,300+ commits, actively shipping (9 releases in April 2026 alone) | Brand new (announced June 2026) — credible backing (Vercel's own production agents run on it) but unproven at scale externally | Newer library (early-to-mid 2026) but built on the mature, widely-adopted LangGraph substrate |
| **Pricing** | Apache-2.0, free; $150/mo Pro for hosted control-plane, custom Enterprise | Open source framework; commercial tier is Vercel's broader platform (Services, Agent, enterprise controls) | Open source; LangSmith/LangGraph Platform hosting is the paid layer |

## How to think about the choice for you specifically

Given your stack (Python, Databricks, PySpark, no TypeScript/Next.js mentioned in what you build), **Vercel's eve is the one that doesn't fit** — it's TypeScript-only and its main value proposition is being deeply wired into Vercel's own hosting/sandbox infrastructure. It's the right tool if you're building a Next.js product where agents are part of the deployed app; it's not a fit for a backend analytics pipeline like the one we designed earlier.

**Agno vs. LangChain Deep Agents** is the more relevant comparison for you:
- **Agno** is closer to a *replacement* for LangGraph+LangSmith as a full stack — it wants to own orchestration, runtime, and observability together, with a strong "your data never leaves your infra" pitch. For your analytics-dashboard pipeline, Agno's Teams/Workflows primitives plus native MCP could genuinely replace the LangGraph graph we sketched, with less boilerplate — but you'd be picking a less battle-tested (though fast-growing) production dependency over LangGraph's much larger, longer-track-record ecosystem.
- **Deep Agents** is not a replacement for LangGraph in your pipeline — it's a *specialization* for a different problem shape: long-horizon, exploratory, planning-heavy tasks (think "investigate this data anomaly across many tables and write a report") rather than the fairly linear discover→generate→validate→execute→publish pipeline we designed, which is better served by LangGraph's explicit graph and human-in-the-loop interrupts. If a future piece of your work looks more like "let the agent freely explore the warehouse and write up findings" rather than a fixed pipeline, Deep Agents' planning/filesystem/subagent model is worth revisiting.

## One caveat

Vercel's own announcement numbers (agent-triggered deployments going from under 3% to over 50%, token volume 2T→20T/month) are self-reported marketing figures from a launch event, not independently verified — worth treating as directional company narrative rather than an industry-wide adoption metric. Agno's and Deep Agents' GitHub star/commit counts are more objectively checkable but still just proxies for popularity, not a guarantee of fit for your specific pipeline.
