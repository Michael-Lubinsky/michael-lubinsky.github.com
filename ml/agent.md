## Agents

<https://habr.com/ru/articles/1050736/>

<https://habr.com/ru/articles/1051166/> Tools, Hooks, Skills, MCP — что есть что?

<https://belderbos.dev/blog/build-minimal-ai-agent-python/>
<https://blog.adarshd.dev/ai/posts/building-ai-agents-in-python/>

Postgres + Agent
<https://www.reddit.com/r/PostgreSQL/comments/1tyewxr/how_an_ai_agent_with_50_tools_queries_postgresql/>

<https://habr.com/ru/articles/1051346/>  Аналитику, которую нельзя выразить в SQL запрос, выносить в Python в песочницу. И описывать данные и схему так, чтобы модель не гадала, что внутри. Эти три вещи мы и зашили в свой MCP-сервер: фронт на Next.js (ai-sdk), бэкенд на FastMCP, под капотом DuckDB, модель ходит в данные только через инструменты.

<https://habr.com/ru/articles/1047230/>

<https://habr.com/ru/companies/postgrespro/articles/1045532/>

<https://habr.com/ru/companies/cloud_ru/articles/1045728/>

<https://news.ycombinator.com/item?id=48413629>  SDD , harness, etc

<https://news.ycombinator.com/item?id=48406174>

<https://news.ycombinator.com/item?id=48449187>  tools you have made for yourself since the advent of AI?

<https://github.com/DrCatHicks/learning-opportunities>

<https://www.youtube.com/watch?v=V9j4smzlVCw> Book and repo: Crack Any Codebase with AI: Zachary Huang on Understanding Code You Didn’t Write

<https://habr.com/ru/companies/doubletapp/articles/1036872/>

<https://habr.com/ru/companies/svoi_ru/articles/1043188/>

<https://www.youtube.com/watch?v=VctYHtCap3o>  Agents Week 2026 | Лекция 1.2 2026 (ru)

<https://www.youtube.com/watch?v=RqM3G3STkGE>  Agents Week | Лекция 4 | 2026 (ru)

<https://www.youtube.com/watch?v=sNemTIFlz08> Agents Week 2026 | Лекция 5.1 

<https://www.youtube.com/watch?v=UxgjgvI_wKY> Agents Week 2026 | Лекция 5.2 

<https://habr.com/ru/companies/netologyru/articles/1034130/>

<https://habr.com/ru/articles/1023316/>  Что такое Harness?

<https://habr.com/ru/articles/1028260/> обширный материал по Context Engineering

<https://habr.com/ru/articles/1025428/> AI-агент : Python, RAG и внешние инструменты через MCP 

<https://habr.com/ru/articles/1031440/>

<https://habr.com/ru/articles/1033136/>

<https://habr.com/ru/articles/1019652/> MCP

<https://habr.com/ru/articles/1032932/> 

<https://habr.com/ru/articles/1035300/> метрики характерные для почти любой агентской системы

<https://habr.com/ru/articles/1043198/> Как превратить стохастический ИИ в детерминированную машину

<https://agenticeng.ru/>

## Claude question: which skills, tools and MCP are available in this session?


###  Skills (via /skill-name or Skill tool)
```
  ┌──────────────────────────┬─────────────────────────────────────────────────────────┐
  │          Skill           │                         Purpose                         │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ update-config            │ Configure Claude Code settings.json, hooks, permissions │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ keybindings-help         │ Customize keyboard shortcuts                            │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ simplify                 │ Review changed code for quality/efficiency              │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ fewer-permission-prompts │ Add allowlist to reduce permission prompts              │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ loop                     │ Run a prompt on a recurring interval                    │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ schedule                 │ Schedule recurring remote agents (cron jobs)            │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ claude-api               │ Build/debug Anthropic SDK apps                          │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ init                     │ Initialize CLAUDE.md                                    │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ review                   │ Review a pull request                                   │
  ├──────────────────────────┼─────────────────────────────────────────────────────────┤
  │ security-review          │ Security review of pending changes                      │
  └──────────────────────────┴─────────────────────────────────────────────────────────┘
```
### Tools (built-in)

  File & Shell: Read, Edit, Write, Bash

  Agents: Agent (with subtypes: claude, claude-code-guide, Explore, general-purpose, Plan,
  statusline-setup)

  UI/Flow: AskUserQuestion, Skill, ToolSearch

  #### Deferred (require ToolSearch to load schema before use):
  CronCreate/Delete/List, EnterPlanMode/ExitPlanMode, EnterWorktree/ExitWorktree, Monitor,
  NotebookEdit, PushNotification, RemoteTrigger, TaskCreate/Get/List/Output/Stop/Update, WebFetch,
  WebSearch

  Misc: ShareOnboardingGuide, ScheduleWakeup

 ### MCP Servers

  Three Google integrations (all require OAuth authentication):   
  - mcp__claude_ai_Gmail — Gmail read/send
  - mcp__claude_ai_Google_Calendar — Calendar access
  - mcp__claude_ai_Google_Drive — Drive file access




## Code search - better then grep, saves tokens

<https://habr.com/ru/articles/1051504/>

<https://habr.com/ru/articles/1052776/> graphlens

<https://habr.com/ru/articles/1049814/>

<https://habr.com/ru/articles/1050204/>

<https://habr.com/ru/articles/1046672/>

<https://habr.com/ru/articles/1042930/>

<https://habr.com/ru/articles/1038474/> CodeGraph

<https://habr.com/ru/articles/1031878/> SocratiCode

<https://maki.sh/>

<https://github.com/lightonai/next-plaid/tree/main/colgrep>

<https://github.com/DeusData/codebase-memory-mcp>

How does it compare to _context-mode_ or _serina_ that are both well established now?

<https://github.com/MinishLab/semble>  Code Search for Agents. Uses ~98% fewer tokens than grep+read

<https://github.com/defendend/Claude-ast-index-search>

### Caveman - saves tokens
 https://github.com/JuliusBrussee/caveman/tree/main

## Hooks 
<https://docs.claude.com/en/docs/claude-code/hooks>
<https://code.claude.com/docs/ru/hooks>
<https://habr.com/ru/companies/rostelecom/articles/1028570/>
```
хуки — это механизм, который позволяет вклиниться в жизненный цикл агента своим кодом.
Ваш shell-скрипт (или HTTP-эндпоинт, или вспомогательный sub-agent) исполняется в строго заданные моменты:
старт сессии, отправка prompt, до tool call, после tool call, запуск sub-agent, остановка,
перед компактификацией контекста, завершение сессии.
В одних точках вы можете только наблюдать;
в других — заблокировать действие агента до того, как оно произойдёт.
```

В Claude Code хуки описываются под ключом hooks в .claude/settings.json (project-level, едет в git)  
или ~/.claude/settings.json (global).
Минимальный конфиг:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-prompt.sh"
          }
        ]
      }
    ]
  }
}
```

<https://magazine.sebastianraschka.com/p/components-of-a-coding-agent>

<https://www.youtube.com/watch?v=ESBMgZHzfG0> AI Periodic table

<https://buildyourowncodingagent.com/>

<https://docs.fabro.sh/getting-started/why-fabro>

<https://ecc.tools/>

<https://vikulin.ai/library/tpost/ai_agent_architecture>

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

## Agents orcestration via md files
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

<https://github.com/cameronsjo/spec-compare>

<https://news.ycombinator.com/item?id=48398925>

<https://habr.com/ru/companies/yadro/articles/1038084/>

<https://habr.com/ru/companies/yadro/articles/1007480/>

<https://habr.com/ru/articles/1022050/>

<https://habr.com/ru/companies/yadro/articles/1029288/>

<https://openspec.dev/>

<https://habr.com/ru/articles/1007048/>

<https://habr.com/ru/articles/985990/>

<https://github.com/sermakarevich/sddw>

<https://news.ycombinator.com/item?id=48231575>

<https://docs.google.com/presentation/d/1SjKXF7hkoqyiN9-3tBGY4PDGvS3iqVyovDlJC_hYvMA/edit?usp=sharing>

## MCP vs Skills

<https://habr.com/ru/articles/1031670/>

<https://david.coffee/i-still-prefer-mcp-over-skills/>

This isn't a zero-sum game or a choice of one over the other. They solve different layers of the developer experience: MCP provides a standardized, portable interface for external data/tools (the infrastructure), while Skills offer project-specific, high-level behavioral context (the orchestration). A robust workflow uses MCP to ensure tool reliability and Skills to define when and how to deploy those tools.


<https://news.ycombinator.com/item?id=47712718>

### MCP

<https://habr.com/ru/articles/1005028/>

<https://habr.com/ru/articles/1006756/>

<https://habr.com/ru/articles/1006756/>

## Skills

<https://habr.com/ru/articles/1020786/>

<https://habr.com/ru/companies/haulmont/articles/1027460/>
 
Это папка с файлом SKILL.md (YAML-метаданные + инструкции для агента) и опциональными скриптами/файлами/всё что может пригодиться:

```
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
```

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




### Tool calling  (sometimes referred to as function calling) 

Tool calling refers to the ability of artificial intelligence (AI) models to interact with external tools, application programming interfaces (APIs) or systems to enhance their functions.

Instead of relying solely on pretrained knowledge, an AI system with tool-calling capabilities can query databases, fetch real-time information, execute functions or perform complex operations beyond its native capabilities.

<https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling>


 #### grep-ast - can be used as tool calling
 умеет находить в коде структурные сущности - классы, методы, точки входа, значит это не просто CLI-утилита для разработчика. Это готовая операция навигации по коду, которую можно дать агенту как инструмент.

 <https://habr.com/ru/companies/ecom_tech/articles/1005610/>

### Sub-agents

<https://habr.com/ru/articles/1006602/>
 

## Pi

<https://pi.dev/>

<https://lucumr.pocoo.org/2026/1/31/pi/>  
<https://shivamagarwal7.medium.com/agentic-ai-pi-anatomy-of-a-minimal-coding-agent-powering-openclaw-5ecd4dd6b440>

<https://github.com/badlogic/pi-mono>

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
 
openclaw cron add --name "Утро" --cron "0 9 * * *" \
  --message "Погода, календарь, важные письма, результат Лиги Чемпионов"

```



## ChatGPT
<https://habr.com/ru/articles/981624/> How to use ChatGPT effectively  

## Codex from OpenAI
<https://habr.com/ru/articles/1037064/>  
<https://habr.com/ru/articles/1036396/>   
<https://habr.com/ru/companies/ods/articles/1001012/>  

<https://ai.sulat.com/the-definitive-guide-to-codex-cli-from-first-install-to-production-workflows-a9f1e7c887ab> Codex CLI
<https://habr.com/ru/articles/1040296/> Codex CLI article above translated

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
