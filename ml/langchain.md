## LangChain LangGraph

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

## A few numbers to treat cautiously

Some sources cite specific benchmark figures — e.g. LangGraph scoring 87% on task success rate benchmarks versus CrewAI's 82% with 1.8s average latency — but these come from a single vendor-adjacent blog rather than an independent, reproducible benchmark, so I'd treat them as directional, not authoritative.

## Version/status notes worth knowing before you commit

- LangGraph never required LangChain, and since v1.0 (October 2025, now at 1.2) the package is fully standalone — you can use any LLM directly without LangChain abstractions.
- CrewAI passed 1.0 and is now at stable branch 1.15.x, handling persistence, partial streaming, and better error recovery than earlier versions.
- CrewAI reached v1.14 with A2A protocol support and enterprise features; AG2 emerged as AutoGen's community-driven successor with event-driven architecture.
- AutoGen's documentation is currently the weakest of the major frameworks because it's in transition from the Microsoft AutoGen branding to the AG2 fork — some docs still point to the old version. If you evaluate AG2, expect some doc friction from that split.

## For your situation specifically

Given the Databricks/analytics-dashboard pipeline we designed earlier — durable state, an explicit human-approval gate before SQL execution and dashboard publish — that's squarely LangGraph's use case per this table, not CrewAI's or AG2's. If you ever build something more exploratory first (e.g., prototyping whether a multi-table-join approach even makes sense before hardening it), CrewAI's fast-iteration model is worth it for that throwaway phase, per the "validate cheap, then migrate" pattern above.
 
