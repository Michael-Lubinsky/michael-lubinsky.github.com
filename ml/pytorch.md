### PyTorch

<img width="374" height="268" alt="image" src="https://github.com/user-attachments/assets/7ec8e369-c70e-41e1-9ddd-6f7328e0942f" />

```python
class NeuralNetwork(nn.Module):          # define model class
    def __init__(self):
        super().__init__()               # initialize nn.Module
        self.flatten = nn.Flatten()      # [B,1,28,28] -> [B,784]
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(28*28, 512),       # [B,784] -> [B,512]
            nn.ReLU(),                   # [B,512] -> [B,512]
            nn.Linear(512, 512),         # [B,512] -> [B,512]
            nn.ReLU(),                   # [B,512] -> [B,512]
            nn.Linear(512, 10),          # [B,512] -> [B,10]
        )

    def forward(self, x):                # x: [B,1,28,28]
        x = self.flatten(x)              # x: [B,784]
        logits = self.linear_relu_stack(x) # logits: [B,10]
        return logits    # return [B,10]  
```

This code defines a very simple **feed-forward neural network** in PyTorch for something like **MNIST digit classification**.

## The code structure

```python
class NeuralNetwork(nn.Module):
```

This creates a custom neural network class.

* `nn.Module` is the base class for all PyTorch models.
* By inheriting from it, your class becomes a PyTorch model.

---

## 1. Constructor: `__init__`

```python
def __init__(self):
    super().__init__()
```

* `__init__` runs when the model object is created.
* `super().__init__()` initializes the parent `nn.Module` class.
* This is required so PyTorch can track layers and parameters.

Initializes the parent class nn.Module.
allows PyTorch to track parameters

enables .parameters(), .to(device), saving/loading, etc.


## 2. Flatten layer

```python
self.flatten = nn.Flatten()
```

This layer converts multi-dimensional input into a 1D vector.

For example, if input image shape is:

```python
[batch_size, 1, 28, 28]
```

after flattening it becomes:

```python
[batch_size, 784]
```

because:

```python
28 * 28 = 784
```

So each image is turned into a single vector of 784 numbers.

## 3. Stack of linear + ReLU layers

```python
self.linear_relu_stack = nn.Sequential(
    nn.Linear(28*28, 512),
    nn.ReLU(),
    nn.Linear(512, 512),
    nn.ReLU(),
    nn.Linear(512, 10),
)
```

`nn.Sequential(...)` means:

> apply these layers one after another in order

### Layer by layer

### First layer

```python
nn.Linear(28*28, 512)
```

* input: 784 features
* output: 512 features

This is a fully connected layer.

It computes:

[
y = xW^T + b
]

So it learns 512 combinations of the 784 input pixels.

---

### Activation

```python
nn.ReLU()
```

ReLU means:

[
ReLU(x) = \max(0, x)
]

It replaces negative values with 0 and keeps positive values.

Why needed:

* adds nonlinearity
* allows network to learn complex patterns

Without ReLU, multiple linear layers would still behave like one linear layer.

---

### Second hidden layer

```python
nn.Linear(512, 512)
```

* input: 512
* output: 512

Another fully connected layer.

---

### Another ReLU

```python
nn.ReLU()
```

Again adds nonlinearity.

### Output layer

```python
nn.Linear(512, 10)
```

* input: 512
* output: 10

This usually means the model predicts one of **10 classes**.

For MNIST, these classes are digits:

```python
0, 1, 2, 3, 4, 5, 6, 7, 8, 9
```

---

## 4. Forward pass

```python
def forward(self, x):
    x = self.flatten(x)
    logits = self.linear_relu_stack(x)
    return logits
```

This defines how input data moves through the model.

### Step 1

```python
x = self.flatten(x)
```

Flatten image into a vector.

### Step 2

```python
logits = self.linear_relu_stack(x)
```

Pass the flattened input through all layers.

### Step 3

```python
return logits
```

Return the output.

## What are `logits`?

`logits` are the raw output scores of the model.

Example output for one image:

```python
[-1.2, 0.8, 3.1, -0.5, ...]
```

There are 10 numbers, one per class.

Important:

* these are **not probabilities yet**
* usually `CrossEntropyLoss` is applied later, and it internally applies softmax

Predicted class is typically:

```python
logits.argmax(dim=1)
```

---

## Input and output shapes

If input batch shape is:

```python
[64, 1, 28, 28]
```

then:

1. after `Flatten()`:

```python
[64, 784]
```

2. after first linear:

```python
[64, 512]
```

3. after second linear:

```python
[64, 512]
```

4. after output layer:

```python
[64, 10]
```

So for each of the 64 images, model outputs 10 class scores.

---

## What kind of network is this?

This is a:

* **fully connected neural network**
* also called **MLP** (multilayer perceptron)

It is **not** a CNN, because it does not use convolution layers.

That means:

* simple
* easy to understand
* works on small image tasks
* but usually worse than CNN on image data, because flattening loses spatial structure

---

## Why `28*28`?

Because the code expects images of size **28 by 28** pixels.

That is common for MNIST / Fashion-MNIST datasets.

If input image size changes, this layer must also change.

For example:

* 32×32 image → use `nn.Linear(32*32, ...)`
* RGB 32×32 image → flattened size is `3*32*32 = 3072`

---

## Summary of the architecture

In compact form:

```python
input image
-> flatten
-> linear(784 -> 512)
-> ReLU
-> linear(512 -> 512)
-> ReLU
-> linear(512 -> 10)
-> logits
```

## In plain English

The model:

1. takes a 28×28 image
2. turns it into a list of 784 pixel values
3. processes it through two hidden layers
4. outputs 10 scores
5. the highest score is the predicted class

---

## Small note

Usually the model is used like this:

```python
model = NeuralNetwork()
pred = model(images)
loss = loss_fn(pred, labels)
```

where `loss_fn` is often:

```python
nn.CrossEntropyLoss()
```

---

## One important caveat

Because the image is flattened immediately, the model does **not** explicitly understand:

* local shapes
* edges
* neighboring pixels
* 2D structure of image

A CNN usually performs better on images for this reason.

---


<https://blog.ezyang.com/2019/05/pytorch-internals/>

<https://pytorch.org/blog/computational-graphs-constructed-in-pytorch/>

<https://0byte.io/articles/pytorch_introduction.html>

<https://machinelearningmastery.com/pytorch-tutorial-develop-deep-learning-models/>

<https://github.com/srush/Tensor-Puzzles>

<https://www.reddit.com/r/MachineLearning/comments/1repn7v/d_ml_engineers_how_did_you_actually_learn_pytorch/>

<https://www.amazon.com/dp/1778042724/> The Hundred-Page Language Models Book: hands-on with PyTorch (The Hundred-Page Books)

<https://www.youtube.com/watch?v=dES5Cen0q-Y> (part 2)  
<https://www.youtube.com/watch?v=-HhE-8JChHA> is the video to accompany 

<https://0byte.io/articles/helloml.html>

<https://www.deeplearning.ai/courses/pytorch-for-deep-learning-professional-certificate/

Free book: <https://zekcrates.quarto.pub/deep-learning-library/>

### Deep Learning with PyTorch — Step-by-Step Beginner's Guides (3 volumes)

Vol.1 (Fundamentals): <https://amzn.to/4aRmIUv>

Vol.2 (Computer Vision): <https://amzn.to/4s88BkD>

Vol.3 (Sequences and NLP): <http://amzn.to/49bh5h2>


Ml by hand : <https://github.com/workofart/ml-by-hand>

https://www.amazon.com/dp/1633436586/ Deep Learning with PyTorch

https://machinelearningmastery.com/pytorch-tutorial-develop-deep-learning-models/

https://habr.com/ru/companies/netologyru/articles/995500/

https://habr.com/ru/companies/otus/articles/975328/ модель множественной регрессии с нуля

https://www.iamtk.co/mastering-pytorch-from-linear-regression-to-computer-vision

https://www.clcoding.com/2024/10/deep-learning-with-pytorch-image.html

https://news.ycombinator.com/item?id=44276476 I have reimplemented Stable Diffusion 3.5 from scratch in pure PyTorch (github.com/yousef-rafat)

### torchvista

An interactive tool to visualize the forward pass of a PyTorch model directly in the notebook
https://github.com/sachinhosmani/torchvista/

https://www.reddit.com/r/learnmachinelearning/comments/1qyjjui/interactive_visualisation_of_pytorch_models_from/

### ONNX C++

https://habr.com/ru/articles/991430/
