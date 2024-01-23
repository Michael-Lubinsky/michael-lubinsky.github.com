## Python notes

### Working with database
```
Parsing TOML Files in Python
 

Consider a sample TOML file, say db_config.toml, containing the required info to connect to the database:

# db_config.toml

[database]
host = "localhost"
port = 5432
database_name = "your_database_name"
user = "your_username"
password = "your_password"
 

 

You need Python 3.11 or a later version to use tomllib.
https://docs.python.org/3/library/tomllib.html

  So you can open the db_config.toml file and parse its contents like so:

import tomllib

with open('db_config.toml','rb') as file:
	credentials = tomllib.load(file)['database']
 

Notice that we tap into the ‘database’ section of the db_config.toml file. The load() function returns a Python dictionary. You can verify this by printing out the contents of credentials:

print(credentials)
 

Output >>>
{'host': 'localhost', 'port': 5432, 'database_name': 'your_database_name', 'user': 'your_username', 'password': 'your_password'}
 

Lets connect to a Postgres database.

pip install psycopg2
 
You can use both the connection and the cursor objects in with statements:

import psycopg2

# Connect to the database
with psycopg2.connect(**credentials) as conn:
	# Inside this context, the connection is open and managed

	with conn.cursor() as cur:
    	# Inside this context, the cursor is open and managed

    	cur.execute('SELECT * FROM my_table')
    	result = cur.fetchall()
            print(result)
```

### Cosine similarity
First attempt
```
def cosine_distance(a, b):
    dot_product = sum(ai * bi for ai, bi in zip(a, b))
    magnitude_a = math.sqrt(sum(ai * ai for ai in a))
    magnitude_b = math.sqrt(sum(bi * bi for bi in b))
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    return 1 - cosine_similarity
```
More performant:
```
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
```
    def cosine_distance(vector1, vector2):
        dot_product = np.dot(vector1, vector2)
        norm_vector1 = np.linalg.norm(vector1)
        norm_vector2 = np.linalg.norm(vector2)
        cosine_similarity = dot_product / (norm_vector1 * norm_vector2)
        cosine_distance = 1 - cosine_similarity
        return cosine_distance
```

### Generate date ranges 
```
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

### Time Series Aggregation with pandas

https://kapilg.hashnode.dev/time-series-aggregation-in-pandas

### import

### Magic methods (starts and ends with  __ )

https://docs.python.org/3/reference/datamodel.html#special-method-names

```__init__ __new__ __call__ __enter__ __exit__  __get_item__ __str__ __repr__```

https://medium.com/techtofreedom/9-advanced-magic-methods-in-python-to-customize-classes-conveniently-a1f50fa4b53e

### pip
https://www.techbeamers.com/python-pip-usage/

## How to save memory:
### Tuple vs List

Given that tuples are immutable (they cannot be changed after creation), it allows Python to make optimizations in terms of memory allocation.
```
import sys

my_tuple = (1, 2, 3, 4, 5)
my_list = [1, 2, 3, 4, 5]

print(sys.getsizeof(my_tuple))
# 80
print(sys.getsizeof(my_list)) 
# 120
```

### Array vs List
```
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
```
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
memory_with_slots = sys.getsizeof(me_with_slots)  # __slots__ classes don't have __dict__

print(memory_without_slots, memory_with_slots)
# 152 48
print(me.__dict__)
# {'name': 'Yang', 'age': 30}
print(me_with_slots.__dict__)
# AttributeError: 'AuthorWithSlots' object has no attribute '__dict__'
```

### String interning
 https://medium.com/techtofreedom/string-interning-in-python-a-hidden-gem-that-makes-your-code-faster-9be71c7a5f3e
 
### mmap
```
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
### SimPy - discrete event simulation
https://simpy.readthedocs.io/en/latest/

