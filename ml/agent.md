## Agents

https://simonwillison.net/2025/Dec/31/the-year-in-llms/#the-year-of-conformance-suites

https://crawshaw.io/blog/eight-more-months-of-agents

https://github.com/Tiendil/donna

https://github.com/gsd-build/get-shit-done  Behind the scenes: context engineering, XML prompt formatting, subagent orchestration, state management. What you see: a few commands that just work.



### Claude 

which claude
/opt/homebrew/bin/claude
```
claude --help
Usage: claude [options] [command] [prompt]

Claude Code - starts an interactive session by default, use -p/--print for non-interactive output

Arguments:
  prompt                                            Your prompt

Options:
  --add-dir <directories...>                        Additional directories to allow tool access to
  --agent <agent>                                   Agent for the current session. Overrides the 'agent' setting.
  --agents <json>                                   JSON object defining custom agents (e.g. '{"reviewer": {"description": "Reviews code", "prompt": "You are a code
                                                    reviewer"}}')
  --allow-dangerously-skip-permissions              Enable bypassing all permission checks as an option, without it being enabled by default. Recommended only for
                                                    sandboxes with no internet access.
  --allowedTools, --allowed-tools <tools...>        Comma or space-separated list of tool names to allow (e.g. "Bash(git:*) Edit")
  --append-system-prompt <prompt>                   Append a system prompt to the default system prompt
  --betas <betas...>                                Beta headers to include in API requests (API key users only)
  --chrome                                          Enable Claude in Chrome integration
  -c, --continue                                    Continue the most recent conversation in the current directory
  --dangerously-skip-permissions                    Bypass all permission checks. Recommended only for sandboxes with no internet access.
  -d, --debug [filter]                              Enable debug mode with optional category filtering (e.g., "api,hooks" or "!1p,!file")
  --debug-file <path>                               Write debug logs to a specific file path (implicitly enables debug mode)
  --disable-slash-commands                          Disable all skills
  --disallowedTools, --disallowed-tools <tools...>  Comma or space-separated list of tool names to deny (e.g. "Bash(git:*) Edit")
  --fallback-model <model>                          Enable automatic fallback to specified model when default model is overloaded (only works with --print)
  --file <specs...>                                 File resources to download at startup. Format: file_id:relative_path (e.g., --file file_abc:doc.txt
                                                    file_def:img.png)
  --fork-session                                    When resuming, create a new session ID instead of reusing the original (use with --resume or --continue)
  --from-pr [value]                                 Resume a session linked to a PR by PR number/URL, or open interactive picker with optional search term
  -h, --help                                        Display help for command
  --ide                                             Automatically connect to IDE on startup if exactly one valid IDE is available
  --include-partial-messages                        Include partial message chunks as they arrive (only works with --print and --output-format=stream-json)
  --input-format <format>                           Input format (only works with --print): "text" (default), or "stream-json" (realtime streaming input) (choices:
                                                    "text", "stream-json")
  --json-schema <schema>                            JSON Schema for structured output validation. Example:
                                                    {"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}
  --max-budget-usd <amount>                         Maximum dollar amount to spend on API calls (only works with --print)
  --mcp-config <configs...>                         Load MCP servers from JSON files or strings (space-separated)
  --mcp-debug                                       [DEPRECATED. Use --debug instead] Enable MCP debug mode (shows MCP server errors)
  --model <model>                                   Model for the current session. Provide an alias for the latest model (e.g. 'sonnet' or 'opus') or a model's full
                                                    name (e.g. 'claude-sonnet-4-5-20250929').
  --no-chrome                                       Disable Claude in Chrome integration
  --no-session-persistence                          Disable session persistence - sessions will not be saved to disk and cannot be resumed (only works with --print)
  --output-format <format>                          Output format (only works with --print): "text" (default), "json" (single result), or "stream-json" (realtime
                                                    streaming) (choices: "text", "json", "stream-json")
  --permission-mode <mode>                          Permission mode to use for the session (choices: "acceptEdits", "bypassPermissions", "default", "delegate",
                                                    "dontAsk", "plan")
  --plugin-dir <paths...>                           Load plugins from directories for this session only (repeatable)
  -p, --print                                       Print response and exit (useful for pipes). Note: The workspace trust dialog is skipped when Claude is run with
                                                    the -p mode. Only use this flag in directories you trust.
  --replay-user-messages                            Re-emit user messages from stdin back on stdout for acknowledgment (only works with --input-format=stream-json
                                                    and --output-format=stream-json)
  -r, --resume [value]                              Resume a conversation by session ID, or open interactive picker with optional search term
  --session-id <uuid>                               Use a specific session ID for the conversation (must be a valid UUID)
  --setting-sources <sources>                       Comma-separated list of setting sources to load (user, project, local).
  --settings <file-or-json>                         Path to a settings JSON file or a JSON string to load additional settings from
  --strict-mcp-config                               Only use MCP servers from --mcp-config, ignoring all other MCP configurations
  --system-prompt <prompt>                          System prompt to use for the session
  --tools <tools...>                                Specify the list of available tools from the built-in set. Use "" to disable all tools, "default" to use all
                                                    tools, or specify tool names (e.g. "Bash,Edit,Read").
  --verbose                                         Override verbose mode setting from config
  -v, --version                                     Output the version number

Commands:
  doctor                                            Check the health of your Claude Code auto-updater
  install [options] [target]                        Install Claude Code native build. Use [target] to specify version (stable, latest, or specific version)
  mcp                                               Configure and manage MCP servers
  plugin                                            Manage Claude Code plugins
  setup-token                                       Set up a long-lived authentication token (requires Claude subscription)
  update|upgrade                                    Check for updates and install if available


Example:

  claude -p "<prompt>" \
    --append-system-prompt "<identity + memory instructions>" \
    --tools "Bash,Read,Write,Edit" \
    --allowedTools "Bash,Read,Write,Edit" \
    --add-dir ~/.epiphyte/memory \
    --model opus \
    --output-format stream-json \
    --resume <session-id> 


```
## Pi
https://shivamagarwal7.medium.com/agentic-ai-pi-anatomy-of-a-minimal-coding-agent-powering-openclaw-5ecd4dd6b440

## OpenClaw
<http://docs.openclaw.ai/>  
<https://clawdhub.com/>  
<https://habr.com/ru/articles/991264/>  
<https://habr.com/ru/articles/990786/>

```js
# Скачиваем и устанавливаем nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# Вместо перезапуска оболочки (применяем изменения в текущей сессии):
\. "$HOME/.nvm/nvm.sh"

# Скачиваем и устанавливаем Node.js:
nvm install 22

# Проверяем версию Node.js:
node -v # Должно вывести "v22.22.0".

# Проверяем версию npm:
npm -v # Должно вывести "10.9.4".


curl -fsSL https://openclaw.ai/install.sh | bash

or 
npm install -g clawdbot
```
После установки (к примеру через npm install -g clawdbot) приложение настраивается мастером:
он создаёт рабочую директорию (~/clawd/ по умолчанию), 
генерирует конфиг ~/.clawdbot/clawdbot.json и собирает скелет ассистента из файлов Markdown. 
Там же лежит то, что в обычных продуктах спрятано глубоко в базе данных: 
память, 
инструкции, 
список инструментов, 
описания навыков (скилов). 

Всё это — просто текстовые файлы, которые можно открыть, почитать, отредактировать и закоммитить обратно, если очень захотелось.

4 ключевых компонента:
Gateway — фоновый демон, который держит подключения к мессенджерам (Telegram, WhatsApp, что угодно из 50+
 интеграций).

Agent — собственно LLM, который интерпретирует ваши намерения.

Skills — модульные возможности: браузер, файловая система, календарь, кастомные интеграции.

Memory — персистентное хранилище в обычных Markdown-файлах, которое можно читать и редактировать руками.

Где бы ни запускался Gateway, паттерн работы одинаков: это локальный агент и внешний канал связи. Агент хранит память и инструкции, обращается к БЯМ для своей работы,
 а Gateway держит коннекторы к чатам и веб-порт, по умолчанию на 127.0.0.1:18789.

(По умолчанию внешних соединений не будет, поэтому для доступа с другого устройства нужно поменять пара
метр gateway.bind на 0.0.0.0).
Также на этом порту в браузере открывается простенький Control UI, написанный на Vite и Lit.

```

https://habr.com/ru/companies/alfa/articles/1000342/  
https://anthropic.skilljar.com/claude-code-in-action  
https://code.claude.com/docs  
https://code.claude.com/docs/en/cli-reference  
https://habr.com/ru/articles/983214/   
https://habr.com/ru/articles/984160/ Claude Code  Agent  

https://www.dev-log.me/pr_review_navigator_for_claude/  Skill for code review

https://psantanna.com/claude-code-my-workflow/workflow-guide.html

## Skills
https://habr.com/ru/articles/1001830/  
https://agentskills.io/
https://www.aitmpl.com/skills 

https://www.youtube.com/watch?v=dTp3gbpT5G8

## ChatGPT
<https://habr.com/ru/articles/981624/> How to use ChatGPT effectively  

## Codex from OpenAI
<https://habr.com/ru/companies/ods/articles/1001012/>
Claude Code написан на TypeScript.  
Codex CLI написан на Rust. 

### Cursor
<https://habr.com/ru/articles/984656/>  Cursor Agent

<https://habr.com/ru/articles/987528/>

<https://mariozechner.at/posts/2025-11-30-pi-coding-agent/>    
<https://news.ycombinator.com/item?id=46844822>

<https://www.freecodecamp.org/news/how-to-build-advanced-ai-agents/>
<https://ampcode.com/how-to-build-an-agent>

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
