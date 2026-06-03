## Protocol
Protocols provide a way to define structural typing in Python, 
allowing you to create interfaces without the need for explicit inheritance.  
<https://realpython.com/python-protocol/>  

### ABC vs Protocol
<https://towardsdev.com/interfaces-en-python-2a7365a9ba14>  

#### Nominal Subtyping
In nominal subtyping, types are related by name.   
That means, a type is a subtype of another only if it is explicitly declared to be so (via inheritance or any other such mechanism).

#### Structural Subtyping
In structural subtyping, types are related by structure — meaning if one type has all the fields and methods of another, it’s a subtype,   
even if it wasn’t explicitly declared.

In Python, variables are not bound to a specific type.   
This means you can assign any type of value to a variable at any point in the program, and its type can change dynamically during runtime.

Python provides the built-in issubclass() function to check, at runtime, whether one class is considered a subtype of another.

In Python, **inheritance** and **Protocol** solve different problems.

### Classical inheritance

Use inheritance when there is a true **"is-a" relationship** and you want to reuse implementation.

```python
class Animal:
    def speak(self):
        raise NotImplementedError

class Dog(Animal):
    def speak(self):
        return "woof"
```

Here:

```python
dog = Dog()
isinstance(dog, Animal)   # True
```

`Dog` explicitly declares that it is an `Animal`.

---

### Protocol

A Protocol specifies **what methods/attributes an object must have**, regardless of its inheritance hierarchy.

Protocols were introduced in Python's `typing` module (PEP 544).

```python
from typing import Protocol

class Speaker(Protocol):
    def speak(self) -> str:
        ...

class Dog:
    def speak(self) -> str:
        return "woof"

class Robot:
    def speak(self) -> str:
        return "beep"
```

Function:

```python
def make_noise(obj: Speaker):
    print(obj.speak())
```

Both work:

```python
make_noise(Dog())
make_noise(Robot())
```

even though neither class inherits from `Speaker`.

This is called **structural typing** ("if it looks like a duck and quacks like a duck, it's a duck").

---

## When Protocol is useful

### 1. Decoupling code

Without Protocol:

```python
def save(data, storage: S3Storage):
    ...
```

Now the function only accepts `S3Storage`.

With Protocol:

```python
class Storage(Protocol):
    def write(self, data: bytes) -> None:
        ...

def save(data, storage: Storage):
    storage.write(data)
```

Any class implementing `write()` can be used:

```python
class S3Storage:
    def write(self, data):
        ...

class LocalFileStorage:
    def write(self, data):
        ...
```

No inheritance required.

---

### 2. Third-party classes

Suppose you use a library class:

```python
class PandasDataFrame:
    ...
```

You cannot modify it to inherit from your base class.

But you can define a Protocol:

```python
class TabularData(Protocol):
    def to_csv(self) -> str:
        ...
```

Any object with `to_csv()` satisfies the protocol.

---

### 3. Dependency Injection and Testing

Production code:

```python
class Database:
    def execute(self, sql: str):
        ...
```

Test code:

```python
class FakeDatabase:
    def execute(self, sql: str):
        ...
```

Protocol:

```python
class DB(Protocol):
    def execute(self, sql: str):
        ...
```

Now both real and fake implementations work without sharing a common parent class.

---

### 4. Multiple unrelated implementations

For example, many objects can be "serializable":

```python
class Serializable(Protocol):
    def to_json(self) -> str:
        ...
```

A User, Order, Product, or Configuration class may all satisfy the protocol without any common ancestor.

---

## Comparison

| Feature                        | Inheritance | Protocol                       |
| ------------------------------ | ----------- | ------------------------------ |
| Reuse implementation           | Yes         | No                             |
| Defines interface              | Yes         | Yes                            |
| Requires explicit subclassing  | Yes         | No                             |
| Works with third-party classes | Usually no  | Yes                            |
| Structural typing              | No          | Yes                            |
| Runtime `isinstance()`         | Yes         | Limited (`@runtime_checkable`) |

---

### Rule of thumb

Use **inheritance** when:

* classes share behavior and implementation,
* there is a genuine "is-a" relationship,
* you want polymorphism through a common base class.

Use **Protocol** when:

* you care only about the methods/attributes an object provides,
* implementations are unrelated,
* you want loose coupling,
* you're doing dependency injection, mocking, or library design.

A common modern Python pattern is:

```python
# Public API uses Protocols
class Storage(Protocol):
    def write(self, data: bytes) -> None:
        ...

# Concrete implementations may use inheritance internally
class S3Storage:
    ...

class AzureStorage:
    ...
```

This gives maximum flexibility while preserving static type checking with tools like `mypy` and `pyright`.


Now, whether issubclass() checks only nominal subtyping or only structural subtyping or both —  
the answer can vary depending on the use of Abstract Base Classes (ABCs) and Protocols.

<https://realpython.com/courses/exploring-protocols-python/>

<https://levelup.gitconnected.com/abstract-base-classes-abcs-and-protocols-in-python-f9c791ad84cd>

 
