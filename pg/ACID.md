## ACID

<https://en.wikipedia.org/wiki/ACID>

https://habr.com/ru/companies/otus/articles/968212/

<https://habr.com/ru/articles/961134/>

ACID  properties:

### Atomicity: 
either all parts of the transaction are committed or all parts are aborted. Martin Kleppmann suggests calling this property “Abortability” because it reflects the meaning more accurately and avoids confusion between atomic commit/abort and atomic visibility.

### Consistency: 
historically added for a better-sounding acronym and rather application-specific than DBMS-specific.

### Isolation: 
concurrently executed transactions are isolated from each other. The results of transaction execution should look like the transactions have been executed serially, one by one.

### Durability: 
committed data is never lost.


## Serializable isolation level
<https://blog.ydb.tech/do-we-fear-the-serializable-isolation-level-more-than-we-fear-subtle-bugs-5a025401b609>

## Теория: уровни изоляции Postgres

<https://habr.com/ru/articles/1044190/>

Уровень изоляции транзакций на изменение значений в БД — это регулятор строгости той самой «I» из ACID. SERIALIZABLE — изоляция в полном смысле: результат эквивалентен последовательному выполнению. Более низкие уровни (REPEATABLE READ, READ COMMITTED) — ослабленная изоляция: часть аномалий разрешена ради скорости. То есть «I» — не бинарная гарантия «есть / нет», а шкала, и выбор уровня — это компромисс между строгостью и производительностью. Остальные три буквы — A, C, D — уровни изоляции не трогают.

Что каждый уровень гарантирует и как ведёт себя при конкурентной записи в одну и ту же строку:

READ COMMITTED (дефолт). База не мешает гонке. Каждый SELECT видит свежий снимок на момент самого запроса; две транзакции спокойно читают одно и то же значение, считают новое и записывают — второе затирает первое. Lost update проходит молча, и чинить его приходится самостоятельно.

REPEATABLE READ. Снимок фиксируется на старт транзакции. Если транзакция меняет строку, которую после этого снимка успел изменить и закоммитить кто-то другой, Postgres не ждёт и не сливает изменения, а отклоняет транзакцию ошибкой 40001 (could not serialize access).

SERIALIZABLE. То же, но строже: Postgres отслеживает зависимости между транзакциями и отклоняет (40001) даже там, где строки разные, но итог не соответствовал бы последовательному выполнению (так ловится write skew). Отказов, естественно, больше.

Главная мысль: повышение уровня изоляции не «чинит» гонку волшебно. Postgres делает ровно ту работу, что входит в его зону ответственности — честно замечает конфликт и сообщает о нём ошибкой 40001. А вот повторять отклонённую транзакцию он за нас не станет: это уже забота приложения. Не предусмотрел повтор — и запрошенная пользователем операция просто не будет осуществлена (транзакция откатывается целиком, данные при этом не теряются — операции просто не происходит).
