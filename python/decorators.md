## Decorators

If d is decorator it means:  
x = d(x)

The d above should be callable: have method __call__
```python
def printlog ( func ) :
  def wrapper (* args , ** kwargs ) :
      print (" CALLING : " + func . __name__ )
      return func (* args , ** kwargs )
  return wrapper

@printlog
 def foo(x) :
    print (x + 2)
```
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

### Printing the inputs and outputs of each function
```python
def debug(func):
    def wrapper(*args, **kwargs):
        # print the fucntion name and arguments
        print(f"Calling {func.__name__} with args: {args} kwargs: {kwargs}")
        # call the function
        result = func(*args, **kwargs)
        # print the results
        print(f"{func.__name__} returned: {result}")
        return result
    return wrapper
```
### Running average    
```python    
def running_average ( func ) :
  data = {" total " : 0 , " count " : 0}
  def wrapper (* args , ** kwargs ) :
      val = func (* args , ** kwargs )
      data [" total "] += val
      data [" count "] += 1
      print (" Average of {} so far: {:.01 f}". format (func . __name__ , data [" total "] / data [" count "]) )
      return func (* args , ** kwargs )
  
  return wrapper    
    
```
### Retry decorator
```python
import time
from functools import wraps

def retry(max_tries=3, delay_seconds=1):
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    if tries == max_tries:
                        raise e
                    time.sleep(delay_seconds)
        return wrapper_retry
    return decorator_retry
    

@retry(max_tries=5, delay_seconds=2)
def call_dummy_api():
    response = requests.get("https://jsonplaceholder.typicode.com/todos/1")
    return response
```
### Timing decorator
```python
import time

def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time} seconds to run.")
        return result
    return wrapper
    
@timing_decorator
def my_function():
    # some code here
    time.sleep(1)  # simulate some time-consuming operation
    return    
```

### Catch the start time decorator 
```python
from time import ctime   
def logged(_func):
    def _wrapped():
        print('Function %r called at: %s' % (
            _func.__name__, ctime()))
        return _func()
    return _wrapped
    
@logged
def foo():
    print('foo() called')
```

### @functools.wraps(func)

@functools.wraps(func) is just a helper that copies metadata from the original function onto your wrapper.  
It's a best practice to always use it when writing decorators.

When you decorate a function _without_ @functools.wraps, you lose important information about the original function:

- __name__ (function name)
- __doc__ (docstring)
- __annotations__ (type hints)

Because the decorator replaces the function with wrapper, 
Python thinks the function is now called "wrapper", not the original name.

```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("Before call")
        return func(*args, **kwargs)
    return wrapper

@greet = my_decorator
def greet():
    """Say hello"""
    print("Hello!")

print(greet.__name__)   # greet ✅
print(greet.__doc__)    # Say hello ✅
```


### Loggging decorator
<https://towardsdatascience.com/python-decorators-for-data-science-6913f717669a>

<https://jacobpadilla.com/articles/Functools-Deep-Dive>
```python
import logging
import functools

logging.basicConfig(level=logging.INFO)

def log_execution(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Executing {func.__name__}")
        result = func(*args, **kwargs)
        logging.info(f"Finished executing {func.__name__}")
        return result
    return wrapper

@log_execution
def extract_data(source):
    # extract data from source
    data = ...

    return data

@log_execution
def transform_data(data):
    # transform data
    transformed_data = ...

    return transformed_data

@log_execution
def load_data(data, target):
    # load data into target
    ...

def main():
    # extract data
    data = extract_data(source)

    # transform data
    transformed_data = transform_data(data)

    # load data
    load_data(transformed_data, target)
```



 


