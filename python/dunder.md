
## Dunder methods and descriptors 
are two different Python language mechanisms, 
although both are part of Python’s object model and are often used together internally.

<https://www.thepythoncodingstack.com/p/do-you-get-it-now-getitem-getattr-getattribute-get>

### 1. Dunder methods (`__something__`)

"Dunder" means **double underscore**.

These are special methods that define how objects behave with Python syntax and built-in operations.

Examples:

```python
__init__
__str__
__len__
__iter__
__add__
__getitem__
```

They are invoked automatically by Python.

Example:

```python
class Vector:
    def __init__(self, x):
        self.x = x

    def __add__(self, other):
        return Vector(self.x + other.x)

    def __str__(self):
        return f"Vector({self.x})"

a = Vector(3)
b = Vector(4)

print(a + b)      # calls __add__
print(str(a))     # calls __str__
```

So:

```python
a + b
```

becomes internally:

```python
a.__add__(b)
```

Dunder methods customize:

* operators
* indexing
* iteration
* printing
* context managers
* attribute access
* function calls
* comparisons
* etc.

---

### 2. Descriptors

Descriptors are objects that control attribute access.

They implement one or more of:

```python
__get__
__set__
__delete__
```

Descriptor protocol:

```python
class MyDescriptor:
    def __get__(self, instance, owner):
        ...

    def __set__(self, instance, value):
        ...

    def __delete__(self, instance):
        ...
```

Descriptors power:

* `property`
* methods
* `classmethod`
* `staticmethod`
* ORM fields
* validation frameworks
* many internals of Python classes

Example:

```python
class Positive:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if value < 0:
            raise ValueError("must be positive")
        instance.__dict__[self.name] = value


class Account:
    balance = Positive()

a = Account()
a.balance = 100

print(a.balance)

a.balance = -5     # raises ValueError
```

Here:

* `balance` is not a normal attribute
* it is a descriptor object
* assignment triggers `__set__`
* reading triggers `__get__`

---

### Key conceptual difference

#### Dunder methods - Define behavior of the *whole object*.

Examples:

* how object adds
* prints
* iterates
* compares

---

#### Descriptors - Define behavior of *attributes* on objects.

Examples:

* computed attributes
* validation
* lazy loading
* bound methods

---

### Important connection

Descriptors themselves use dunder methods:

```python
__get__
__set__
```

So descriptors are actually a *specific protocol implemented via dunder methods*.

That means:

* all descriptor hooks are dunder methods
* but not all dunder methods are descriptors

---

### Simple mental model

## Dunder methods

"How does this object behave?"

```python
obj + x
len(obj)
obj[i]
```

---

### Descriptors "What happens when this attribute is accessed?"

```python
obj.attr
obj.attr = value
del obj.attr
```

---

### Example showing both together

```python
class Logged:
    def __get__(self, instance, owner):
        print("getting value")
        return 42


class Example:
    x = Logged()

    def __str__(self):
        return "Example object"


e = Example()

print(e.x)     # descriptor __get__
print(e)       # dunder __str__
```

Output:

```python
getting value
42
Example object
```

---

### Extra subtle point

Functions in classes are descriptors.

Example:

```python
class A:
    def hello(self):
        print("hi")
```

When you access:

```python
a.hello
```

Python internally uses the descriptor protocol on the function object to create a **bound method**.

This is one of the most important real-world uses of descriptors.
