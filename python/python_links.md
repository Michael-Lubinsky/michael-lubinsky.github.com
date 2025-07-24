https://pydevtools.com/handbook/

https://habr.com/ru/companies/raiffeisenbank/articles/885792/ архитектурный подход к Python приложениям

https://pattern-kit.readthedocs.io/en/latest/ implementations of common software design patterns

https://habr.com/ru/articles/930094/

https://adamgrant.micro.blog/2025/07/24/123050.html


https://news.ycombinator.com/item?id=44675119


### Working with large files: 
https://blog.devgenius.io/10-ways-to-work-with-large-files-in-python-effortlessly-handle-gigabytes-of-data-aeef19bc0429

### asyncio
https://github.com/anordin95/a-conceptual-overview-of-asyncio/blob/main/readme.md

https://afabundle.pro/product/competitive-programming-in-python/ Competitive Programming Book

https://habr.com/ru/companies/dockhost/articles/891544/

https://blog.stackademic.com/12-python-scripts-that-saved-me-10-hours-every-week-6459a06f6c03 12 Python Script

https://uproger.com/optimizciyaiuskoreniecodanapython/ Python performance


### Python Type checker

https://pyrefly.org/

https://marketplace.visualstudio.com/items?itemName=astral-sh.ty   ty Visual Studio Code extension

https://yasirbhutta.github.io/python/docs/oop-inheritance/practice-and-progress/find-fix-mistakes-oop-inheritance.html 

https://www.reddit.com/r/Python/comments/1ku6th8/which_useful_python_libraries_did_you_learn_on/

https://www.reddit.com/r/Python/comments/1l43i8z/what_are_your_favorite_modern_libraries_or/

https://github.com/EntilZha/PyFunctional

https://github.com/mahmoud/boltons  Boltons useful lib

https://github.com/jlevy/strif  string, file, and object utilities

https://github.com/Erotemic/ubelt  Ubelt

https://realpython.com/python-loguru/  Loguru , also look into structlog

https://github.com/surister/queryzen SQL over HTTP

https://connect.posit.cloud/ A cloud environment to easily showcase your Python and R content.


https://github.com/savioxavier/dbglib  DEBUG util

https://blog.edward-li.com/tech/advanced-python-features
 
### Code snippets

https://medium.datadriveninvestor.com/mastering-advanced-python-40-pro-level-snippets-for-2024-85f5b9359103

https://python.plainenglish.io/mastering-python-100-advanced-python-cheatsheets-for-developers-a5da6f176667

### Decorators  
https://habr.com/ru/articles/910424/

https://towardsdatascience.com/pythons-most-powerful-decorator-6bc39e6a8dd8

### Links

<https://pypi.org/project/sqlxport/> read from Postgres and Redshift and save as parquet (optionally on S3)

<https://habr.com/ru/articles/914650/> Descriptors in Python



<https://medium.com/@CodeWithHannan/10-python-workflows-for-high-volume-etl-pipelines-54d57728b773>

<https://medium.com/@abdullah.iu.cse/mastering-python-with-these-code-snippets-part-4-de4441e29260>

<https://pythonhelper.com/python/python-dictionary-methods/>

<https://realpython.com/instance-class-and-static-methods-demystified/>

<https://realpython.com/python-subprocess>

<https://adamj.eu/tech/2024/12/30/python-spy-changes-sys-monitoring/>

<https://pybit.es/articles/generator-mechanics-expressions-and-efficiency/>

https://www.youtube.com/@PyConUS

https://data-hacks.com/python-programming-language

https://riverml.xyz/latest/ Online machine learning in Python

https://habr.com/ru/companies/otus/articles/888974/ Type Annotations 

### Parsing

  https://eshsoft.com/blog/5-lark-features-you-didnt-know  Lark parser

 https://habr.com/ru/articles/905582/

 https://habr.com/ru/articles/901324/

 https://habr.com/ru/articles/883390/

### Pipelines

https://medium.com/@connect.hashblock/i-built-a-fastapi-system-that-handled-1-billion-events-per-day-heres-the-architecture-c73fb7dd7eb1

https://medium.com/@kazarmax/from-api-to-dashboard-building-an-end-to-end-etl-pipeline-with-azure-9b498daa2ef6

https://pybit.es/articles/a-practical-example-of-the-pipeline-pattern-in-python/

https://python.plainenglish.io/how-i-built-a-python-automation-system-that-runs-my-entire-workflow-while-i-sleep-07c98494f0f6

<https://medium.com/python-in-plain-english/i-built-a-python-devops-toolkit-that-deploys-monitors-and-recovers-itself-5061f484ff39>

<https://python.plainenglish.io/mastering-the-hidden-layers-of-python-building-a-modular-file-processing-system-from-scratch-4871e5541553>

<https://medium.com/data-science-collective/how-i-rebuilt-my-entire-coding-workflow-with-python-scripts-7ac3d3b6d2d9>


https://hamilton.dagworks.io/en/latest/

https://pipefunc.readthedocs.io/en/latest/

https://www.youtube.com/watch?v=tyWpb8E4fqo  10 python libs

https://habr.com/ru/articles/562380/ Statistics


How python manage memory: https://habr.com/ru/companies/ibs/articles/905376/

### Discrete event simulation SimPy, Salabim
<https://en.wikipedia.org/wiki/Discrete-event_simulation>
<https://simpy.readthedocs.io/en/latest/>
<https://simulation.teachem.digital/free-simulation-in-python-with-simpy-guide>
<https://github.com/salabim/salabim>


Equinox: neural networks for JAX (2.4k stars, 1.1k used-by)

jaxtyping: type annotations for shape and dtypes (1.4k stars, 4k used-by)   
Also despite the now-historical name this supports pytorch+numpy+tensorflow+mlx so it's seen traction in all kinds of array-based computing.



https://github.com/patrick-kidger


msgspec as a faster version of pydantic

rich for pretty terminal output

https://deptry.com/
deptry for finding issues with project dependencies


## Scheduling
```python
import sched
import time

scheduler = sched.scheduler(time.time, time.sleep)

def job():
    print("Running task at", time.ctime())

    # Reschedule the job to run again in 2 hours (7200 seconds)
    scheduler.enter(7200, 1, job)

# Schedule the first run in 0 seconds (immediate start)
scheduler.enter(0, 1, job)

print("Scheduler started at", time.ctime())
scheduler.run()
```

| Feature                         | `sched` (Standard Library)             | `APScheduler` (Third-Party)                                  |
| ------------------------------- | -------------------------------------- | ------------------------------------------------------------ |
| 📦 Included in Standard Library | ✅ Yes                                  | ❌ No (install via `pip install apscheduler`)                 |
| 🧠 Complexity                   | Simple                                 | More powerful and configurable                               |
| ⏱ Task Types                    | Only one-shot (delayed) tasks          | Interval, cron, date-based, and more                         |
| 🔁 Repeating Tasks              | ❌ No built-in support                  | ✅ Yes (interval or cron-style)                               |
| 🧵 Thread Safety                | No (single-threaded use)               | Yes (with options for threading, asyncio, etc.)              |
| ⚙ Backends                      | Manual loop (`scheduler.run()`)        | Multiple backends: in-memory, database, etc.                 |
| 🧪 Persistent Jobs              | ❌ No                                   | ✅ Yes (with DB/job store)                                    |
| 🧰 Built-in Job Management      | ❌ No                                   | ✅ Yes (pause, resume, remove, view jobs)                     |
| 🕒 Time Sources                 | You provide `timefunc` and `delayfunc` | Built-in support for multiple time zones, `datetime` objects |
| 🐍 Python Versions              | Python 3+                              | Python 3.6+ (actively maintained)                            |





### Web GUI with Python
https://medium.com/@manikolbe/streamlit-gradio-nicegui-and-mesop-building-data-apps-without-web-devs-4474106778f5
