
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
