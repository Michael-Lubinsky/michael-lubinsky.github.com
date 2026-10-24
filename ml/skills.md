## Skills
```
в контекст сначала попадают только название и описание SKILL-а, можно безболезненно добавить 30 своих SKILL-ов без особых последствий.
Когда потребуется использовать SKILL, LLM-агент сам подтянет его описание, если поймет из контекста задачи,
что это нужно, или пользователь сам скажет ему использовать такой SKILL для работы.

SKILL представляет собой не просто инструкцию, а целый набор инструментов.
Помимо SKILL.md, в него можно положить готовые скрипты, документацию, шаблоны и другие файлы. И самое интересное: все эти файлы не загружаются в контекст автоматически.
Агент читает их только по необходимости, а готовые скрипты может просто запускать, не тратя токены на генерацию кода.
Таким образом, SKILL позволяет объединить инструкции, документацию и исполняемый код в один пакет, не раздувая контекст LLM.
Например, структура может выглядеть так:


my-skill/
├── SKILL.md
├── scripts/
│   ├── generate.py
│   └── validate.py
├── references/
│   └── api.md
└── assets/
    └── template.html
```
<https://www.skills.sh>

<https://habr.com/ru/articles/1078034/>  

<https://github.com/davidondrej/skills>

<https://github.com/sshwarts/skillscript>



<https://arxiv.org/abs/2608.12610>

<https://habr.com/ru/articles/1062626/>

<https://github.com/mattpocock/skills>

<https://habr.com/ru/articles/1065860/>

<https://www.youtube.com/watch?v=M6mYodf0dJM>

<https://www.aihero.dev/5-agent-skills-i-use-every-day>

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
 

Из интересного это поле requires.bins in line above - это своего рода гейтинг: 
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
skill - это «упакованный» кусочек экспертного опыта или пошаговой процедуры,
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
Главный файл - SKILL.md.
 Это гибрид YAML и Markdown: он начинается с YAML-заголовка,
где указываются метаданные навыка, а далее следует собственно инструкция в MD-разметке.
Пример (упрощенный фрагмент для иллюстрации):
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


