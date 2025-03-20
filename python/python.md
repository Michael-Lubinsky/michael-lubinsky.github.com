## Python notes

https://realpython.com/python-subprocess

https://www.youtube.com/@PyConUS

https://data-hacks.com/python-programming-language

https://riverml.xyz/latest/ Online machine learning in Python

https://habr.com/ru/companies/otus/articles/888974/ Type Annotations 

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

If you get SSL errors (common if you are in a hotel or a company network):   
python -m pip install pendulum --trusted-host pypi.org --trusted-host files.pythonhosted.org

If you are behind a corporate proxy that requires authentication:  
python -m pip install pendulum --proxy http://your_username:yourpassword@proxy_address

If you want to download a package without installing it, you can use  
python -m pip download NAME

It will download the package and all its dependencies in the current directory
(the files, called, wheels, have a .whl extension).
You can then install them offline by doing
python -m pip install
on the wheels.

```
### venv

On Windows, use  
   py -3.X -m venv MY_ENV  
to create a virtual environment, and   
   MY_ENV\Scripts\activate  
to use it.

On Mac and Linux, to create a virtual environment:
    python3.X -m venv MY_ENV 
 and to activate it:  
  source MY_ENV/bin/activate” 


Once you have activated a virtual environment, you can install a thing by doing

python -m pip install thing


### 
```
You don't need to activate a virtual environment to use it! This is just a convenience feature.
If you use the commands situated in the Scripts (on windows) or bin (on Unix) folders
in the virtual environment directly, they are specially crafted to only see the virtual environment even without activation.
In fact, activating just make those commands the default ones by manipulating a bunch of environment variables.


The statement "You don't need to activate a virtual environment to use it" means
that even if you don't explicitly activate a virtual environment
(e.g., with source venv/bin/activate or .\venv\Scripts\activate),
 you can still use the environment by referencing its Python executable directly.

How Virtual Environments Work
When you create a virtual environment in Python (using python -m venv venv or similar tools like virtualenv), a directory is created with:

A standalone Python interpreter specific to the virtual environment.
Its own site-packages directory for storing dependencies installed within the virtual environment.
Activation
Activating a virtual environment is essentially a convenience feature:

It modifies your shell environment so that:
The virtual environment's Python interpreter is used by default
(e.g., running python refers to venv/bin/python instead of the system Python).
Commands like pip install packages into the virtual environment.
It often changes the shell prompt to indicate that the virtual environment is active.
Using a Virtual Environment Without Activation
Even if you don't activate the environment, you can use it by directly referencing the Python executable in the virtual environment.

Examples:
Running Python directly:

 
path/to/venv/bin/python script.py      # On macOS/Linux
path\to\venv\Scripts\python script.py  # On Windows

This ensures that the script runs using the virtual environment's Python and its installed packages.

Installing dependencies without activation:
Instead of activating, you can point pip directly to the virtual environment:

 
path/to/venv/bin/pip install requests      # macOS/Linux
path\to\venv\Scripts\pip install requests  # Windows

When Might You Avoid Activation?

In automated scripts or CI/CD pipelines where you can directly specify
the virtual environment's Python executable.
When you want to run isolated commands without modifying your shell environment.
Benefits of Activation
It’s simpler and more intuitive for interactive use.
Ensures that the environment's python and pip are automatically used without needing to specify their full paths every time.
Provides visual feedback via the modified shell prompt to remind you that you're working within the virtual environment.
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
Based on this we can build Python program which supports plugins:
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

