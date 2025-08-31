### Python logging

<https://www.dash0.com/guides/logging-in-python>  
<https://www.youtube.com/watch?v=9L77QExPmI0>

print(f”{value=}”)

### ABC vs Protocol

#### Nominal Subtyping
In nominal subtyping, types are related by name.   
That means, a type is a subtype of another only if it is explicitly declared to be so (via inheritance or any other such mechanism).

#### Structural Subtyping
In structural subtyping, types are related by structure — meaning if one type has all the fields and methods of another, it’s a subtype,   
even if it wasn’t explicitly declared.

In Python, variables are not bound to a specific type.   
This means you can assign any type of value to a variable at any point in the program, and its type can change dynamically during runtime.

Python provides the built-in issubclass() function to check, at runtime, whether one class is considered a subtype of another.

Now, whether issubclass() checks only nominal subtyping or only structural subtyping or both —  
the answer can vary depending on the use of Abstract Base Classes (ABCs) and Protocols.

<https://realpython.com/courses/exploring-protocols-python/>

<https://levelup.gitconnected.com/abstract-base-classes-abcs-and-protocols-in-python-f9c791ad84cd>

### String formatting
<https://mkaz.blog/working-with-python/string-formatting>
```python
a = 1
b = "hello"

print("I want to say: " + b + " (" + str(a) + ")")
print("I want to say: %s (%s)" % (a, b))
print("I want to say: %(text)s (%(number)s)" % {"text": a, "number": b})
print("I want to say {} ({})".format(a, b))
print(f"I want to say {a} ({b})")

print(f"{a=}")   # a=1
```
### t-strings (Python 3.14)
<https://snarky.ca/unravelling-t-strings/>
<!--
https://habr.com/ru/articles/911196/
-->

### glom jmespath pydash

# Comparison: glom vs jmespath vs pydash

## 🔍 High-Level Comparison

| Feature / Library       | `glom`                                | `jmespath`                          | `pydash`                              |
|-------------------------|----------------------------------------|-------------------------------------|----------------------------------------|
| Type                    | Data transformation and access tool   | Query language for JSON             | Functional utility library (lodash-like) |
| Ideal Use Case          | Structured nested data manipulation   | Read/query JSON                     | General-purpose data manipulation       |
| Syntax Style            | Pythonic, declarative DSL             | Custom query language string        | Functional chaining and helpers        |
| Transformations         | ✅ Yes (complex pipelines)             | ❌ Read-only                         | ✅ Some basic transformations           |
| JSON Compatibility      | ✅ Good                                | ✅ Excellent                         | ✅ Good                                 |
| Custom Functions        | ✅ Callable and DSL                    | ❌ Not directly                      | ✅ Python functions                     |
| Default Value Handling  | ✅ Built-in with `default=` or `Coalesce` | ✅ With `||` fallback syntax         | ❌ No built-in, must handle manually   |
| Default Value Handling  | ✅ Built-in                            | ✅ With `||` (fallback)              | ❌ Manual fallback logic                |
| Performance             | Moderate                              | Fast (C implementation)             | Fast (pure Python)                     |

---

## 🧪 Example Comparison

Given:

```python
data = {
    "person": {
        "name": "Alice",
        "info": {
            "age": 30,
            "email": "alice@example.com"
        }
    },
    "friends": [
        {"name": "Bob", "age": 25},
        {"name": "Carol", "age": 27}
    ]
}
```

### 🔸 `glom`

```python
from glom import glom

glom(data, 'person.info.email')             # 'alice@example.com'
glom(data, ('friends', ['name']))           # ['Bob', 'Carol']
```

### 🔸 `jmespath`

```python
import jmespath

jmespath.search('person.info.email', data)  # 'alice@example.com'
jmespath.search('friends[*].name', data)    # ['Bob', 'Carol']
```

### 🔸 `pydash`

```python
import pydash

pydash.get(data, 'person.info.email')       # 'alice@example.com'
pydash.map_(data['friends'], 'name')        # ['Bob', 'Carol']
```

---

## 🧠 When to Use Each

### ✅ `glom`
- You want **Python-native syntax** for data access and transformations.
- Need **default handling**, **deep traversal**, or **custom logic**.
- Useful for **pipeline-like transformations**.

### ✅ `jmespath`
- You want a **compact and powerful query language**.
- Mostly **read/query only** operations on JSON.
- You work with APIs, AWS, or structured JSON responses.

### ✅ `pydash`
- You need **lodash-like utilities** in Python.
- Want a broad set of functions (deep get, clone, filter, etc.).
- Prefer **functional programming** utilities.

---

## 🔚 Summary

| Use Case                         | Best Tool     |
|----------------------------------|---------------|
| Query deeply nested JSON         | `jmespath`    |
| Pythonic access + transformation | `glom`        |
| Functional utilities + JSON get  | `pydash`      |


###  Monitor and restart 
```python
import subprocess
import sys
import time
import os
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API работает"}

@app.get("/shutdown")
async def shutdown():
    """Останавливаем сервис для теста"""
    os._exit(1)

@app.get("/status")
async def status():
    return {"is_running": True}

def run_server():
    """Запуск FastAPI сервера"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def monitor_and_restart():
    """Мониторинг с автоперезапуском"""
    while True:
        try:
            print("[Monitor] Запускаем сервис...")
            process = subprocess.Popen([sys.executable, __file__, "--server"])
            process.wait()  # Ждем завершения
            print("[Monitor] Сервис упал, перезапуск через 3 сек...")
            time.sleep(3)
        except KeyboardInterrupt:
            print("[Monitor] Остановка")
            break

def main():
    monitor_and_restart()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        # Режим сервера
        run_server()
    else:
        # Режим монитора
        main()
```
Как протестировать
```
1. Запустите скрипт: python script.py
2. Откройте http://127.0.0.1:8000/status – увидите {"is_running": true}
3. Откройте http://127.0.0.1:8000/shutdown – процесс завершится
4. Через 3 секунды в терминале появится сообщение о перезапуске
5. Снова проверьте /status – API снова работает
```
Ограничения и когда есть смысл использовать
```
Это решение не замена supervisor, Docker restart policies или Kubernetes. Оно лишь имитирует простейший автоперезапуск на уровне приложения. Это подойдет для:
- Тестовых стендов
- Прототипов
- Простых сервисов, где не хочется поднимать тяжелую инфраструктуру

Для продакшена стоит добавить обработку исключений, логирование и более продуманное разделение между API и служебными процессами.
```

### Small puzzles

There are 2 python integer arrays A and B of the same size N.
The goal is to check whether there is a swap operation which can be performed on these arrays  
in such a way that the sum of elements in array A equals the sum of elements in array B after the swap.
By swap operation we mean picking one element from array A and  
one element from array B and exchanging them.
```python
def can_swap_to_equal_sum(A, B):
    sum_a = sum(A)
    sum_b = sum(B)
    diff = sum_a - sum_b

    # For the swap to equalize sums, the difference must be even
    if diff % 2 != 0:
        return False

    # We want to find two elements a ∈ A and b ∈ B such that:
    # sum_a - a + b == sum_b - b + a
    # Simplifying gives: a - b == (sum_a - sum_b) / 2
    target = diff // 2

    set_b = set(B)
    for a in A:
        b = a - target
        if b in set_b:
            return True  # such a pair exists

    return False  # no such pair found
```

### Counting sort O(n + k)
Notice that we have to know the range of the sorted values.  
First, count the elements in the array of counters.   
Next, just iterate through the array of counters in increasing order.

If all the elements are in the set {0, 1, . . . , k},   
then the array used for counting should be of size k + 1.  
```python
def countingSort(A, k):
  n = len(A)
  count=[0]*(k+1)  # initalize with 0
  for i in range(n):
    count[A[i]] += 1

  p=0
  for i in range(k + 1):
    for j in range(count[i]):
      A[p] = i
      p += 1
  return A
```
### Python Function to Find Majority Element (Occurs More Than Half the Time)

Here's a Python function using the Boyer-Moore Voting Algorithm, 
which works in O(n) time and O(1) space:

```python
def find_majority_element(arr):
    candidate = None
    count = 0

    for num in arr:
        if count == 0:
            candidate = num
            count = 1
        elif num == candidate:
            count += 1
        else:
            count -= 1

    # Optional: Verify that candidate is actually majority
    if arr.count(candidate) > len(arr) // 2:
        return candidate
    return None
```

### Most frequent element in Array
```python
from collections import Counter

def most_frequent_element(arr):
    if not arr:
        return None
    counter = Counter(arr)
    return counter.most_common(1)[0][0]
```

### Top 10 Most frequent elements in Array

```python
from collections import Counter

def top_10_frequent_elements(arr):
    counter = Counter(arr)
    return counter.most_common(10)
```
### MAX sum subarray with O(n) time complexity
For each position, we compute the largest sum that ends in that position. 
If we assume that the maximum sum of a slice ending in position i equals max_ending,  
then the maximum slice ending in position i+1 equals max(0, max_ending+ ai+1).
```python
def  max_slice(A):
  max_ending = max_slice = 0
  for a in A:
    max_ending = max(0, max_ending + a)
    max_slice = max(max_slice, max_ending)

return max_slice
```


### Python Function to Find Top 10 Most Frequent Elements without Using collections.Counter

You can use a dictionary to count frequencies manually and then sort the result:

```python
def top_10_frequent_elements(arr):
    freq_map = {}
    for item in arr:
        if item in freq_map:
            freq_map[item] += 1
        else:
            freq_map[item] = 1

    # Sort by frequency in descending order and take top 10
    sorted_items = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:10]
```


### Given n sticks as array count the number of triangles that can be constructed using these sticks. 
More precisely, we have to count the number of triplets at indices x < y < z, such that a[x] +a[y] > a[z].

Solution O(n2):
For every pair x,y we can find the largest stick z that can be used to construct the triangle.  
Every stick k, such that y < k <= z, can also be used, because the condition ax + ay > ak 
will still be true. 
We can add up all these triangles at once.  
We can instead use the caterpillar method. 
When increasing the value of y, we can increase (as far as possible) the value of z.

```python
def triangles(A):
  n = len(A)
  result = 0
  for x in xrange(n):
    z=x+2

  for y in xrange(x + 1, n):
    while (z < n and A[x] + A[y] > A[z]):
      z += 1
    result += z - y - 1

return result
```
The time complexity of the above algorithm is O(n2), because for every stick x the values of y and z increase O(n) number of times.

