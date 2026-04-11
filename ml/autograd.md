## Auto-differentiation, backpropagation

<https://algebrica.org/backpropagation/>


<https://www.youtube.com/watch?v=tIeHLnjs5U8&list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi&index=4&pp=iAQB>

<https://imaddabbura.github.io/posts/mlsys/automatic-differentiation.html>

<https://habr.com/ru/articles/960970/>  gradient decent

https://www.youtube.com/watch?v=EWxa8VHi2iA  Nikolenko. Stochastic Gradient

chain rule
<https://pytorch.org/blog/overview-of-pytorch-autograd-engine/>

<https://habr.com/ru/companies/yadro/articles/1002784/> in C++


<https://www.youtube.com/watch?v=rjPO-k-WaDI>

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


https://www.youtube.com/watch?v=ZGSUrfJcXmA

<https://rlhick.people.wm.edu/posts/mle-autograd.html>


<https://huggingface.co/blog/andmholm/what-is-automatic-differentiation>

<https://habr.com/ru/articles/874592/>

<https://eli.thegreenplace.net/2025/reverse-mode-automatic-differentiation/>

### Automatic differentiation
<https://www.youtube.com/watch?v=17gfCTnw6uE> 

<https://www.youtube.com/watch?v=MmkNSsGAZhw>

<https://www.youtube.com/watch?v=nxaOp76MaDQ>

<https://www.youtube.com/watch?v=wG_nF1awSSY>

<https://www.youtube.com/watch?v=twTIGuVhKbQ>

<https://www.youtube.com/watch?v=sq2gPzlrM0g>

## Когда вычисляется обратное распространение в глубоком обучении зачем вычислять производные по входным сигналам в дополнение к производным по параметрам ?

## Зачем вычислять градиенты по входам, а не только по параметрам?

На первый взгляд кажется, что для обновления весов достаточно $\frac{\partial L}{\partial W}$ — зачем тогда считать $\frac{\partial L}{\partial x}$?

---

### Причина 1: Цепное правило требует этого структурно

Сеть — это композиция слоёв. Для слоя $l$ с входом $x^{(l)}$, весами $W^{(l)}$ и выходом $x^{(l+1)} = f(W^{(l)}, x^{(l)})$:

$$\frac{\partial L}{\partial W^{(l)}} = \frac{\partial L}{\partial x^{(l+1)}} \cdot \frac{\partial x^{(l+1)}}{\partial W^{(l)}}$$

$$\frac{\partial L}{\partial x^{(l)}} = \frac{\partial L}{\partial x^{(l+1)}} \cdot \frac{\partial x^{(l+1)}}{\partial x^{(l)}}$$

Чтобы вычислить $\frac{\partial L}{\partial W^{(l-1)}}$ для **предыдущего** слоя, нужен именно $\frac{\partial L}{\partial x^{(l)}}$ — без него цепочка обрывается. То есть **градиент по входам — это «сигнал», передаваемый назад по сети**.

---

### Причина 2: Обучаемые модули на входе

Если входной сигнал $x$ сам порождается другим обучаемым модулем (например, предыдущим слоем, энкодером, эмбеддингом), то $\frac{\partial L}{\partial x}$ — единственный способ обучить этот модуль. Пример:

```
Embedding → LSTM → Linear → Loss
```

LSTM обновляет свои веса через $\frac{\partial L}{\partial W_{\text{LSTM}}}$, но Embedding получает сигнал только через $\frac{\partial L}{\partial x_{\text{LSTM input}}}$.

---

### Причина 3: Архитектурные паттерны

| Паттерн | Зачем нужен $\frac{\partial L}{\partial x}$ |
|---|---|
| **Skip connections (ResNet)** | Градиент должен пройти напрямую через ветку сложения |
| **GAN (дискриминатор → генератор)** | Градиент течёт от дискриминатора обратно в генератор через входные данные |
| **Meta-learning (MAML)** | Градиент второго порядка по начальным параметрам требует прохода через $x$ |
| **Adversarial examples** | Атака строится именно как $\frac{\partial L}{\partial x_{\text{input}}}$ |
| **Feature visualization** | Оптимизируем входное изображение, а не веса |

---

### Причина 4: Слои без параметров

Слои вроде ReLU, MaxPool, Dropout, LayerNorm (иногда) не имеют обучаемых параметров. Для них $\frac{\partial L}{\partial W}$ попросту не существует, но $\frac{\partial L}{\partial x}$ **обязан** быть вычислен, чтобы сигнал прошёл дальше.

---

### Резюме

> $\frac{\partial L}{\partial W^{(l)}}$ отвечает на вопрос *«как изменить веса этого слоя»*, а $\frac{\partial L}{\partial x^{(l)}}$ — *«как передать ошибку предыдущему слою»*. Первое нужно оптимизатору, второе — самому алгоритму backprop для продолжения вычислений.

Оба вычисляются из одного и того же промежуточного результата $\frac{\partial L}{\partial x^{(l+1)}}$, поэтому дополнительные затраты минимальны.

Короткий ответ:
**производные по входным сигналам нужны, чтобы передать градиент дальше назад по сети**, а не для обновления параметров напрямую.

---

## 📌 1. Что мы вообще хотим получить?

В обучении нейросети мы хотим:

* вычислить градиенты функции потерь ( L )
* по параметрам ( W, b )

То есть:
[
\frac{\partial L}{\partial W}, \quad \frac{\partial L}{\partial b}
]

👉 Эти градиенты используются в градиентном спуске.

---

## 📌 2. Но сеть — это цепочка функций

Рассмотрим простой случай:

[
x \rightarrow \text{Layer 1} \rightarrow \text{Layer 2} \rightarrow L
]

Каждый слой — это функция:
[
z^{(1)} = f^{(1)}(x), \quad z^{(2)} = f^{(2)}(z^{(1)})
]

---

## 📌 3. Цепное правило (самое главное)

Чтобы найти градиенты для ранних слоев, используется **цепное правило**:

[
\frac{\partial L}{\partial z^{(1)}} =
\frac{\partial L}{\partial z^{(2)}} \cdot
\frac{\partial z^{(2)}}{\partial z^{(1)}}
]

👉 Вот здесь и появляется:

* производная по входу слоя ( \frac{\partial z^{(2)}}{\partial z^{(1)}} )

---

## 📌 4. Почему нужны производные по входу слоя?

Потому что:

👉 **вход одного слоя = выход предыдущего слоя**

То есть:

* чтобы обучить слой 1, нужно знать:
  [
  \frac{\partial L}{\partial z^{(1)}}
  ]
* а это вычисляется через:
  [
  \frac{\partial L}{\partial z^{(2)}}
  ]

---

## 📌 5. Интуитивно

Представь поток информации:

```
Forward pass:    x → layer1 → layer2 → loss
Backward pass:   loss → layer2 → layer1 → x
```

Во время backward:

* слой 2 получает градиент и:

  * вычисляет градиенты по своим весам ✅
  * вычисляет градиент по входу ❗

👉 этот градиент по входу передается в слой 1

---

## 📌 6. Формально для одного слоя

Пусть:
[
y = f(x, W)
]

Тогда при backprop считаем:

* ( \frac{\partial L}{\partial W} ) — для обновления весов
* ( \frac{\partial L}{\partial x} ) — чтобы передать дальше назад

---

## 📌 7. Что если НЕ считать производные по входу?

Тогда:

* градиент "застрянет" на текущем слое
* предыдущие слои не смогут обучаться

👉 сеть превратится в:

* обучается только последний слой

---

## 📌 8. Аналогия

Представь конвейер:

* каждый рабочий:

  * считает свою ошибку (градиент по параметрам)
  * передает сигнал предыдущему рабочему (градиент по входу)

Если не передать сигнал назад:

* предыдущие "рабочие" не узнают, что делают неправильно

---

## 📌 9. Важное замечание

Производные по входу:

* **не используются напрямую для обновления параметров**
* но **необходимы для вычисления градиентов предыдущих слоев**

---

## ✅ Итог

Производные по входным сигналам нужны потому что:

* нейросеть — это композиция функций
* используется цепное правило
* градиент нужно "протолкнуть назад" через все слои
* без этого ранние слои не обучаются

---

Если хочешь, могу:

* разобрать это на конкретном PyTorch примере с тензорами и shapes
* или показать математику для linear + ReLU слоя шаг за шагом 👍

