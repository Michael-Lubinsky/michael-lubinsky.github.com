## Agents

https://simonwillison.net/2025/Dec/31/the-year-in-llms/#the-year-of-conformance-suites

https://crawshaw.io/blog/eight-more-months-of-agents

https://github.com/Tiendil/donna

### Claude 
https://anthropic.skilljar.com/claude-code-in-action
https://code.claude.com/docs  
https://code.claude.com/docs/en/cli-reference  
https://habr.com/ru/articles/983214/   
https://habr.com/ru/articles/984160/ Claude Code  Agent  

https://www.dev-log.me/pr_review_navigator_for_claude/  Skill for code review

https://psantanna.com/claude-code-my-workflow/workflow-guide.html

## Skills

https://agentskills.io/
https://www.aitmpl.com/skills 

https://www.youtube.com/watch?v=dTp3gbpT5G8

## ChatGPT
https://habr.com/ru/articles/981624/  How to use ChatGPT effectively  

### Cursor
https://habr.com/ru/articles/984656/  Cursor Agent

https://habr.com/ru/articles/987528/
https://mariozechner.at/posts/2025-11-30-pi-coding-agent/  
https://news.ycombinator.com/item?id=46844822

https://www.freecodecamp.org/news/how-to-build-advanced-ai-agents/ 
https://ampcode.com/how-to-build-an-agent

https://www.mihaileric.com/The-Emperor-Has-No-Clothes/

https://github.com/SWE-agent/mini-swe-agent

https://github.com/rcarmo/python-steward

https://habr.com/ru/articles/979012/ Собираем LLM-агента на Python

https://habr.com/ru/articles/953154/ Как ИИ-агенты учатся работать с временными рядами

### Microsoft AI Agents for beginners (lessons 1-10)
https://www.youtube.com/watch?v=OhI005_aJkA&list=PLlrxD0HtieHgKcRjd5-8DT9TbwdlDO-OC

https://github.com/microsoft/ai-agents-for-beginners

https://github.com/nicolasahar/morphic-programming

https://habr.com/ru/articles/951428/

https://github.com/Mathews-Tom/Agentic-Design-Patterns

https://learn.microsoft.com/en-us/shows/ai-agents-for-beginners/

https://habr.com/ru/companies/otus/articles/978426/

https://habr.com/ru/articles/981650/

https://habr.com/ru/articles/981100/

https://pub.towardsai.net/building-production-grade-ai-agents-in-2025-the-complete-technical-guide-9f02eff84ea2

1. Google's Agent Whitepaper: http://lnkd.in/gFvCfbSN
2. Google's Agent Companion: http://lnkd.in/gfmCrgAH
3. Building Effective Agents by Anthropic: http://lnkd.in/gRWKANS4.
4. Claude Code Best Agentic Coding practices: http://lnkd.in/gs99zyCf
5. OpenAI's Practical Guide to Building Agents: http://lnkd.in/guRfXsFK


## Aider vs Claude CLU - Architecture difference between “model CLIs” and “agent coding shells"

> You use **Aider** when you want a repo-editing coding agent.
> You use **Claude CLI** when you want a direct LLM interface (chat + commands).

They overlap, but they’re not the same tool category.

---

##  Mental model first

| Tool       | Role                  |
| ---------- | --------------------- |
| Claude CLI | AI brain terminal     |
| Aider      | AI coding agent shell |

Analogy:

* Claude CLI = talking to an engineer
* Aider = project manager + Git editor + engineer

---

## 🔍 Core architectural difference

## Claude CLI

Provides:

* Chat
* File reading/writing (if enabled)
* Command execution (Computer Use)
* General reasoning

But repo workflows are ad-hoc.

You must say things like:

> “Edit src/foo.py and add X.”

It doesn’t inherently manage diffs, Git commits, or patch safety.

---

## Aider

Built specifically for coding repos.

Provides:

* Automatic file tracking
* Patch diffs
* Git commits
* Multi-file edits
* Test-driven loops
* Conflict handling

So it wraps the model with coding workflows.


### 📊 Feature comparison

| Capability           | Claude CLI  | Aider     |
| -------------------- | ----------- | --------- |
| Chat with LLM        | ✅           | ✅         |
| Edit files           | ✅           | ✅         |
| Repo awareness       | Medium      | High      |
| Git integration      | ❌           | ✅         |
| Patch diffs          | ❌           | ✅         |
| Auto commits         | ❌           | ✅         |
| Multi-file refactors | Manual      | Native    |
| Test loops           | Manual      | Supported |
| Model choice         | Claude only | Any       |

---

### 🧪 Example — your ONNX CLI project

## Using Claude CLI directly

You’d do:

```
Write summarize.py to parse ONNX graph.
```

Then:

* Copy/paste code
* Save file
* Run tests
* Ask for fixes
* Apply patches manually

Workflow = conversational.

---

## Using Aider

You’d run:

```bash
aider src tests
```

Prompt:

```
Build CLI tool to summarize ONNX models.
```

Aider will:

1. Create files
2. Apply diffs
3. Commit changes
4. Track modified files
5. Iterate via tests

Workflow = agentic.

---

### 🧩 Where Aider adds value

## 1) Git-native editing

Aider shows diffs like:

```diff
+ def summarize_model(path):
+     model = onnx.load(path)
```

You approve or reject.

Claude CLI → no built-in diff workflow.

---

### 2) Multi-file refactors

Example:

> “Rename summarize() to summarize_model() everywhere.”

Aider updates:

* CLI
* Imports
* Tests

Claude CLI → you must orchestrate.

---

### 3) Test-driven development loops

You can do:

```
Fix failing pytest tests.
```

Aider:

* Reads failures
* Edits code
* Re-runs loop (conceptually)

Claude CLI → manual copy/paste cycle.

---

### 4) Model portability

Aider can switch brains:

* Claude today
* DeepSeek tomorrow
* Local model offline

Claude CLI → locked to Claude.

---

### 🧭 When Claude CLI alone is enough

Use Claude CLI if you want:

* One-off scripts
* Concept design
* Debug help
* Architecture brainstorming
* Terminal automation

Example:

> “Explain ONNX graph structure.”

No repo edits needed.

---

### 🧭 When Aider is better

Use Aider if you want:

* Persistent coding agent
* Git-managed changes
* Multi-file edits
* Automated refactors
* Test iteration

Your ONNX CLI project fits here.

---

### ⚖️ Cost & infra angle

| Factor              | Claude CLI    | Aider       |
| ------------------- | ------------- | ----------- |
| Model cost          | Claude tokens | Same tokens |
| Tool cost           | Paid          | Free OSS    |
| Local model support | ❌             | ✅           |
| Offline coding      | ❌             | ✅           |

So Aider can reduce costs if you use local models.

---

### 🧩 Real-world stack patterns

Common setups:

### Claude-only

```
Claude CLI → code → manual edits
```

### Aider + Claude

```
Aider shell → Claude brain → Git patches
```

### Aider + DeepSeek (free)

```
Aider shell → Local model → Git patches
```

---

###  Why both exist

Because they solve different layers:

| Layer           | Tool       |
| --------------- | ---------- |
| LLM reasoning   | Claude CLI |
| Coding workflow | Aider      |

Codex.app bundles both into one product.

Open-source world splits them.

---

# ✅ Bottom line

Use Claude CLI if:

* You want direct AI interaction
* Repo edits are light/manual

Use Aider if:

* You want an autonomous coding agent
* You want Git-native edits
* You want multi-file refactors
* You want model flexibility

For your ONNX summarizer project:

> Claude CLI = helpful
> Aider = more productive

---

If you want, I can:

* Show side-by-side workflow (Claude CLI vs Aider) building your ONNX CLI
* Recommend cheapest model stack
* Provide a ready-to-run Mac setup script (brew + pip + ollama + aider)


   
### Agent Skills:
<https://skillsmp.com/>

<https://habr.com/ru/articles/987552/>

<https://habr.com/ru/articles/987552/>
```
Agent Skills (навыки агентов) - это новый архитектурный паттерн для LLM-агентов,
позволяющий имитировать наличие у модели набора узкоспециализированных компетенций.
Технически Skill - это директория, содержащая манифест с инструкциями (SKILL.md)
и связанные ресурсы (скрипты, шаблоны, справочники).
Идея была впервые формализована компанией Anthropic осенью 2025 года,
а к концу 2025-го стала открытым стандартом, поддерживаемым индустрией.
Проще говоря, skill - это «упакованный» кусочек экспертного опыта или пошаговой процедуры,
 который агент может динамически загрузить и применить, когда этот навык ему пригодится.
```
https://habr.com/ru/companies/bitrix/articles/980654/

Структура skill к концу 2025 года уже стала де-факто стандартом (поддерживается сообществом ).   
Вот как выглядит типичный навык в файловой системе:
```
my-cool-skill/
├── SKILL.md          # Манифест и инструкции
├── scripts/          # Исполняемый код (напр. Python или Bash)
├── references/       # Справочные материалы (например, перечень кодов ошибок)
└── assets/           # Шаблоны документов, письма и пр.
```

```
Главный файл - SKILL.md. Это гибрид YAML и Markdown: он начинается с YAML-заголовка,
где указываются метаданные навыка, а далее следует собственно инструкция в MD-разметке. Пример (упрощенный фрагмент для иллюстрации):
---
name: production-incident-triage
description: Используй этот навык при алертах P0/P1 для первичной диагностики и коммуникации.
---

# Incident Triage Procedure
## 1. Context Collection
Сначала собери метрики за последние 15 минут.  
Используй tool query_grafana с дашбордом main-cluster-v2.

## 2. Severity Check
ЕСЛИ error_rate > 5% ИЛИ latency p99 > 2s:
  - Объяви инцидент через tool create_jira_ticket.
  - Используй шаблон из файла assets/incident-template.md.

## 3. Communication
Не пиши отсебятину. Используй строгий стиль из references/comms-guide.md.

```

### Axelrod tournament

<https://vknight.org/2025/10/21/rrr.html> Axelrod tournament

https://en.wikipedia.org/wiki/The_Evolution_of_Cooperation

https://en.wikipedia.org/wiki/Anatol_Rapoport

https://en.wikipedia.org/wiki/Tit_for_tat
