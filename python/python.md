## Python notes

https://realpython.com/python-subprocess

https://www.youtube.com/@PyConUS

https://data-hacks.com/python-programming-language

https://riverml.xyz/latest/ Online machine learning in Python

### Python dependency management

https://nielscautaerts.xyz/python-dependency-management-is-a-dumpster-fire.html

https://martynassubonis.substack.com/p/python-project-management-primer

https://martynassubonis.substack.com/p/python-project-management-primer-a55

https://news.ycombinator.com/item?id=42676432

### pip 

https://www.techbeamers.com/python-pip-usage/

https://pip.pypa.io/en/stable/

export PIP_REQUIRE_VIRTUALENV=true`  
will force you to not install packages in the system site-packages.

To check dependencies:  
  python -m pip check  
To get a JSON output of your current virtual environment:  
  python -m pip inspect  
To update stuff automatically:  
  python -m pip install --upgrade   
Or, skip worrying about dependencies:  
  python -m pip install --no-deps
  
Do a dry run installation with full report on what would be installed:  
pip install --ignore-installed --dry-run --quiet --report

Display only those packages that are not dependencies of other installed packages.  
python -m pip list --not-required  
```
python -m pip: This runs the pip module as a script using the specified Python interpreter.
list: This subcommand lists all installed Python packages in the current environment.
--not-required: This flag filters the output to display only those packages that are not dependencies of other installed packages.
```
###  pyenv

https://news.ycombinator.com/item?id=42419822

brew info --json python3 | jq -r '.[].versioned_formulae[]'

### pipx

https://zahlman.github.io/posts/2025/01/07/python-packaging-2/

### uv  

https://docs.astral.sh/uv/

https://www.saaspegasus.com/guides/uv-deep-dive/

https://martynassubonis.substack.com/p/python-project-management-primer-a55

https://www.peterbe.com/plog/run-standalone-python-2025

https://news.ycombinator.com/item?id=42676432

https://simonwillison.net/2024/Dec/19/one-shot-python-tools/

### dataclass
```
from dataclasses import dataclass
@dataclass(kw_only=True)
class Example
  a: int
  b: int

ex1=Example(a=1, b=2)  
ex2=Example(1,2) # error
```
### any and all
```
x = [1, 2, 3, 4, 10, 12, 7, 8]

check if exists at least one number > 10

if any((a := i) > 10 for i in x):
    print(f'Yes, found number > 10. It is {a}!')

И, соответственно, все ли числа меньше 10
check if all  numbers < 10

if all((a := i) < 10 for i in x):
    print(f'All numbers < 10')
else:
    print(f'Not all numbers < 10. For example, {a}')
```
### Itertools

https://mathspp.com/blog/module-itertools-overview

### Importlib

The importlib library allows you to load modules and packages dynamically.  

```
import importlib
def load_module(module_name):
    module = importlib.import_module(module_name)
    return module
 
# ... Somewhere else in your code
my_module = load_module('my_module')
```
Based on this we can build pthon program which supports plugins:
https://github.com/janvarev/jaapy
https://habr.com/ru/articles/827176/

### JSON manipulation
```
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

### Ibis amd SQLFrame

https://sqlframe.readthedocs.io/en/stable/

https://github.com/eakmanrq/sqlframe/blob/main/blogs/sqlframe_universal_dataframe_api.md

https://ibis-project.org/why

https://ibis-project.org/posts/1tbc/

https://www.youtube.com/watch?v=1ND6COslBKU

### Pandas series
```
import pandas as pd
t_list = [25, 28, 26, 30, 29, 27, 31]
t_series = pd.Series(t_list, name='Temperature')
print(t_series.mean())  # Calculate mean
```
A series mainly consists of the following three properties: index, datatype and shape

1) Index: Each element in a Series has a unique label or index that we can use to access the specific data points.
```
data = [10.2, 20.1, 30.3, 40.5]
series = pd.Series(data, index=["a", "b", "c", "d"])
print(series["b"])  # Access element by label
print(series[1])    # Access element by position

```
2) Data Type: All elements in a Series share the same data type.
   It is important for consistency and enabling smooth operations.

```
print(series.dtype)
print(series.shape)
print(series.loc["c"])  # Access by label
print(series.iloc[2])   # Access by position
```
Missing values
```
series.iloc[1] = np.nan # npy here is an object of numpy
print(series.dropna())  # Drop rows with missing values
```

#### Series Resampling
```
dates = pd.date_range(start="2024-01-01", periods=4)
temp_series = pd.Series([10, 12, 15, 18], index=dates)
# Calculate monthly avg temperature
print(temp_series.resample("M").mean())
```
### Pandas dataframe
Following code uses the .index attribute of the DataFrame to access the row labels and select the first 10 rows.
```
import pandas as pd
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
print(df.to_string(index=False))

df["A"].mean()

first_10_rows = df.loc[df.index[:10]]
print(first_10_rows)

first_10_rows = df.iloc[:10]
print(first_10_rows)

first_10_rows = df.query(‘index < 10’)
print(first_10_rows)
```

### Pandas queries
```
import pandas as pd
df = pd.DataFrame({"col1" : range(1,5), 
                   "col2" : ['A A','B B','A A','B B'],
                   "col3" : ['A A','A A','B B','B B']
                   })
newdf = df.query("col2 == 'A A'")  # hardcoded filter

myval1 = 'A A'
newdf = df.query("col2 == @myval1") # variable in filter

## pass column name to query:
myvar1 = 'col2'
newdf2 = df.query("{0} == 'A A'".format(myvar1))


## pass multiple column names to query:
myvar1 = 'col2'
myvar2 = 'col3'
newdf2 = df.query("{0} == 'A A' & {1} == 'B B'".format(myvar1, myvar2)) 


```
### Pandas and NumPy links

https://www.kdnuggets.com/visualizing-data-directly-numpy-arrays

https://realpython.com/python-for-data-analysis/

https://medium.com/@deyprakash753/14-pandas-tricks-you-must-know-aee396dde875

https://towardsdatascience.com/7-advanced-tricks-in-pandas-for-data-science-41a71632b5d9

https://github.com/DataForScience/

### Working with database

#### Parsing TOML Files in Python
```
You need Python 3.11 or a later version to use tomllib.
https://docs.python.org/3/library/tomllib.html

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
```
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
``` 
import psycopg2

with psycopg2.connect(**credentials) as conn:
	with conn.cursor() as cur:
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

### Magic methods (starts and ends with  __ )

https://docs.python.org/3/reference/datamodel.html#special-method-names

```__init__ __new__ __call__ __enter__ __exit__  __get_item__ __str__ __repr__```

https://medium.com/techtofreedom/9-advanced-magic-methods-in-python-to-customize-classes-conveniently-a1f50fa4b53e


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

### Decorators and other code snippets

https://medium.datadriveninvestor.com/mastering-advanced-python-40-pro-level-snippets-for-2024-85f5b9359103

https://python.plainenglish.io/mastering-python-100-advanced-python-cheatsheets-for-developers-a5da6f176667

https://towardsdatascience.com/pythons-most-powerful-decorator-6bc39e6a8dd8

### Pipilines

https://hamilton.dagworks.io/en/latest/

https://pipefunc.readthedocs.io/en/latest/

https://www.youtube.com/watch?v=tyWpb8E4fqo  10 python libs

### SimPy - discrete event simulation
https://simpy.readthedocs.io/en/latest/

