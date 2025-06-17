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

<https://levelup.gitconnected.com/abstract-base-classes-abcs-and-protocols-in-python-f9c791ad84cd>

### String formatting
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
``
