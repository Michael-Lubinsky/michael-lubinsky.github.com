https://habr.com/ru/articles/981624/  How to use ChatGPT effectively 

https://github.com/Mathews-Tom/Agentic-Design-Patterns

https://learn.microsoft.com/en-us/shows/ai-agents-for-beginners/

https://habr.com/ru/companies/otus/articles/978426/

https://habr.com/ru/articles/981650/

https://habr.com/ru/articles/981100/

https://pub.towardsai.net/building-production-grade-ai-agents-in-2025-the-complete-technical-guide-9f02eff84ea2

Agent Skills:

Agent Skills (навыки агентов) - это новый архитектурный паттерн для LLM-агентов, позволяющий имитировать наличие у модели набора узкоспециализированных компетенций. Технически Skill - это директория, содержащая манифест с инструкциями (SKILL.md) и связанные ресурсы (скрипты, шаблоны, справочники). Идея была впервые формализована компанией Anthropic осенью 2025 года, а к концу 2025-го стала открытым стандартом, поддерживаемым индустрией. Проще говоря, skill - это «упакованный» кусочек экспертного опыта или пошаговой процедуры, который агент может динамически загрузить и применить, когда этот навык ему пригодится.
https://habr.com/ru/companies/bitrix/articles/980654/

Структура skill к концу 2025 года уже стала де-факто стандартом (поддерживается сообществом ). Вот как выглядит типичный навык в файловой системе:
```
my-cool-skill/
├── SKILL.md          # Манифест и инструкции
├── scripts/          # Исполняемый код (напр. Python или Bash)
├── references/       # Справочные материалы (например, перечень кодов ошибок)
└── assets/           # Шаблоны документов, письма и пр.
```

```
Главный файл - SKILL.md. Это гибрид YAML и Markdown: он начинается с YAML-заголовка, где указываются метаданные навыка, а далее следует собственно инструкция в MD-разметке. Пример (упрощенный фрагмент для иллюстрации):
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
