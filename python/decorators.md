## Decorators

### @dataclass decorator

 can automatically generate several special methods for a class, such as
 __init__, __repr__, __eq__, __lt__, and so on.


 ###  @contextmanager decorator
 returns object with automatically created  __enter__() и __exit__()
```python

@contextmanager
def set_environ(**kwargs):
    """Temporarily set environment 
       variables inside the context … """

    original_env = {k: os.environ.get(k) for k in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for k, v in original_env.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v

# Usage

with set_environ(SCRAPY_CHECK='true'):
    for spidername in args or spider_loader.list():
        spidercls = spider_loader.load(spidername)

```
