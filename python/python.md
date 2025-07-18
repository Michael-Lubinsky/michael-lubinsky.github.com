## Python notes
check syntax  
python -m py_compile my_script.py

### None
```python
if x is None:
```
Checks only whether x is exactly None.

It's type-specific and does not consider falsy values like 0, [], '', etc.

```python
if not x:
```
Checks whether x is "falsy" — meaning any of the following:

- None
- False
- 0, 0.0
- '' (empty string)
- [] (empty list)
- {} (empty dict)
- set() (empty set)
- etc.

### *args **kwargs
```python
def greet(*args, **kwargs):  
    for name in args:  
        print(f"Hello, {name}!")  
    for key, value in kwargs.items():  
        print(f"{key} = {value}")

greet("Alice", "Bob", language="Python", level="Intermediate")
```

### zip
zip() takes 2 or more iterables
```python
names = ["James", "Bob", "Kate", "Sarah"]
ages = [20, 54, 34, 19]
locations = ["London",  "San Francisco", "Sydney", "Vancouver"]
 
team_members = zip(names, ages, locations)
 
next(team_members)   # ('James', 20, 'London')
next(team_members)   # ('Bob', 54, 'San Francisco')
next(team_members)   # ('Kate', 34, 'Sydney')
next(team_members)    # ('Sarah', 19, 'Vancouver')
 

sorted_team = sorted(team_members, key=lambda grouping: grouping[1])
sorted_team
# [('Sarah', 19, 'Vancouver'), ('James', 20, 'London'),  ('Kate', 34, 'Sydney'), ('Bob', 54, 'San Francisco')]

names, ages, locations = zip(*sorted_team)

names # ('Sarah', 'James', 'Kate', 'Bob')
ages # (19, 20, 34, 54)
locations # ('Vancouver', 'London', 'Sydney', 'San Francisco')
```

### zip with strict
 zip silently stops at the shortest list, 
 but you can raise  ValueError if lengths don’t match using strict=True
```python
for fruit, count in zip(a, b, strict=True):  
    print(f"{fruit}: {count}")

combined = list(zip(names, scores))
```
unzip example:
```python
zipped = [('Alice', 85), ('Bob', 90), ('Charlie', 78)]
names, scores = zip(*zipped)

print(names)   # ('Alice', 'Bob', 'Charlie')
print(scores)  # (85, 90, 78)
```
### min and max with key
```
fruits = ["apple", "banana", "cherry"]
print(min(fruits, key=lambda x: len(x)))  # Output: apple
print(max(fruits, key=lambda x: len(x)))  # Output: banana
```

### Sorting

sorted_by_len = sorted(list_of_strings, key=len)

Lowecase comes after uppercase in ASCII
```python
names = ['Alice', 'bob', 'Charlie']
print(sorted(names))
print(sorted(names, key=str.lower))
sorted_numbers = sorted(names, reverse=True)


def sort_sales_data_by_sales(data):
 return sorted(data, key=lambda x: x['Sales'])

sales_data = [
 {'Product': 'Laptop', 'Sales': 150},
 {'Product': 'Mouse', 'Sales': 300},
 {'Product': 'Keyboard', 'Sales': 200},
]
print(sort_sales_data_by_sales(sales_data))
```
Order the names using the number of times the letter 'a' appears in the name:
Since sorted() deals with numerical values by ordering them in ascending order,   
the names with no 'a's appear first since .count("a") returns 0 for these names.  
You can add a third keyword argument to sorted(), reverse=True,  
to order the names starting with the one with the most occurrences of the letter 'a'.

```python
def get_number_of_a_s(item):
    return item.lower().count("a")

reordered_names = sorted(some_names, key=get_number_of_a_s)

# same as above using lambda: 
reordered_names = sorted(
    some_names,
    key=lambda item: item.lower().count("a"),
)
```

The built-in sorted() does not change the object passed to it.  
Instead, it returns a new list with the output.   
However, the list method .sort() mutates the list it acts on.  
Since lists are mutable, list methods such as .sort() modify the original list rather than returning a copy.

<https://www.thepythoncodingstack.com/p/the-key-to-the-key-parameter-in-python>

### Context manager

```python
class DatabaseConnection:  
    def __enter__(self):  
        self.conn = connect_to_database()  # Simulate connection  
        print("Connected to database.")  
        return self.conn  

    def __exit__(self, exc_type, exc_val, exc_tb):  
        self.conn.close()  
        print("Connection closed.")  

# Usage  
with DatabaseConnection() as db:  
    db.query("SELECT * FROM users") 
```

Let's order the names using the number of times the letter 'a' appears in the name. 
```python
def get_number_of_a_s(item):
    return item.lower().count("a")

reordered_names = sorted(some_names, key=get_number_of_a_s)
```

### reverse
```python
nums = [1, 2, 3]
print(nums[::-1])
print(list(reversed(nums))) 
```
### Stack, queue and  deque
In Python, there is no built-in stack type. 
Instead, we can simply use a list to represent a stack efficiently: 
```
 .append  -  perform push operations.  
 .pop removes the last element of  list (representing the top of the stack), and returns this element
```

deque (in collections module) is actually a doubly linked list.



### divmod - calculates a quotient and remainder in one shot
```sql
result = divmod(10, 3)
print(result)  # Output: (3, 1)
```
### Enum
<https://mayursurani.medium.com/the-enum-trick-every-python-developer-should-know-a-comprehensive-guide-6092ff7167ea>
<https://mathspp.com/blog/module-enum-overview>
<https://everydaysuperpowers.dev/articles/supercharge-your-enums-cleaner-code-with-hidden-features/>
```python
from enum import Enum

class UserRole(Enum):
    #ADMIN = 1
    #EDITOR = 2
    #VIEWER = 3
    ADMIN = auto()
    EDITOR = auto()
    VIEWER = auto()
    def can_edit(self):
        return self in {UserRole.ADMIN, UserRole.EDITOR}

    def can_delete(self):
        return self == UserRole.ADMIN

role = UserRole.ADMIN
print(role)  # UserRole.ADMIN
print(role.value)  # 1
```

### String

.strip() removes all leading and trailing whitespace characters, including newlines and tabs.
```python
s='!?abc?!'
s.strip('?!')    # 'abc'

string.removeprefix(prefix)
string.removesuffix(suffix)
```
### Dictionary: get() and setdefault(), defaultdict

If you use [] to access a non-existent key, you’ll get a KeyError.   
But if you use .get(), you’ll get None (or a default value you specify).

```python
dictionary.get(key, default=None)   -- will not raise exception if key not found

# Transform this verbose code
user_stats = {}
if "login_count" not in user_stats:
    user_stats["login_count"] = 1
else:
    user_stats["login_count"] += 1

# Into this elegant one-liner
user_stats.setdefault("login_count", 0) += 1

from collections import defaultdict

# Track word frequencies elegantly
word_counts = defaultdict(int)
for word in ["apple", "banana", "apple", "cherry"]:
    word_counts[word] += 1  # No need for key existence check!

```
#### Sort dict by key and by val
```python
sorted_by_key = dict(sorted(data.items()))  
sorted_by_value = dict(sorted(data.items(), key=lambda x: x[1]))
```
#### Merging dictionaries:
in case of duplicate keys the value from last dict will be used
```python
dict1 = {'a': 1, 'b': 2}
dict2 = {'b': 3, 'c': 4}
merged_dict = dict1 | dict2

# In-place update
default_config |= user_config
```
#### defaultdict

```python
from collections import defaultdict

groups = defaultdict(list)
groups["fruits"].append("apple")
```
### map
```python
colors = ["red", "blue", "yellow", "gray", "green"]
upper_colors = list(map(str.upper, colors))
print(upper_colors)

Output:
["RED", "BLUE", "YELLOW", "GRAY", "GREEN"]

numbers_str = ["1", "2", "3", "4"]
numbers_int = list(map(int, numbers_str))

celsius = [0, 20, 37, 100]
fahrenheit = list(map(lambda x: (x * 9/5) + 32, celsius))

```
### filter 
```python
numbers = list(range(-5, 5))
greater_than_zero = list(filter(lambda b: b > 0, numbers))
print(greater_than_zero)

Output:
[1, 2, 3, 4]
```

### reduce
Reduce() is used to produce a single value by sequentially combining the elements in a list.  
The reduce() function is located in the functools module. It is necessary to import first.
```
from functools import reduce
words = ["hello", "world", "this", "is", "python"]
sentence = reduce(lambda x, y: x + " " + y, words)
print(sentence)

Output:
hello world this is python
```

### flat nested list
```python
nested = [[1, 2], [3, 4], [5]]
 flat = [item for sublist in nested for item in sublist]
>>> flat
[1, 2, 3, 4, 5]
```
### Dataclass
Automatically generates methods like __init__() and __repr__().

frozen=True   
order=True  
kw_value=True
```python
from dataclasses import dataclass
@dataclass(kw_only=True)
class Example
  a: int
  b: int

ex1=Example(a=1, b=2)  
ex2=Example(1,2) # error, because it expects key=value


@dataclass
class Rectangle:
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

rectangle = Rectangle(10, 20)
print(rectangle.area)       # Outputs: 200
print(rectangle.perimeter)  # Outputs: 60
```
### Dataclass and Enum example:
```python
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum, auto

# Enum for Order Status
class OrderStatus(StrEnum):
    OPEN = auto()
    CLOSED = auto()

@dataclass
class Product:
    name: str
    category: str
    shipping_weight: float
    unit_price: int
    tax_percent: float
    def __post_init__(self):
        if self.unit_price < 0 or self.shipping_weight < 0:
            raise ValueError("unit_price and shipping_weight must be positive.")
        if not (0 <= self.tax_percent <= 1):
            raise ValueError("tax_percent must be between 0 and 1.")

@dataclass
class Order:
    status: OrderStatus
    creation_date: date = date.today()
    products: list[Product] = field(default_factory=list)
    def add_product(self, product: Product):
        self.products.append(product)
    @property
    def sub_total(self) -> int:
        return sum(p.unit_price for p in self.products)
    @property
    def tax(self) -> float:
        return sum(p.unit_price * p.tax_percent for p in self.products)
    @property
    def total_price(self) -> float:
        return self.sub_total + self.tax

# Example Usage
banana = Product(name="banana", category="fruit", shipping_weight=0.5, unit_price=215, tax_percent=0.07)
mango = Product(name="mango", category="fruit", shipping_weight=2.0, unit_price=319, tax_percent=0.11)
order = Order(status=OrderStatus.OPEN)
order.add_product(banana)
order.add_product(mango)
print(f"Total Price: ${order.total_price / 100:.2f}")
```


### Difference between `dataclass` and `TypedDict` in Python

#### `dataclass`:
- Introduced in Python 3.7.
- Used to create classes with automatic `__init__`, `__repr__`, and comparison methods.
- Represents structured data with **runtime behavior and methods**.
- Supports type hints but **does not enforce types at runtime**.
- Instances are mutable by default.
- Useful for creating lightweight classes with behavior.

**Example:**
```python
from dataclasses import dataclass

@dataclass
class Device:
    name: str
    type: str
    value: float
```

---

### `TypedDict`:
- Introduced in `typing` (Python 3.8+) for **static type checking**.
- Represents the expected shape of a dictionary with specific key names and types.
- Provides **no runtime type enforcement** or methods.
- Instances are plain dictionaries, not objects.
- Useful for defining the structure of JSON or dict data for type checkers.

**Example:**
```python
from typing import TypedDict

class DeviceDict(TypedDict):
    name: str
    type: str
    value: float
```

## When to use `TypedDict`:
`TypedDict` is useful when:
- You are working with **JSON-like dictionaries** from APIs, configuration files, or data ingestion.
- You want **static type checking** (with `mypy`, `pyright`, etc.) while continuing to use plain dictionaries for lightweight data.
- You need to ensure keys and value types are consistent without converting dictionaries into classes.

---

## Example scenario:
You are parsing JSON data from an API that returns user data:

```python
from typing import TypedDict
import json

class UserResponse(TypedDict):
    id: int
    name: str
    email: str

raw_json = '{"id": 123, "name": "Alice", "email": "alice@example.com"}'
data = json.loads(raw_json)
```

Using `TypedDict`, you can type hint the parsed data:

```python
def process_user(user: UserResponse) -> None:
    print(f"User {user['id']} - {user['name']} - {user['email']}")

process_user(data)
```

### Benefits:
✅ **Code completion:** Your IDE will suggest keys like `id`, `name`, `email`.
✅ **Static type checking:** Tools will warn if you miss a required key or use the wrong type.
✅ **Zero runtime overhead:** Since `TypedDict` does not wrap the data, you can use plain dictionaries while benefiting from type safety.

---

✅ Use `TypedDict` when working with structured JSON/dict data you want to type-check while keeping your code clean and performant.

### Summary:
| Feature | `dataclass` | `TypedDict` |
|---------|-------------|-------------|
| Structure | Class with fields | Dictionary with typed keys |
| Runtime behavior | Has methods | Plain dict |
| Type enforcement | No runtime enforcement | No runtime enforcement |
| Use case | Lightweight objects with behavior | Typed JSON/dict structures |

✅ Use **`dataclass`** when you need structured, behavior-enabled objects.
✅ Use **`TypedDict`** when you need static type checking for dictionary-shaped data.



### any and all
```python

# Sample data: a list of numbers and a list of booleans
numbers = [1, -5, 0, 10, -2]
conditions = [True, True, False, True]

# Using 'any'
# any() returns True if at least one element in the iterable is True
has_positive = any(x > 0 for x in numbers)
print("Is there any positive number?", has_positive)  # Output: True (because 1 and 10 are positive)

has_negative = any(x < 0 for x in numbers)
print("Is there any negative number?", has_negative)  # Output: True (because -5 and -2 are negative)

all_true = any(conditions)
print("Is there any True in conditions?", all_true)  # Output: True (because there are True values)

# Using 'all'
# all() returns True if every element in the iterable is True
all_positive = all(x > 0 for x in numbers)
print("Are all numbers positive?", all_positive)  # Output: False (because some are negative or zero)

all_non_zero = all(x != 0 for x in numbers)
print("Are all numbers non-zero?", all_non_zero)  # Output: False (because 0 is present)

all_conditions_true = all(conditions)
print("Are all conditions True?", all_conditions_true)  # Output: False (because False is present)

# Edge cases
empty_list = []
print("any() on empty list:", any(empty_list))  # Output: False (no elements to evaluate)
print("all() on empty list:", all(empty_list))  # Output: True (vacuously true, no elements to fail)

x = [1, 2, 3, 4, 10, 12, 7, 8]

# check if exists at least one number > 10

if any((a := i) > 10 for i in x):
    print(f'Yes, found number > 10. It is {a}!')

# check if all  numbers < 10

if all((a := i) < 10 for i in x):
    print(f'All numbers < 10')
else:
    print(f'Not all numbers < 10. For example, {a}')
```
### Itertools

https://mathspp.com/blog/module-itertools-overview

### Importlib

The importlib library allows you to load modules and packages dynamically.  

```python
import importlib
def load_module(module_name):
    module = importlib.import_module(module_name)
    return module
 
# ... Somewhere else in your code
my_module = load_module('my_module')
```
Based on this we can build Python program which supports plugins:  
<https://github.com/janvarev/jaapy>  
<https://habr.com/ru/articles/827176/>  

### Protocol
Protocols provide a way to define structural typing in Python, 
allowing you to create interfaces without the need for explicit inheritance.
<https://realpython.com/python-protocol/>
<https://towardsdev.com/interfaces-en-python-2a7365a9ba14> ABC vs Protocol
 
```python
from typing import Protocol
from abc import ABC, abstractmethod

# Protocol Example
class Printable(Protocol):
    def __str__(self) -> str:
        pass

def print_object(obj: Printable) -> None:
    print(str(obj))

# ABC Example
class Shape(ABC):

    @abstractmethod
    def area(self) -> float:
        pass

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14 * self.radius ** 2

r = Rectangle(4, 5)
c = Circle(3)

print_object(r)     # Output: <__main__.Rectangle object at 0x000001>
print_object(c)     # Output: <__main__.Circle object at 0x000002>
```
### Dependency Injection

Replace:
```python
    class C:
        def __init__(self):
            self.foo = ConcreteFoo()
```
with:

```python
   class C:
        def __init__(self, foo: SupportsFoo):
            self.foo = foo
```
where SupportsFoo is a Protocol. 

### JSON manipulation
```python
import json

def export_json(filename, obj):
    with open(filename, 'w') as writer:
        writer.write(json.dumps(obj, indent=2))

def import_json(filename):
    obj = {}
    with open(filename, 'r') as reader:
        obj = reader.read()
    return json.loads(obj)

sample_dict = {
    "maps": [
        {'a': 1},
        {'b': 2},
        {'c': 3},
        {'d': 4},
    ]
}

export_json('maps.json', sample_dict)
obj = import_json('maps.json')

print(type(obj))
print(obj)

# Export and Import List (List of JSON Objects)

sample_list = [
    {'a': 1},
    {'b': 2},
    {'c': 3},
    {'d': 4},
]

export_json('maps.json', sample_list)
obj = import_json('maps.json')
print(obj)
print(type(obj))
```

### Working with database

#### Parsing TOML Files in Python
 
You need Python 3.11 or a later version to use tomllib.  
<https://docs.python.org/3/library/tomllib.html>
```
Consider a sample TOML file, say db_config.toml,
containing the required info to connect to the database:

File: db_config.toml

[database]
host = "localhost"
port = 5432
database_name = "your_database_name"
user = "your_username"
password = "your_password"
```
Let read TOML file:
```python
import tomllib

with open('db_config.toml','rb') as file:
	credentials = tomllib.load(file)['database']
        print(credentials)

# Output of print(credentials):
{  'host': 'localhost', 'port': 5432,
   'database_name': 'your_database_name',
   'user': 'your_username',
   'password': 'your_password'
}
```
#### Run SQL
```python
import psycopg2

with psycopg2.connect(**credentials) as conn:
	with conn.cursor() as cur:
    	    cur.execute('SELECT * FROM my_table')
    	    result = cur.fetchall()
            print(result)
```

### Cosine similarity implementations
First attempt
```python
def cosine_distance(a, b):
    dot_product = sum(ai * bi for ai, bi in zip(a, b))
    magnitude_a = math.sqrt(sum(ai * ai for ai in a))
    magnitude_b = math.sqrt(sum(bi * bi for bi in b))
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    return 1 - cosine_similarity
```
More performant:
```python
def cosine_distance(a, b):
    dot_product = 0
    magnitude_a = 0
    magnitude_b = 0
    for ai, bi in zip(a, b):
        dot_product += ai * bi
        magnitude_a += ai * ai
        magnitude_b += bi * bi
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    return 1 - cosine_similarity
```
Cosine similarity with NumPy 
```python
    def cosine_distance(vector1, vector2):
        dot_product = np.dot(vector1, vector2)
        norm_vector1 = np.linalg.norm(vector1)
        norm_vector2 = np.linalg.norm(vector2)
        cosine_similarity = dot_product / (norm_vector1 * norm_vector2)
        cosine_distance = 1 - cosine_similarity
        return cosine_distance
```

### Generate date ranges 
```python
import datetime

def generate_dates_in_range(start_date, end_date, range="DAY"):
  start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
  all_dates=[start_date]
  str_next=start_date

  if range == "DAY":
        interval=1
  elif range =="WEEK":
        interval=7
  else:
        print("Unknown range ", range)
        return None

  while str_next < end_date:
    next = start + datetime.timedelta(days=interval)
    str_next=str(next)[0:10]
    all_dates.append(str_next)
    start=next

  return all_dates

# Test

start='2024-01-30'
end='2024-02-05'
print(start, end)
all_dates = generate_dates_in_range(start, end)
print(all_dates)
```

### Given a list of numeric elements,   shift all zeroes to end 
```python
    non_zero_index = 0

    #  first fill the non zero elements from the list.
    for i in range(len(lst)):
        if lst[i] != 0:
            if non_zero_index != i:
                lst[non_zero_index] = lst[i]
            non_zero_index += 1
    
    #  fill the rest of the list with zeroes
    for i in range(non_zero_index, len(lst)):
        lst[i] = 0
```
### Magic methods (starts and ends with  __ )

<https://docs.python.org/3/reference/datamodel.html#special-method-names>

```__init__ __new__ __call__ __enter__ __exit__  __get_item__ __str__ __repr__```

<https://medium.com/techtofreedom/9-advanced-magic-methods-in-python-to-customize-classes-conveniently-a1f50fa4b53e>


## How to save memory:
### Tuple vs List

Given that tuples are immutable (they cannot be changed after creation), 
it allows Python to make optimizations in terms of memory allocation.
```python
import sys

my_tuple = (1, 2, 3, 4, 5)
my_list = [1, 2, 3, 4, 5]

print(sys.getsizeof(my_tuple))
# 80
print(sys.getsizeof(my_list)) 
# 120
```

### Array vs List
```python
import sys
import array

my_list = [i for i in range(1000)]

my_array = array.array('i', [i for i in range(1000)])

print(sys.getsizeof(my_list))  
# 8856
print(sys.getsizeof(my_array)) 
# 4064
```

### Slots 
If you create a lot of objects __slots__ can save memory
```python
import sys

class Author:
    def __init__(self, name, age):
        self.name = name
        self.age = age

class AuthorWithSlots:
    __slots__ = ['name', 'age']

    def __init__(self, name, age):
        self.name = name
        self.age = age

# Creating instances
me = Author('Yang', 30)
me_with_slots = AuthorWithSlots('Yang', 30)

# Comparing memory usage
memory_without_slots = sys.getsizeof(me) + sys.getsizeof(me.__dict__)
memory_with_slots = sys.getsizeof(me_with_slots)
 # __slots__ classes don't have __dict__

print(memory_without_slots, memory_with_slots)
# 152 48
print(me.__dict__)
# {'name': 'Yang', 'age': 30}
print(me_with_slots.__dict__)
# AttributeError: 'AuthorWithSlots' object has no attribute '__dict__'
```

### String interning
 <https://medium.com/techtofreedom/string-interning-in-python-a-hidden-gem-that-makes-your-code-faster-9be71c7a5f3e>
 
### mmap
```python
import mmap

with open('test.txt', "r+b") as f:
    # memory-map the file, size 0 means whole file
    with mmap.mmap(f.fileno(), 0) as mm:
        # read content via standard file methods
        print(mm.read())
        # read content via slice notation
        snippet = mm[0:10]
        print(snippet.decode('utf-8'))
```
  
<!--
### Decorators and other code snippets

https://medium.datadriveninvestor.com/mastering-advanced-python-40-pro-level-snippets-for-2024-85f5b9359103

https://python.plainenglish.io/mastering-python-100-advanced-python-cheatsheets-for-developers-a5da6f176667

https://towardsdatascience.com/pythons-most-powerful-decorator-6bc39e6a8dd8

### Links

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


### Pipelines

https://hamilton.dagworks.io/en/latest/

https://pipefunc.readthedocs.io/en/latest/

https://www.youtube.com/watch?v=tyWpb8E4fqo  10 python libs

https://habr.com/ru/articles/562380/ Statistics

### Discrete event simulation SimPy, Salabim
<https://en.wikipedia.org/wiki/Discrete-event_simulation>
<https://simpy.readthedocs.io/en/latest/>
<https://simulation.teachem.digital/free-simulation-in-python-with-simpy-guide>
<https://github.com/salabim/salabim>

-->
