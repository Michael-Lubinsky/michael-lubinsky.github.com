### Dataclass 

In a Python @dataclass, the order=True option means the class will automatically get comparison methods:

__lt__ (less than)  
__le__ (less than or equal)  
__gt__ (greater than)  
__ge__ (greater than or equal)

These methods compare objects field by field **in the order they are defined**, just like a tuple comparison.

By default, all fields are used in comparison unless you exclude some using field(compare=False)
Example: label is excluded from comparison in code below


```python
from dataclasses import dataclass, field, InitVar
from typing import List
import math

@dataclass(order=True, frozen=True)
class Point3D:
    # Fields with default values
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Field excluded from generated methods (e.g. repr, eq, order)
    label: str = field(default="", compare=False, repr=False)

    # Init-only variable (not stored as attribute)
    magnitude_threshold: InitVar[float] = 0.0

    # Post-init processing
    def __post_init__(self, magnitude_threshold):
        magnitude = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if magnitude < magnitude_threshold:
            object.__setattr__(self, "label", "Too Small")  # needed because frozen=True

@dataclass
class Polygon:
    name: str
    vertices: List[Point3D] = field(default_factory=list)  # default factory for mutable type

    def add_vertex(self, point: Point3D):
        self.vertices.append(point)

# Usage
p1 = Point3D(1, 2, 3, magnitude_threshold=5)
p2 = Point3D(4, 5, 6)
p3 = Point3D(1, 2, 3, magnitude_threshold=1)

print(p1)       # Demonstrates __repr__ and frozen assignment via __post_init__
print(p1 == p3) # Demonstrates __eq__ (True, because only x, y, z are compared)
print(p1 < p2)  # Demonstrates ordering (__lt__)
print(p1.label) # Shows label set in __post_init__

## Sorting array of Point3D objects
points = [
    Point3D(3, 2, 1),
    Point3D(1, 2, 3),
    Point3D(1, 1, 1)
]

# Sort in ascending order
sorted_points = sorted(points)
print(sorted_points)

# Sort by squared distance from origin
sorted_points = sorted(points, key=lambda p: p.x**2 + p.y**2 + p.z**2)

### Poligon example:
poly = Polygon("Triangle")
poly.add_vertex(p1)
poly.add_vertex(p2)

print(poly)     # Uses default __repr__, shows use of default_factory for list
```

| Feature           | Explanation                                                               |
| ----------------- | ------------------------------------------------------------------------- |
| `@dataclass`      | Generates boilerplate code like `__init__`, `__repr__`, etc.              |
| `frozen=True`     | Makes the instance immutable.                                             |
| `order=True`      | Enables ordering comparison methods (`<`, `>`, etc.)                      |
| `field()`         | Customizes each field’s behavior (e.g., exclude from comparison or repr). |
| `default_factory` | Initializes mutable fields safely.                                        |
| `InitVar`         | Input to `__post_init__` but not part of the dataclass fields.            |
| `__post_init__`   | Runs after `__init__`, used for additional initialization logic.          |


