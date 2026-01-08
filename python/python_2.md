## Python notes continued
```
SET
* ﻿﻿add()
* ﻿﻿clear)
* ﻿﻿pop()
* ﻿﻿union()
* ﻿﻿issuperset()
* ﻿﻿issubset()
* ﻿﻿intersection()
* ﻿﻿diffrence()
* ﻿﻿isdiscard()
* ﻿﻿setdiscard()
* ﻿﻿copy()
LIST
* ﻿﻿append()
* ﻿﻿copy()
* ﻿﻿count()
* ﻿﻿insert()
* ﻿﻿reverse(
* ﻿﻿remove()
* ﻿﻿sort()
* ﻿﻿pop()
* ﻿﻿extend()
* ﻿﻿index()
* ﻿﻿clear()
DICTIONARIES
* ﻿﻿copy()
* ﻿﻿clear()
* ﻿﻿fromkeys()
* ﻿﻿items)
* ﻿﻿get()
* ﻿﻿keys()
* ﻿﻿pop()
* ﻿﻿values()
* ﻿﻿update()
* ﻿﻿setdefault()
* ﻿﻿popitem()
TUPLES
* ﻿﻿count()
* ﻿﻿index)
Since tuples are immutable, these are the only specific methods available directly to them
```

https://python.plainenglish.io/10-tiny-python-wins-that-changed-my-workflow-forever-5b2ecd3cc888

https://habr.com/ru/articles/967152/

### regex
https://habr.com/ru/articles/972746/

### with (__enter__ __exit__)
https://habr.com/ru/articles/964502/ 

### Transpose Matrix 
```python
m = [[1, 2], [3, 4], [5, 6]]
for row in m:
    print(row)
rez = [[m[j][i] for j in range(len(m))] for i in range(len(m[0]))]
print("\n")
for row in rez:
    print(row)

# output
[1, 2]
[3, 4]
[5, 6]
[1, 3, 5]
[2, 4, 6]
```

### Sparse Matrix

```python
class SparseMatrix2D:
    def __init__(self, rows, cols):
        """Initialize a sparse matrix with given dimensions."""
        self.rows = rows
        self.cols = cols
        self.data = {}  # Dictionary to store non-zero values: {(row, col): value}
    
    def set(self, row, col, value):
        """Set a value at the specified row and column."""
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            raise IndexError(f"Index out of bounds: ({row}, {col})")
        
        if value != 0:
            self.data[(row, col)] = value
        elif (row, col) in self.data:
            # Remove entry if setting to zero
            del self.data[(row, col)]
    
    def mul(self, vec):
        """Multiply sparse matrix by a dense vector."""
        if len(vec) != self.cols:
            raise ValueError(f"Vector length {len(vec)} doesn't match matrix columns {self.cols}")
        
        # Initialize result vector with zeros
        result = [0.0] * self.rows
        
        # For each non-zero entry in the sparse matrix
        for (row, col), value in self.data.items():
            result[row] += value * vec[col]
        
        return result


# Usage:
# Sparse Matrix * Dense Vector
v = [1.] * 8  # vector
m = SparseMatrix2D(rows=10, cols=8)
m.set(row=0, col=0, value=1.)
m.set(2, 0, 1.)
m.set(3, 4, 1.5)
m.set(3, 3, 1.)
m.set(7, 6, 1.)
m.set(5, 2, 5.)
m.set(0, 0, 2.)  # Overwrites the previous value at (0, 0)
o = m.mul(v)
print(o)
print(sum(o))
# "should be 11.5"
```


#### Another implementation of SparseMatrix2D

```python
class SparseMatrix2D:
    """
    A simple sparse 2D matrix backed by dict-of-dicts:
      storage[row][col] = value
    - set(r, c, v): sets/overwrites an entry; if v == 0, deletes the entry.
    - mul(vec): returns the dense result of (self * vec) as a Python list.
    """
    __slots__ = ("rows", "cols", "_data")

    def __init__(self, rows, cols):
        if not isinstance(rows, int) or not isinstance(cols, int):
            raise TypeError("rows and cols must be integers")
        if rows <= 0 or cols <= 0:
            raise ValueError("rows and cols must be positive")
        self.rows = rows
        self.cols = cols
        self._data = {}  # row_index -> {col_index: value}

    def _check_indices(self, row, col):
        if not (0 <= row < self.rows):
            raise IndexError(f"row {row} out of range [0, {self.rows})")
        if not (0 <= col < self.cols):
            raise IndexError(f"col {col} out of range [0, {self.cols})")

    def set(self, row, col, value):
        self._check_indices(row, col)
        if value == 0 or value == 0.0:
            # Remove entry if it exists to keep sparsity
            if row in self._data and col in self._data[row]:
                del self._data[row][col]
                if not self._data[row]:
                    del self._data[row]
            return
        # Insert / overwrite
        row_map = self._data.get(row)
        if row_map is None:
            self._data[row] = {col: float(value)}
        else:
            row_map[col] = float(value)

    def mul(self, vec):
        # Basic validation
        try:
            n = len(vec)
        except Exception as e:
            raise TypeError("vec must be a sequence supporting len() and indexing") from e
        if n != self.cols:
            raise ValueError(f"vector length {n} does not match matrix cols {self.cols}")

        # Compute y = A * x
        out = [0.0] * self.rows
        # Iterate only stored non-zeros
        for r, row_map in self._data.items():
            acc = 0.0
            for c, val in row_map.items():
                acc += val * vec[c]
            out[r] = acc
        return out


# ----------------------------
# Example usage (from prompt):
if __name__ == "__main__":
    v = [1.] * 8  # vector

    m = SparseMatrix2D(rows=10, cols=8)

    m.set(row=0, col=0, value=1.)
    m.set(2, 0, 1.)
    m.set(3, 4, 1.5)
    m.set(3, 3, 1.)
    m.set(7, 6, 1.)
    m.set(5, 2, 5.)
    m.set(0, 0, 2.)  # overwrite

    o = m.mul(v)
    print(o)        # expected: [2.0, 0.0, 1.0, 2.5, 0.0, 5.0, 0.0, 1.0, 0.0, 0.0]
    print(sum(o))   # expected: 11.5
```




### Zip 

Python Zip returns an iterator of tuples, where the i-th tuple contains the i-th element from each of the argument sequences or iterables. 

In follwing code *m unpacks the list of lists so that it's as if you wrote:  
t = zip([1, 2], [3, 4], [5, 6])

```python
matrix = [(1, 2, 3), (4, 5, 6), 
                  (7, 8, 9), (10, 11, 12)]
for row in matrix:
    print(row)
print("\n")
t_matrix = zip(*matrix)
for row in t_matrix:
    print(row)
```
### operator
The operator module in Python provides function-based equivalents of many built-in Python operators   
— like +, -, *, ==, <, and so on.

Makes operators first-class functions, so you can pass them as arguments to higher-order functions like map(), reduce(), or sorted().

Improves readability, especially in functional programming.

Provides efficient versions of itemgetter, attrgetter, and methodcaller for dynamic access.
```
import operator

print(operator.add(2, 3))     # 2 + 3 → 5
print(operator.mul(4, 5))     # 4 * 5 → 20
print(operator.pow(2, 3))     # 2 ** 3 → 8

print(operator.eq(3, 3))      # 3 == 3 → True
print(operator.lt(2, 5))      # 2 < 5 → True
print(operator.ge(7, 4))      # 7 >= 4 → True

print(operator.and_(True, False))  # False
print(operator.or_(True, False))   # True

from operator import itemgetter, attrgetter

# itemgetter: for lists, dicts, tuples
data = [('Alice', 30), ('Bob', 25), ('Carol', 35)]
print(sorted(data, key=itemgetter(1)))  # Sort by age → [('Bob', 25), ...]

# attrgetter: for objects
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

people = [Person("Alice", 30), Person("Bob", 25)]
sorted_people = sorted(people, key=attrgetter("age"))
print([p.name for p in sorted_people])  # ['Bob', 'Alice']

```

### @staticmethod 
Use @staticmethod when you have a method inside a class 
that doesn't access the instance (self) or the class (cls) — it’s just logically grouped under the class.

Static methods are frequently used in real-world code for tasks like input validation, data formatting,  
and calculations—especially when that logic naturally belongs with a class but doesn't need its state.
```python
class User:
    @staticmethod
    def is_valid_email(email):
        return "@" in email and "." in email

```
This method doesn't depend on any part of the User instance, but conceptually belongs in the class.   
It can be used anywhere as `User.is_valid_email(email)`, keeping your code cleaner and more organized.


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


### Generators and yield
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

### flush and fsync
```python
with open("log.txt", "a") as f:
    f.write("Hello\n")
    f.flush()
    os.fsync(f.fileno())
```
### Send e-mail

```python
import smtplib
import socket
from email.mime.text import MIMEText
from shutil import disk_usage

def send_alert(usage):
    host = socket.gethostname()
    msg = MIMEText(f"Disk usage on {host}: {usage}%")
    msg['Subject'] = 'Disk Alert'
    msg['From'] = 'monitoring@example.com'
    msg['To'] = 'admin@example.com'
    
    with smtplib.SMTP('smtp.example.com') as server:
        server.send_message(msg)

def main():
    threshold = 90
    partition = '/'
    
    total, used, _ = disk_usage(partition)
    usage_percent = (used / total) * 100
    
    if usage_percent >= threshold:
        send_alert(round(usage_percent, 1))


if __name__ == '__main__':
    main()

```



### Monitor Folder Changes in Real-Time 

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class Watcher(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'Modified: {event.src_path}')

observer = Observer()
observer.schedule(Watcher(), path='.', recursive=True)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()

```

### Flatten JSON

```python

def flatten_json(d, parent_key='', sep='.'):
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items

nested = {'user': {'id': 1, 'info': {'name': 'Alice'}}}
print(flatten_json(nested))
```


### Directory Monitor with os and time
Objective: Monitor a directory for file changes.

```python
import os
import time
directory = '.'
prev_files = set(os.listdir(directory))
while True:
    time.sleep(5)
    current_files = set(os.listdir(directory))
    new_files = current_files - prev_files
    if new_files:
        print(f"New files: {new_files}")
    prev_files = current_files
```
<https://github.com/peterlamar/python-cp-cheatsheet>
