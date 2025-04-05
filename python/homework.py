"""
An algebraic data type is a type formed by combining other types using one of two main ways:
Sum types (aka tagged unions, variants, choices)
Product types (aka tuples, records, structs)

Imagine modeling a Shape:
It can be a Circle with a radius
Or a Rectangle with width and height
That’s a sum type — a Shape can be one of many options (circle OR rectangle).
And within each option, like a Rectangle, you're grouping multiple values — width AND height — which makes that part a product type.

Why are they useful?
Safe by design: You can use pattern matching to exhaustively handle all cases.
Clear and concise: Makes data models expressive.
Foundation for Option/Result types: 
   Optional, Maybe, Result, Either types are all built using algebraic data types.
"""
### Algebraic data type in Python

from dataclasses import dataclass
from typing import Union

@dataclass
class Circle:
    radius: float

@dataclass
class Rectangle:
    width: float
    height: float

Shape = Union[Circle, Rectangle]


arr = [1, 2, 3, 4, 5]
for i in reversed(arr):
    print(i)


## Swap columns #2 and #3 using Python’s standard csv module:

import csv

def swap_columns_2_and_3(input_file, output_file):
    with open(input_file, newline='', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            if len(row) >= 3:
                # Swap columns 2 and 3 (index 1 and 2)
                row[1], row[2] = row[2], row[1]
            writer.writerow(row)

#### same as above but use stdin / stdout instead of files
import csv
import sys

def swap_columns_2_and_3_stdin():
    reader = csv.reader(sys.stdin)
    writer = csv.writer(sys.stdout)

    for row in reader:
        if len(row) >= 3:
            row[1], row[2] = row[2], row[1]
        writer.writerow(row)

####  asyncio

# asyncio.to_thread(sync_f) runs the sync function in a non-blocking way using a thread.
# asyncio.create_task(async_g()) schedules the async function to run concurrently.
# asyncio.gather(...) waits for both to finish.
  
import asyncio

def sync_f():
    print("sync_f started")
    import time
    time.sleep(2)
    print("sync_f finished")
    return "result from sync_f"

async def async_g():
    print("async_g started")
    await asyncio.sleep(2)
    print("async_g finished")
    return "result from async_g"

async def main():
    # Run sync and async functions in parallel and get results
    sync_task = asyncio.to_thread(sync_f)
    async_task = asyncio.create_task(async_g())

    # Wait for both and get return values
    result_sync, result_async = await asyncio.gather(sync_task, async_task)

    print(f"sync_f returned: {result_sync}")
    print(f"async_g returned: {result_async}")

if __name__ == "__main__":
    asyncio.run(main())

############ Metaclass  #############
import functools
import sys


class AnnouncerMeta(type):
    """
    Print method name when called.
    """

    def __new__(cls, class_name, bases, namespace):
        def make_wrapper(func, name):
            @functools.wraps(func)
            def call_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                finally:
                    print(f"Called {name}")
            return call_wrapper

        for name, func in list(namespace.items()):
            if callable(func) and not name.startswith("__"):
                namespace[name] = make_wrapper(func, name)

        return super().__new__(cls, class_name, bases, namespace)


# Leave code below as is; focus on fixing the metaclass

class ExampleClass(metaclass=AnnouncerMeta):
    """
    Just example of class using AnnouncerMeta class.
    """

    def foo(self, n):
        return f"foo{n}"

    def bar(self, n):
        return f"bar{n}"


test_name = sys.stdin.readline().strip()
if test_name == "sample_test":
    instance = ExampleClass()
    print(instance.foo(1) + instance.bar(2))
