## Python notes

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
### import

### __init__

### pip

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

### SimPy - discrete event simulation
https://simpy.readthedocs.io/en/latest/

