### Agents

https://habr.com/ru/articles/981624/  How to use ChatGPT effectively   
https://habr.com/ru/articles/983214/  Claude Code   
https://habr.com/ru/articles/984160/ Claude Code  Agent  
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
   
### Agent Skills:
<https://skillsmp.com/>
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
