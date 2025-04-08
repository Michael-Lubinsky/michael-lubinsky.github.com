https://grep.app/ search on github

AWS S3 explained: https://medium.com/@joudwawad/aws-s3-deep-dive-1c19ad58af40
S3:  
https://habr.com/ru/companies/runity/articles/898710/

<https://www.reddit.com/r/MachineLearning+Python+apachespark+code+csbooks+datamining+flask+hadoop+javascript+learnmachinelearning+programming/>


https://www.youtube.com/watch?v=OLXkGB7krGo   ETL dbt snowflake, etc

### Architecture

https://www.cosmicpython.com/book/preface.html

https://polylith.gitbook.io/polylith



### сегментацию и кластеризацию клиентской базы
https://medium.com/data-science/building-effective-metrics-to-describe-users-3212727c5a9e
https://habr.com/ru/articles/423597/
https://habr.com/ru/articles/668186/ ищем тренд и прогнозируем спрос с помощью временных рядов, SARIMA 
https://www.youtube.com/watch?v=vGcjIz38Mbs cohort retension python

### Customer Live Time Value
https://medium.com/airbnb-engineering/how-airbnb-measures-listing-lifetime-value-a603bf05142c
https://habr.com/ru/companies/appodeal/articles/294864/  
https://habr.com/ru/articles/436236/  
https://medium.com/bolt-labs/understanding-the-customer-lifetime-value-with-data-science-c14dcafa0364  
https://habr.com/ru/companies/beeline_tech/articles/755232/  
https://habr.com/ru/companies/beeline_tech/articles/792618/ 
https://habr.com/ru/companies/beeline_tech/articles/771246/  
https://habr.com/ru/companies/alfa/articles/789894/  
https://habr.com/ru/companies/alfa/articles/808711/
https://habr.com/ru/companies/beeline_tech/articles/802005/
 
### RFM 
https://habr.com/ru/companies/otus/articles/894850/  
https://habr.com/ru/companies/otus/articles/893964/  
https://habr.com/ru/companies/otus/articles/666862/  
https://habr.com/ru/articles/780330/  
https://habr.com/ru/articles/658225/  
https://habr.com/ru/articles/863374/  
https://habr.com/ru/companies/mindbox/articles/423463/  
https://habr.com/ru/companies/gazprombank/articles/805101/  
https://habr.com/ru/companies/otus/articles/812225/  
https://habr.com/ru/companies/devtodev/articles/295560/  
https://habr.com/ru/articles/543950/  
https://habr.com/ru/articles/497356/  
https://habr.com/ru/companies/plarium/articles/431520/  

- Recency — когда последний раз был активен пользователь
- Frequency — как часто он делает покупки/действия
- Monetary — сколько он потратил денег (или сделал заказов, если у тебя freemium)

- Кто покупает часто
- Кто покупает дорого
- Кто давно не заходил, но когда‑то приносил тебе деньги

### Customer metrics analysis
https://habr.com/ru/companies/otus/articles/893964/

https://habr.com/ru/companies/otus/articles/893988/
https://habr.com/ru/companies/appodeal/articles/294864/
Life Time Value (LTV)

ARPU ARPU (Average Revenue Per User)
Average Revenue Per Daily Active User (ARPDAU)

### https://habr.com/ru/articles/886100/ Retention

AARRR: Acquisition → Activation → Retention → Revenue → Referral

### Cohort Retention Rate (Коэффициент удержания по когортам) 

https://habr.com/ru/companies/productstar/articles/509410/

https://habr.com/ru/articles/892980/

https://habr.com/ru/articles/343544/

https://habr.com/ru/articles/415727/

https://habr.com/ru/articles/342108/

https://habr.com/ru/articles/542626/ with Python 

https://habr.com/ru/articles/501492/ with Python 

https://habr.com/ru/companies/click/articles/464511/ with SQL+ Grafana

https://habr.com/ru/companies/dcmiran/articles/500360/ SQL

https://habr.com/ru/companies/io/articles/262025/

https://onthe.io/learn+%D0%A7%D1%82%D0%BE+%D1%82%D0%B0%D0%BA%D0%BE%D0%B5+%D0%BA%D0%BE%D0%B3%D0%BE%D1%80%D1%82%D0%BD%D1%8B%D0%B9+%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7

```
– базовая метрика, показывающая,
какая доля пользователей остается активной спустя определённый период после привлечения. Рассчитывается по формуле:
Retention Rate = (Число пользователей, оставшихся активными к концу периода) / (Число пользователей в начале периода) × 100%

Например, если из 100 пользователей, зарегистрировавшихся в январе, 40 продолжали пользоваться продуктом в феврале,
коэффициент удержания за 1 месяц = 40%. Когортный анализ строит кривую удержания –
как процент активных пользователей снижается со временем.
Здоровый продукт обычно демонстрирует сперва падение кривой (первые отсевающие пользователи),
но затем плато удержания: оставшаяся доля лояльных пользователей, которая продолжительно пользуется продуктом.
Сравнивая ретеншен разных когорт или после экспериментальных изменений, можно выявлять улучшения или проблемы с удержанием.
 Например, резкий спад на 1-й день или неделе указывает на неэффективную активацию или первые впечатления.
```
### Churn Rate (Уровень оттока) – обратная метрика к удержанию, 
показывающая процент пользователей, покинувших продукт за период. Churn = 1 - Retention

обычно в процентах). Например, если из 100 клиентов за месяц отписались или перестали заходить 5, ежемесячный отток = 5%. 
Контролируя churn, компании следят, чтобы он не превышал темп прироста пользователей.
Высокий churn – сигнал проблемы: либо продукт не даёт долговременной ценности, либо есть неудовлетворенность.
В сочетании с коэффициентом удержания churn помогает оценить, какая часть пользовательской базы “доживает” до каждого следующего периода.

### Average User Lifetime (Средний жизненный цикл пользователя) 
```
– среднее время, которое пользователь остается активным до ухода. В сегменте подписок этому эквивалентен срок удержания клиента. 
Если retention rate известен, можно приблизительно рассчитать среднюю продолжительность жизни клиента 
(например, при месячном оттоке 5% средний клиент остается ~20 месяцев). Данная метрика важна для оценки пожизненной ценности клиента.


Но дьявол в деталях: что считать “активным” и за какой период для расчета этих метрик?

Шаг 1 – определить “единицу ценности” вашего продукта. Что именно пользователь делает или получает, ради чего он будет возвращаться? Это ключевое действие или событие.
Для соцсети – просмотр ленты или общение, для райдшеринга – совершённая поездка, для маркетплейса – заказ,
для SaaS – успешное использование функционала (например, отправленный командой проект в Trello).
Именно это событие и должно лежать в основе метрики удержания.
“Метрика удержания, привязанная к фактическому использованию продукта, гораздо лучше предсказывает отток”.

То есть смотрим не просто “залогинился ли пользователь”, а получил ли он ценность снова.
Например, в Uber – совершил ли пользователь поездку в этом месяце. В Netflix– посмотрел ли хотя бы одно видео за N дней.
В Slack – отправил X сообщений за неделю.

Шаг 2 – определить окно времени. Разные продукты имеют разный “ритм” использования – кто-то ежедневно, кто-то ежемесячно,
кто-то от случая к случаю. Нужно выбрать период, по истечении которого отсутствие активности можно считать уходом.
Для Facebook это дни или недели, для SaaS с помесячной подпиской – обычно месяц,
для сезонных или низкочастотных сервисов – квартал или даже год.
Хорошая практика – смотреть когортный retention: взять всех новых пользователей, пришедших в месяц X, и отслеживать,
 какой процент из них активны через 1 месяц, 2 месяца, 3, и т.д.

Когортный анализ – разбиение пользователей на когорты (обычно по месяцу/неделе регистрации или первой покупки) и отслеживание их удержания во времени.
Это позволяет выявлять тренды (улучшается ли удержание новых когорт vs старых при внесении улучшений) и особенности поведения разных групп.
Когортные таблицы и графики визуализируют % оставшихся активных по периодам (Month 0, 1, 2... или Day 1, 7, 30...).
```
https://habr.com/ru/articles/342108/
