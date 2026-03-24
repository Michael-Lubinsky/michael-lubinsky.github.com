## Agents

<https://www.youtube.com/watch?v=ESBMgZHzfG0> AI Periodic table

<https://ecc.tools/>

<https://github.com/gepa-ai/gepa>

<https://medium.com/@durgaktkm/building-agentic-ai-applications-in-2026-872aefe192f6>

<https://habr.com/ru/articles/1013330/>

<https://habr.com/ru/articles/1013272/>

<https://github.com/garrytan/gstack> 

<https://habr.com/ru/companies/ostrovok/articles/1008652/>

<https://habr.com/ru/articles/1010430/>

 <https://habr.com/ru/articles/1010236/>

 <https://github.com/obra/superpowers>

 <https://habr.com/ru/companies/alfa/articles/1000342/>  

Free book online
<https://www.manning.com/books/build-a-multi-agent-system-from-scratch>

<https://openrouter.ai/>

<https://github.com/BerriAI/litellm>

## Agents orchestration via md files
<https://habr.com/ru/articles/1009534/>

The 100 line AI agent that solves GitHub issues or helps you in your command line.
<https://github.com/SWE-agent/mini-swe-agent/>

<https://github.com/jbonatakis/blackbird>

<https://simonwillison.net/guides/agentic-engineering-patterns/>

<https://simonwillison.net/2025/Dec/31/the-year-in-llms/#the-year-of-conformance-suites>

<https://crawshaw.io/blog/eight-more-months-of-agents>

<https://github.com/FareedKhan-dev/all-agentic-architectures>

<https://github.com/Tiendil/donna>

<https://blog.tedivm.com/guides/2026/03/beyond-the-vibes-coding-assistants-and-agents/>

<https://github.com/gsd-build/get-shit-done>  Behind the scenes: context engineering, XML prompt formatting, subagent orchestration, state management. What you see: a few commands that just work.

Создание умных AI-агентов: полный курс по LangGraph от А до Я. Часть 2. Диалоговые агенты: память, сообщения и контекст 
<https://habr.com/ru/companies/amvera/articles/948000/>

<https://github.com/Mathews-Tom/Agentic-Design-Patterns>


<https://habr.com/ru/articles/951428/> Что такое AI-агент и из каких основных частей он состоит

### Spec Driven Development, OpenSpec

<https://openspec.dev/>

<https://habr.com/ru/articles/1007048/>

<https://habr.com/ru/articles/985990/>


### Tool calling  (sometimes referred to as function calling) 

Tool calling refers to the ability of artificial intelligence (AI) models to interact with external tools, application programming interfaces (APIs) or systems to enhance their functions.

Instead of relying solely on pretrained knowledge, an AI system with tool-calling capabilities can query databases, fetch real-time information, execute functions or perform complex operations beyond its native capabilities.

<https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling>


 #### grep-ast - can be used as tool calling
 умеет находить в коде структурные сущности - классы, методы, точки входа, значит это не просто CLI-утилита для разработчика. Это готовая операция навигации по коду, которую можно дать агенту как инструмент.

 <https://habr.com/ru/companies/ecom_tech/articles/1005610/>

### Sub-agents

<https://habr.com/ru/articles/1006602/>
 
### MCP

<https://habr.com/ru/articles/1005028/>

<https://habr.com/ru/articles/1006756/>

<https://habr.com/ru/articles/1006756/>

## Pi

<https://pi.dev/>

<https://shivamagarwal7.medium.com/agentic-ai-pi-anatomy-of-a-minimal-coding-agent-powering-openclaw-5ecd4dd6b440>

<https://github.com/can1357/oh-my-pi>

<https://news.ycombinator.com/item?id=47143754>

## OpenClaw
<http://docs.openclaw.ai/>  
<https://clawdhub.com/>  
<https://habr.com/ru/articles/991264/>  
<https://habr.com/ru/articles/990786/>




```bash
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
```

### Setup OpenClaw
<https://habr.com/ru/articles/992720/>
```
curl -fsSL https://openclaw.ai/install.sh | bash

or 
npm install -g clawdbot
```

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

У обычных чат-ботов память это их контекстное окно (тот чат в котором мы с ними общаемся).
Закрыл вкладку и он всё забыл (а ведь реально раздражает по новой объяснять ту же задачу, но в новой вкладке). В OpenClaw свой интересный подход: вся память это обычные Markdown-файлы в ~/.openclaw/workspace/.

Что находится в ~/.openclaw/workspace/:

SOUL.md - там личность бота. Его тон, стиль, границы, имя, характер, привычки. Можно переписать под себя: хоть формальным, хоть саркастичным.

AGENTS.md - это правила поведения. Что делать при старте сессии, как вести себя в группах, какие действия требуют подтверждения. Самый важный файл для контроля уровня вседозволенности и автономности (чтобы не натворил делов).

USER.md - данные о тебе любимом. "Люблю горячие бутерброды", "Python в разы лучше C++", "работаю в на трех работах", "мой любимый сериал - Молодежка". 
Бот пополняет этот файл по ходу общения, можно явно говорить что туда заносить.

MEMORY.md - тут долгосрочные заметки. Ключевые решения, важные выводы, повторяющиеся ответы на вопросы и тд. Загружается только в main session (не в групповых чатах для твоей приватности).

memory/YYYY-MM-DD.md - это ежедневник / дневник. Бот пишет туда постоянно информацию достаточно важную, чтобы хоть куда-то сохранить, но слишком не важную чтобы оказаться в Memory.md.
Бот читает файлы за сегодня и вчера перед каждым ответом. Можно всегда указать конкретный период времени, на который стоит посмотреть.

Pi - это чистый лист при каждом запуске, никакой встроенной памяти между сессиями. 
Вся преемственность только в файлах, поэтому перед ответом агент заново читает SOUL.md, USER.md, MEMORY.md и дне
вные заметки (твои лимиты токенов в восторге 😁).
```

### Как устроен skill
```
Это папка с файлом SKILL.md (YAML-метаданные + инструкции для агента) и опциональными скриптами/файлами/всё что может пригодиться:

skills/my-skill/
  SKILL.md       # Описание + инструкции
  helper.py      # Вспомогательный скрипт (опционально)
 
YAML-фронтматтер задаёт зависимости:

name: github
description: Interact with GitHub using the gh CLI.
metadata: {"openclaw":{"requires":{"bins":["gh"]}}}
 
Всё и из названий полей понятно, особо комментировать нечего.
Из интересного это поле requires.bins - это своего рода гейтинг: 
если gh (в данном примере) не установлен, skill спит, поставил - проснулся.

Skill можно писать как в ручную, так и с помощью самого OpenClaw.
Описываешь ему задачу в чате, говоришь - "реши мне ее и запомни как это сделал". Например - "Создай skill для ресайза изображений с водяным знаком".
OpenClaw через встроенный skill-creator сам напишет скрипт, сгенерирует структуру и создаст SKILL.md с примерами (успешность, конечно, зависит от твоей задачи).

Есть больше 50 навыков из коробки: Apple Notes/Reminders/Things 3, Gmail/Calendar/Drive (через gog CLI), Slack, iMessage, Twitter/X, Philips Hue, Sonos, Eight Sleep, GitHub CLI, Whisper и другие.
А есть ещё ClawHub - это мини-реестр навыков, включаешь его и агент сам ищет и подтягивает нужные skills по мере необходимости.
```

```
Проактивность: бот, который пишет первым ⏰
Чат-боты по дефолту первыми тебе не напишут, это всегда только ответы на твои сообщения. OpenClaw умеет инициировать контакт и это одна из его сильных сторон
(да, я знаю, что тут (как и во многих других штуках) он не первопроходец и это уже есть, но в купе с другими фишками, это подкупает).

Как он это делает?

Создаем файл (хоть руками, хоть вместе с агентом) HEARTBEAT.md с чек-листом: "проверяй sports.ru каждое утро", "проверяй календарь на мои синки каждые 2 часа", "если молчал 4+ часа - пришли "я живой, все хорошо"." 

Настраиваешь интервал и рабочие часы в ~/.opencrew/opencrew.json.

{
  "agents": {
	"defaults": {
  	"heartbeat": {
    	"every": "15m",
    	"activeHours": { "start": "06:00", "end": "23:00" }
  	}
	}
  }
}
 
Бот периодически прогоняет список - если есть что сообщить, сам напишет, а если задач не нашлось, то пропускает ход. Обычный классический такт, ничего гениального нет, но всё еще очень удобно.

А еще есть возможность дать задачи по точному расписанию. Делается это с помощью cron задач:

# Утренняя личная подборка, каждый день в 9:00
openclaw cron add --name "Утро" --cron "0 9 * * *" \
  --message "Погода, календарь, важные письма, результат Лиги Чемпионов"

```


## Skills

<https://habr.com/ru/articles/1011524/>

<https://habr.com/ru/articles/1001830/>  
<https://agentskills.io/>  
<https://agentskills.io/specification>  
<https://www.aitmpl.com/skills>  

<https://github.com/ComposioHQ/awesome-claude-skills>

<https://github.com/K-Dense-AI/claude-scientific-skills>

https://www.youtube.com/watch?v=dTp3gbpT5G8

 
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

<https://habr.com/ru/companies/bitrix/articles/980654/>

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




### Axelrod tournament

<https://vknight.org/2025/10/21/rrr.html> Axelrod tournament

https://en.wikipedia.org/wiki/The_Evolution_of_Cooperation

https://en.wikipedia.org/wiki/Anatol_Rapoport

https://en.wikipedia.org/wiki/Tit_for_tat
