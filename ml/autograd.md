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

### Use in Deep Learning
In libraries like PyTorch, TensorFlow, and JAX:

You define a forward computation (e.g., loss function).

The framework automatically computes gradients via reverse-mode AD.

These gradients are then used in optimization algorithms like SGD or Adam.








https://rlhick.people.wm.edu/posts/mle-autograd.html
