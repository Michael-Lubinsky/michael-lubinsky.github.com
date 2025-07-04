https://modelcontextprotocol.io/

https://github.com/punkpeye/awesome-mcp-clients

https://mcp.so/

https://habr.com/ru/articles/890740/

https://habr.com/ru/articles/862312/

https://habr.com/ru/articles/910524/

https://habr.com/ru/articles/899088/

https://habr.com/ru/articles/893822/

### MCP Host: 
Это приложение, где живет LLM (например, Claude Desktop или Cursor IDE). Хост хочет получить доступ к внешним возможностям/данным

### MCP Client: 
Компонент внутри хоста. Для каждого внешнего сервиса создается клиент, который устанавливает соединение с соответствующим сервером и общается с ним по протоколу MCP

### MCP Server: 
Внешняя программа или сервис, который предоставляет хосту определенные данные или функции по протоколу MCP. Сервер может быть локальным (доступ к файлам на компьютере) или удаленным (обертка над API или, например, БД). Каждый сервер определяет и объявляет, какими ресурсами, инструментами и подсказками он может поделиться с моделью

Общение между клиентом и сервером происходит через стандартные HTTP + JSON-RPC для запросов и Server-Sent Events (SSE) для асинхронщины и стриминга.
MCP определяет четыре основных типа возможностей, которые могут предоставлять серверы:

### 1. Инструменты: активные действия
Инструменты(tools) — это функции, которые модель может вызывать для выполнения конкретных действий: поиск в интернете, отправка email, выполнение вычислений, генерация изображений и т.д.

Ключевая особенность инструментов — они инициируются моделью на основе понимания потребностей пользователя. Например, когда пользователь спрашивает о погоде, модель сама решает, что нужно вызвать инструмент получения метеоданных.

### 2. Ресурсы: источники знаний
Ресурсы(resources) — это пассивные источники данных, к которым модель может обращаться для получения контекста: документы, базы данных, файлы пользователя и т.д.

В отличие от инструментов, ресурсы обычно не выполняют сложных вычислений и используются для расширения контекстуальных знаний модели.

### 3. Промпты: шаблоны взаимодействия
Промпты(prompts) — это предопределенные шаблоны взаимодействия с моделью, которые задают структуру диалога и направляют модель в решении конкретных задач.

Промпты можно сравнить с рабочими инструкциями, которые помогают модели более эффективно решать специализированные задачи: составление резюме, анализ кода, генерация идей и т.д.

### 4. Сэмплинг: рекурсивный интеллект
Сэмплинг(sampling) — это уникальная возможность, позволяющая серверу запрашивать у модели дополнительные размышления или анализ. Это создает своего рода "рекурсивное мышление", где ИИ может анализировать свои собственные выводы.

Сэмплинг открывает двери к созданию по-настоящему автономных ИИ-агентов, способных к многошаговому планированию и самокоррекции.

Протокол четко определяет взаимодействие между компонентами. Вот основные элементы:

### 1 Messages: 
Основа основ в нашем протоколе – диалог.

MCP структурирует его как последовательность сообщений с четкими ролями: user (это мы), assistant (наш ИИ), system (всевозможные системные инструкции) и tool (результат работы внешних сервисов, которые MCP Server). Каждое сообщение содержит текст и опциональные метаданные (время, язык, приоритет и тд). Системные сообщения задают тон и правила игры для модели ("Отвечай, как будто ты – вежливый помощник...", "Отвечай только на основе данных из предоставленных документов...").

Это помогает управлять поведением модели и защищаться от атак вроде prompt-injection (но надо понимать, что почти всегда можно все обойти, когда речь идет про ИИ - так что на сто процентов нельзя быть уверенным, что модель будет следовать этой инструкции).

Модель также может добавлять свои "мысли вслух" или план действий в метаданные ассистентских сообщений (chain of thoughts - цепочка рассуждений)

#### 2 Tools: 
Ну, собственно, это и есть наши внешние сервисы и функции, которые модель может вызывать.

Каждый инструмент описывается сервером: имя, понятное описание (чтобы модель знала, когда его использовать) и схема параметров. То есть, я могу создать инструмент с названием "база экономических данных Японии за 2000-2025 годы" и описать ее так: "Обращайся к этому инструменту, если тебе нужны какие-либо данные про экономику Японии за последние 25 лет". И мне нужно описать, что данный инструмент умеет отвечать на запросы с такими-то параметрами. Модель, получив список доступных инструментов, сама определяет, какой из них применить для ответа на запрос пользователя. Вызов происходит так: модель генерирует ответ типа "Я хочу вызвать инструмент X с параметрами Y". MCP-клиент перехватывает такой запрос, передает его нужному MCP-серверу, тот выполняет нужное действие и возвращает результат. Результат (например, данные из API или из БД) вставляется обратно в диалог как сообщение от роли tool. После этого модель продолжает диалог, уже зная результат.

MCP стандартизирует весь цикл: объявление, вызов, обработка ошибок, получение результата. Это позволяет строить сложные цепочки действий: модель может последовательно вызывать несколько инструментов, а протокол гарантирует корректную передачу данных между шагами. За счет того, что модель вызывает инструменты по своему усмотрению, а не по жесткому скрипту, система получается гибкой и "умной"

#### 3 Memory: 
Мы же хотим, чтобы ассистент помнил важные вещи между сессиями? MCP предлагает решение через так называемые серверы памяти.

Это могут быть сервисы, хранящие заметки, факты или векторные представления данных для семантического поиска по ним. На гитхабе уже есть примеры таких серверов от Anthropic и не только (всякие Memory Bank, Memory Box и тд). Модель знает, что может использовать инструменты этих серверов, чтобы запомнить что-то важное (вызвав метод save_memory) или "вспомнить" (вызвав метод search_memory). Так LLM обретает долговременную память: разные пользовательские предпочтения, какие-то детали прошлых проектов, важные факты - не теряются. Сами данные хранятся на стороне сервера, что важно для конфиденциальности.

MCP помогает управлять и краткосрочной памятью: если диалог становится слишком длинным, Context Manager может сжимать или суммировать историю, сохраняя самое важное в пределах контекстного окна модели

#### Files & Resources: 
Помимо активных инструментов, модели часто нужен доступ к данным – файлам, записям в базах данных, результатам API-запросов, логам. В контексте MCP это называется ресурсы. Сервер объявляет доступные ресурсы, используя URI-схемы (например, file:///path/doc.txt или database://customers/123. Я выше для облегчения понимания писал про то, что БД может быть инструментом - это так, если поверх нее есть какое-то API. Но может быть и ресурсом в зависимости от удобства применения). Модель может запросить содержимое ресурса, как бы делая GET-запрос. В отличие от инструментов, ресурсы обычно предназначены только для чтения (у инструментов можно вызывать любые описанные функции, и они могут изменять состояние инструмента как угодно). Файловая система – типичный пример ресурса. Anthropic выпустила готовый Filesystem MCP-сервер, позволяющий Claude безопасно работать с файлами на компьютере пользователя

Prompts: Кроме базовой системной инструкции, в MCP есть понятие Prompts – это предопределенные шаблоны взаимодействия для каких-то стандартных задач. Эти шаблоны могут комбинироваться, создавая сложные рабочие процессы (workflows). Например, шаблон "анализа лога" может включать шаги поиска по логу (в инструменте, например в elasticsearch), суммирование найденного (уже сама модель), выдача заключения по шаблону. MCP позволяет явно объявлять такие последовательности



https://habr.com/ru/articles/893482/

https://habr.com/ru/articles/920972/

https://habr.com/ru/articles/916722/

https://habr.com/ru/articles/903942/
