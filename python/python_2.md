## Python notes continued

### @staticmethod 
Use @staticmethod when you have a method inside a class 
that doesn't access the instance (self) or the class (cls) — it’s just logically grouped under the class.

Example: A utility function inside a class

```python
class MathHelper:
    @staticmethod
    def add(a, b):
        return a + b

    @staticmethod
    def multiply(a, b):
        return a * b
```

### @classmethod 
Use @classmethod when you need a method that acts on the class itself (receiving cls as the first argument).  
Typically used for alternative constructors or class-level operations.

Example: Creating an instance in different ways

```python
class Book:
    def __init__(self, title, author):
        self.title = title
        self.author = author

    @classmethod
    def from_string(cls, book_str):
        title, author = book_str.split(' - ')
        return cls(title, author)

# Usage
b1 = Book("1984", "George Orwell")
b2 = Book.from_string("To Kill a Mockingbird - Harper Lee")

print(b1.title, "-", b1.author)  # Output: 1984 - George Orwell
print(b2.title, "-", b2.author)  # Output: To Kill a Mockingbird - Harper Lee
✅ from_string creates a Book instance from a formatted string — it needs access to cls to create a new object.
```


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
```python
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
Generators particularly shine in these use cases:

- Large Dataset Processing: Manage extensive datasets that would otherwise exceed memory constraints if loaded entirely.
- Streaming Data Handling: Effectively process data that continuously arrives in real-time.
- Composable Pipelines: Create data transformation pipelines that benefit from modular and readable design.
- Infinite Sequences: Generate sequences indefinitely, processing elements until a specific condition is met.
- File Processing: Handle files line-by-line without needing to load them fully into memory.

### itertools and composition of generators expressions
```python
from itertools import chain, filterfalse

# Chain multiple generator expressions together
result = chain((x * x for x in range(10)), (y + 10 for y in range(5)))

# Filter values from a generator
odd_squares = filterfalse(lambda x: x % 2 == 0, (x * x for x in range(10)))

# Transform values from a generator
doubled_values = map(lambda x: x * 2, range(10))
```
