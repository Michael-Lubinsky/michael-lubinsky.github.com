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
 ```
 __init__,
 __repr__,
 __eq__,
 __lt__,  
```

### @property decorator
```python
class Student:
    def __init__(self):
        self._score = 0

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, s):
        if 0 <= s <= 100:
            self._score = s
        else:
            raise ValueError('The score must be between 0 ~ 100!')

Yang = Student()

Yang.score=99
print(Yang.score)
# 99

Yang.score = 999
# ValueError: The score must be between 0 ~ 100!
```

###  @lru_cache: Speed Up Your Programs by Caching
The simplest way to speed up your Python functions with caching tricks is to use the @lru_cache decorator.  
This decorator can be used to cache the results of a function,   
so that subsequent calls to the function with the same arguments will not be executed again.
It is especially helpful for functions that are computationally expensive or that are called frequently with the same arguments.

Example:
```
import time

def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


start_time = time.perf_counter()
print(fibonacci(30))
end_time = time.perf_counter()
print(f"The execution time: {end_time - start_time:.8f} seconds")
# The execution time: 0.18129450 seconds
```
The above program calculates the Nth Fibonacci number with a Python function. 
It’s time-consuming cause when you calculate the fibonacci(30), many previous Fibonacci numbers will be calculated many times during the recursion process.

Now, let’s speed it up with the @lru_cache decorator:
```python
from functools import lru_cache
import time
@lru_cache(maxsize=None)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


start_time = time.perf_counter()
print(fibonacci(30))
end_time = time.perf_counter()
print(f"The execution time: {end_time - start_time:.8f} seconds")
# The execution time: 0.00002990 seconds
```
As the above code shows, after using the @lru_cache decorator, we can get the same result in 0.00002990 seconds, 
which is super faster than the previous 0.18129450 seconds.

The @lru_cache decorator has a maxsize parameter that specifies the maximum number of results to store in the cache.  
When the cache is full and a new result needs to be stored, 
the least recently used result is evicted from the cache to make room for the new one. 
This is called the least recently used (LRU) strategy.

By default, the maxsize is set to 128. 
If it is set to None, as our example, the LRU features are disabled and the cache can grow without bound.

 ###  contextmanager decorator
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

```python
from contextlib import contextmanager
import time

@contextmanager
def timer(label='Operation'):
    start = time.time()
    yield
    end = time.time()
    print(f"[{label}] took {end - start:.4f} seconds")

# How to use it:

with timer("Data Processing"):
    process_data()
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

### one more logging decorator
```
import logging
import functools

def log_calls(func=None, level=logging.INFO):
    """Log function calls with arguments and return values."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args_str = ", ".join([str(a) for a in args])
            kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            all_args = f"{args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str}"

            logging.log(level, f"Calling {func.__name__}({all_args})")
            result = func(*args, **kwargs)
            logging.log(level, f"{func.__name__} returned {result}")

            return result
        return wrapper

    # Handle both @log_calls and @log_calls(level=logging.DEBUG)
    if func is None:
        return decorator
    return decorator(func)
```

### memoization

```python
def memoize(func):
    """Caches the return value of a function based on its arguments."""
    cache = {}

    def wrapper(*args, **kwargs):
        # Create a key that uniquely identifies the function call
        key = str(args) + str(kwargs)

        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper

@memoize
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

<!--
<https://www.kdnuggets.com/custom-python-decorator-patterns-worth-copy-pasting-forever>

https://habr.com/ru/articles/910424/

https://towardsdatascience.com/pythons-most-powerful-decorator-6bc39e6a8dd8

<https://towardsdatascience.com/python-decorators-for-data-science-6913f717669a>

<https://jacobpadilla.com/articles/Functools-Deep-Dive>
 
-->

