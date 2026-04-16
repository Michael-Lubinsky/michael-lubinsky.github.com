## Claude
<https://code.claude.com/docs>  

<https://anthropic.skilljar.com/>

<https://blog.dailydoseofds.com/p/anatomy-of-the-claude-folder>

<https://github.com/luongnv89/claude-howto> 

<https://habr.com/ru/articles/1021810/> Claude links

<https://habr.com/ru/articles/1021696/> Claude folders

<https://medium.com/data-science-collective/how-to-build-claude-skills-2-0-better-than-99-of-people-af4927dd5335>

<https://github.com/shanraisshan/claude-code-best-practice>

<https://github.com/davila7/claude-code-templates>

<https://ccunpacked.dev/>

### CLI
<https://cc.storyfox.cz/> CLI commands  
<https://code.claude.com/docs/en/cli-reference>   
<https://habr.com/ru/companies/cloud4y/articles/1014386/> CLI commands

## Skills
<https://www.claudeskills.org/>  
<https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf>  
<https://anthropic.skilljar.com/claude-code-in-action>  

<https://www.youtube.com/watch?v=dn3CuC-2NiI>

<https://habr.com/ru/articles/983214/>

## Agent
https://habr.com/ru/articles/984160/ Claude Code  Agent  

<https://habr.com/ru/articles/1015252/> Claude Code  Agent 

### Superpowers

Ты говоришь Claude: «Добавь авторизацию через JWT». Без Superpowers он сразу начнёт писать код. С Superpowers — вызывает скилл brainstorming, задаёт уточняющие вопросы, предлагает 2-3 подхода, рисует дизайн. И только после твоего одобрения переходит к writing-plans — декомпозирует работу на задачи по 2-5 минут каждая.
<https://github.com/obra/superpowers>

<https://blog.fsck.com/2025/10/09/superpowers/>

https://www.dev-log.me/pr_review_navigator_for_claude/  Skill for code review

https://psantanna.com/claude-code-my-workflow/workflow-guide.html
<https://habr.com/ru/articles/1012412/>

<https://boristane.com/blog/how-i-use-claude-code/>

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
<https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf>

Structured outputs <https://platform.claude.com/docs/en/agent-sdk/structured-outputs>

<https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling>

<https://github.com/affaan-m/everything-claude-code>

![Claude Code WorkFlow Cheatsheet](https://github.com/user-attachments/assets/c86f34e8-31d1-467e-b3f7-5f9c832e1429)

<img width="1228" height="1536" alt="image" src="https://github.com/user-attachments/assets/4ab21e44-594b-4c9f-b13b-5dcbe8da4f6a" />

![desilula for butting state Code](https://github.com/user-attachments/assets/f48fe08f-3464-48c2-881b-3ec864587c67)

<img width="1166" height="1176" alt="image" src="https://github.com/user-attachments/assets/33ca876d-8246-4a60-8efb-2691b12d0184" />

<img width="483" height="428" alt="image" src="https://github.com/user-attachments/assets/66c1407f-b0e6-4ef6-a4cd-7173bdd0ae6e" />

<img width="764" height="1024" alt="image" src="https://github.com/user-attachments/assets/711c8732-befb-4b71-a65c-ef8774825feb" />


→ Всегда используй режим plan, давай Claude способ проверить результат
→ Попроси Claude провести с тобой интервью через инструмент AskUserQuestion
→ Используй Git Worktrees для параллельной разработки
→ /loop — планируй повторяющиеся задачи до 3 дней
→ Code Review — новые контекстные окна находят баги, которые пропустил исходный агент
→ /btw — побочные цепочки диалога, пока Claude работает
→ Делай поэтапные планы с «гейтами» и тестами для каждого этапа
→ Используй cross-model (Claude Code + Codex) для ревью плана
→ CLAUDE.md должен быть меньше 200 строк на файл
→ Используй команды для workflow вместо саб-агентов
→ Делай узкоспециализированных саб-агентов с конкретными навыками, а не универсальных QA или backend-инженеров
→ Обычный Claude Code лучше сложных workflow для небольших задач
→ Делай скриншоты и отправляй Claude, если застрял
→ Используй MCP, чтобы Claude видел логи консоли Chrome
→ Попроси Claude запускать терминал как фоновую задачу для лучшей отладки
→ Используй cross-model для QA — например, Codex для проверки плана и реализации
Включённые community workflow:
→ Cross-Model (Claude Code + Codex) Workflow
→ RPI (Research Plan Implement)
→ Ralph Wiggum Loop для автономных задач
→ Github Speckit (74K звёзд)
→ obra/superpowers (72K звезды)
→ OpenSpec OPSX (28K звёзд)
Ключевые вопросы на миллиард долларов:
→ Что должно быть внутри CLAUDE.md?
→ Когда использовать command vs agent vs skill?
→ Почему Claude игнорирует инструкции из CLAUDE.md?
→ Можно ли превратить кодовую базу в спецификации и пересоздать код только из них?
Ежедневные привычки:
→ Обновляй Claude Code каждый день
→ Начинай день с чтения changelog
→ Следи за r/ClaudeAI и r/ClaudeCode на Reddit

<https://github.com/shanraisshan/claude-code-best-practice>
