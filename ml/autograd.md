## Auto-differentiation

Auto-differentiation is neither symbolic differentiation nor numerical approximations using finite difference methods.   
What auto-differentiation provides is code augmentation where code is provided for derivatives of your functions free of charge.


Automatic Differentiation is a method for computing exact derivatives of numerical functions expressed as code,  
by systematically applying the chain rule to a computation graph.

| Method                        | Characteristics                                                     |
| ----------------------------- | ------------------------------------------------------------------- |
| Symbolic differentiation      | Can be slow or produce very large expressions (like in SymPy)       |
| Numerical differentiation     | Uses finite differences → approximate, suffers from rounding errors |
| **Automatic Differentiation** | Exact, efficient, and works well for complex programs               |


### Two Modes of AD

#### Forward Mode AD

Computes derivatives along the direction of input variables.

Efficient when number of inputs ≪ number of outputs.

#### Reverse Mode AD (used in deep learning)

Computes derivatives starting from the outputs back to the inputs.

Efficient when number of outputs ≪ number of inputs (e.g., loss → many weights).

##  Autograd 
autograd refers to tools or libraries that implement automatic differentiation.

Examples:
PyTorch’s autograd: Core system that powers backward gradients

```python
import torch

x = torch.tensor([2.0], requires_grad=True)
y = x**2 + 3*x
y.backward()  # compute dy/dx
print(x.grad)  # prints tensor([7.])
```
JAX’s grad:
```
python
import jax.numpy as jnp
from jax import grad

def f(x):
    return x**2 + 3*x

df_dx = grad(f)
print(df_dx(2.0))  # prints 7.0
```

| Term                          | Meaning                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| **Automatic Differentiation** | Technique to compute exact derivatives by code tracing and chain rule              |
| **autograd**                  | Library/tool that implements automatic differentiation                             |
| **Reverse mode AD**           | Used for training neural networks: efficient gradient computation from scalar loss |
| **PyTorch Autograd**          | PyTorch’s system to record and compute gradients of tensor operations              |





### Use in Deep Learning
In libraries like PyTorch, TensorFlow, and JAX:

You define a forward computation (e.g., loss function).

The framework automatically computes gradients via reverse-mode AD.

These gradients are then used in optimization algorithms like SGD or Adam.


### How autograd  is implemented?

 Implementing autograd (automatic differentiation) involves creating a computational graph at runtime   
 and then applying the chain rule to compute derivatives in reverse (for reverse-mode AD, like in PyTorch).

Core Concepts
1. Tensor/Variable with Gradient Tracking
Each number (or tensor) must store:

its value

whether it needs a gradient

its gradient (computed during backward)

a reference to how it was computed (grad_fn)

2. Computational Graph (Dynamic DAG)
Every operation creates a node in a graph:

nodes represent operations (e.g. add, mul)

edges represent data dependencies (inputs → output)

This graph is built dynamically as operations are executed.

3. Backward Pass (Reverse-mode AD)
Start from the output node (typically a scalar like loss)

Recursively apply the chain rule:

Two-Phase Execution


| Phase        | Description                                            |
| ------------ | ------------------------------------------------------ |
| **Forward**  | Build computational graph while performing computation |
| **Backward** | Traverse graph in reverse to compute gradients         |

### Minimal Example of Autograd in Python
Here’s a very simplified custom implementation of autograd for scalar values:

```python
class Value:
    def __init__(self, data, _children=(), _op=''):
        self.data = data
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op  # for debugging

    def __add__(self, other):
        out = Value(self.data + other.data, (self, other), '+')
        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        out = Value(self.data * other.data, (self, other), '*')
        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def backward(self):
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        build_topo(self)

        self.grad = 1.0
        for node in reversed(topo):
            node._backward()

# Example: y = (x1 + x2) * x3
x1 = Value(2.0)
x2 = Value(3.0)
x3 = Value(4.0)
y = (x1 + x2) * x3  # y = (2+3)*4 = 20
y.backward()

print(f"dy/dx1 = {x1.grad}")  # 4.0
print(f"dy/dx2 = {x2.grad}")  # 4.0
print(f"dy/dx3 = {x3.grad}")  # 5.0

```

| Component         | Role                               |
| ----------------- | ---------------------------------- |
| Tensor/Value      | Stores data and gradient info      |
| Computation graph | Tracks operations and dependencies |
| Backward method   | Applies chain rule using graph     |
| Gradients         | Propagated from output to inputs   |



<https://rlhick.people.wm.edu/posts/mle-autograd.html>


<https://huggingface.co/blog/andmholm/what-is-automatic-differentiation>

<https://habr.com/ru/articles/874592/>

https://eli.thegreenplace.net/2025/reverse-mode-automatic-differentiation/
