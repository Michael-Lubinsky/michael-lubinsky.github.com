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

Now, whether issubclass() checks only nominal subtyping or only structural subtyping or both —  
the answer can vary depending on the use of Abstract Base Classes (ABCs) and Protocols.

<https://realpython.com/courses/exploring-protocols-python/>

<https://levelup.gitconnected.com/abstract-base-classes-abcs-and-protocols-in-python-f9c791ad84cd>

 
