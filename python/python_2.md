## Python notes 2

### Generators and yeld
When a normal function returns, its stack frame (containing local variables and execution context) is immediately destroyed.  
In contrast, a generator’s stack frame is suspended when it yields a value and resumed when next() is called again. 
This suspension and resumption is managed by the Python interpreter,   
maintaining the exact state of all variables and the instruction pointer.

```python
def simple_generator():
    print("First yield")
    yield 1
    print("Second yield")
    yield 2
    print("Third yield")
    yield 3

gen = simple_generator()
value = next(gen)  # Prints "First yield" and returns 1
value = next(gen)  # Prints "Second yield" and returns 2


def yield_all_numbers(numbers: list):
    """Generator - produces one value at a time"""
    for i in range(numbers):
        yield i

def fibonacci_generator(limit):
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b

# Multiple yield points with conditional logic
def conditional_yield(data):
    for item in data:
        if item % 2 == 0:
            yield f"Even: {item}"
        else:
            yield f"Odd: {item}"
```

### Generator expressions
Python offers a concise syntax for creating generators called generator expressions. 
These are similar to list comprehensions but use parentheses and produce values lazily: 
```
# List comprehension - creates the entire list in memory
squares_list = [x * x for x in range(10)]


# Generator expression - creates values on demand
squares_gen = (x * x for x in range(10))
The performance difference becomes significant with large datasets:

import sys
import time

# Compare memory usage and creation time for large dataset
start = time.time()
list_comp = [x for x in range(100_000_000)]
list_time = time.time() - start
list_size = sys.getsizeof(list_comp)

start_gen = time.time()
gen_exp = (x for x in range(100_000_000))
gen_time = time.time() - start_gen
gen_size = sys.getsizeof(gen_exp)

print(f"List comprehension: {list_size:,} bytes, created in {list_time:.4f} seconds")
# List comprehension: 835,128,600 bytes, created in 4.9007 seconds

print(f"Generator expression: {gen_size:,} bytes, created in {gen_time:.4f} seconds")
# Generator expression: 200 bytes, created in 0.0000 seconds
```
