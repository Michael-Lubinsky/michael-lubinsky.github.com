## Build From Scratch


<img width="472" height="51" alt="image" src="https://github.com/user-attachments/assets/0ee72af4-ba9a-407c-8554-774d4a061b1c" />


**FlashAttention** 
```
is a fast and memory-efficient algorithm for computing the **attention operation**
used in Transformer models (like GPT, BERT, etc.).
It was introduced in 2022 to dramatically speed up training and inference of large language models.
```

### 1. Reminder: What Attention Does

In a Transformer, attention computes:

[
Attention(Q,K,V) = softmax\left(\frac{QK^T}{\sqrt{d}}\right)V
]

where:

* **Q** = queries
* **K** = keys
* **V** = values
* (QK^T) produces a matrix of size **N × N** (sequence length squared)
```
Problem:

If sequence length is **N**, attention requires:

* **O(N²) memory**
* **O(N²) compute**

For long sequences this becomes extremely expensive.
```
Example:

| Tokens | Attention matrix size |
| ------ | --------------------- |
| 1k     | 1M entries            |
| 10k    | 100M entries          |
| 100k   | 10B entries           |

This is why long-context LLMs are difficult.


### 2. What FlashAttention Changes

FlashAttention does **not change the math** of attention.

It changes **how the computation is executed on GPU**.

Key idea:

> Compute attention in **small blocks that stay inside GPU SRAM** instead of writing large intermediate matrices to slow GPU memory (HBM).

Standard attention:

```
Compute QK^T  → store large matrix in GPU memory
Softmax
Multiply by V
```

FlashAttention:

```
Load small block of Q,K,V
Compute partial attention
Apply streaming softmax
Accumulate result
Move to next block
```

The full attention matrix is **never stored in memory**.

---

### 3. Why It Is Faster

GPU architecture:

| Memory               | Speed   |
| -------------------- | ------- |
| Registers            | fastest |
| SRAM / shared memory | fast    |
| HBM (GPU DRAM)       | slow    |

Standard attention constantly writes/reads the **N×N matrix from HBM**.

FlashAttention:

* keeps blocks in **SRAM**
* avoids writing large intermediate matrices
* reduces memory traffic dramatically

Result:

* **2–4× faster**
* **10–20× lower memory usage**

# 4. Simplified Algorithm Idea

Instead of computing

```
softmax(QK^T)V
```

FlashAttention processes rows in blocks:

```
for block_i in Q:
    for block_j in K,V:
        compute Q_i * K_j^T
        update running softmax
        accumulate V contribution
```

A special **online softmax algorithm** ensures numerical stability while streaming.

---

### 5. Why It Matters for LLMs

FlashAttention enables:

* longer context windows
* larger batch sizes
* faster training

Used by many modern models:

* GPT-4 style architectures
* LLaMA
* Mistral
* Claude
* Falcon

Libraries implementing it:

* **PyTorch 2.x**
* **xFormers**
* **Triton kernels**


### 6. Evolution

Versions:

| Version               | Improvement               |
| --------------------- | ------------------------- |
| FlashAttention (2022) | basic IO-aware attention  |
| FlashAttention-2      | faster parallelization    |
| FlashAttention-3      | optimized for Hopper GPUs |

### 7. Important Insight

FlashAttention is an example of **algorithm + hardware co-design**.

It does **exactly the same attention mathematically**, but reorganizes computation to match GPU memory hierarchy.

✅ **Summary**

FlashAttention is a GPU-optimized algorithm that computes Transformer attention **without materializing the huge attention matrix**, making LLM training and inference dramatically faster and more memory-efficient.
 
```
Neural networks separate layers by breaking linearity with an activation
function. Activation functions are non-linear to prevent composable matmul
from collapsing layers, and are differentiable or mostly-differentiable to
support back propagation.
```

https://www.iclimbtrees.com/courses

### Loss Function in DL

<https://www.datacamp.com/tutorial/loss-function-in-machine-learning>

<https://arxiv.org/pdf/2504.04242v1>

https://miriamposner.com/blog/introducing-beginners-to-the-mechanics-of-machine-learning/ 

https://zekcrates.quarto.pub/deep-learning-library/

 

<https://github.com/Mathews-Tom/no-magic>


https://www.youtube.com/watch?v=3_e0HVV3nMM 


## MicroGPT Karpathy

https://www.reddit.com/user/rsrini7/comments/1r3q5u2/andrej_karpathys_microgpt_architecture_stepbystep/


 Demo : https://ko-microgpt.vercel.app/

Source : https://github.com/woduq1414/ko-microgpt 


<img width="1080" height="589" alt="image" src="https://github.com/user-attachments/assets/bc19e841-ba69-4650-a8ec-5e7756efd54d" />

```
Forward Pass (Making Predictions)
Step 1: Tokenizer - Text to Numbers

    Takes your input text (like "emma")

    Converts each character into a number ID

    Adds a special BOS (Begin/End of Sequence) token at the start and end

    Example: "emma" becomes [BOS, e, m, m, a, BOS] → [26, 4, 12, 12, 0, 26]

Step 2: Embeddings - Numbers to Meaningful Vectors

    Token Embedding (wte): Looks up each character ID and gets a 16-number vector that represents "what this character is"

    Position Embedding (wpe): Gets another 16-number vector that represents "where this character sits in the sequence"

    Combines them: Adds the two vectors together element-by-element to create one input vector per character

Step 3: RMSNorm - Stabilize the Numbers

    Normalizes the input vector to keep values in a stable range

    Prevents numbers from getting too large or too small during calculations

    Formula: divides the vector by sqrt(mean(x²) + epsilon)

Step 4: Attention Layer - Letters Talk to Each Other

    Creates 3 vectors for each token:

        Query (Q): "What am I looking for?"

        Key (K): "What information do I have?"

        Value (V): "What do I want to share?"

    Uses 4 parallel "heads" (each head focuses on different patterns)

    Each position can only look at previous positions (causality enforced structurally via sequential processing and a growing KV cache — no explicit mask matrix)

    Calculates attention scores to decide which previous characters are most relevant

    Combines relevant information from past characters

    Residual connection: Adds the previous representation back (x = x + Attention(x))

Step 5: MLP Block - Deep Thinking

    Expands the 16-dimensional vector to 64 dimensions (more room to think)

    Applies ReLU activation (sets negative numbers to zero)

    Compresses back down to 16 dimensions

    Residual connection: Adds the previous representation back (x = x + MLP(x))

Step 6: LM Head - Turn Thoughts into Character Scores

    Projects the 16-dimensional vector into 27 raw scores (one for each possible character)

    These raw scores are called "logits"

Step 7: Softmax - Scores to Probabilities

    Converts the 27 logits into probabilities that sum to 100%

    Example: 'a' might get 60%, 'o' might get 20%, 'z' might get 0.1%

Training Mode - Learning from Mistakes
Step 8: Calculate Loss

    Compares the predicted probabilities to the correct answer

    Uses Negative Log Likelihood: higher loss = model was more surprised by the correct answer

    Formula: loss = -log(probability of correct character)

Step 9: Backpropagation - Figure Out What Went Wrong

    The custom Autograd engine traces back through every calculation

    For each of the ~4,192 parameters, it calculates: "How much did you contribute to the mistake?"

    This creates gradients (directions to improve)

Step 10: Update Parameters with Adam Optimizer

    Adjusts all 4,192 parameters slightly in the direction that reduces loss

    Learning rate starts at 0.01 and gradually decays to zero

    Repeat Steps 1-10 for 1000 training steps (default)

Inference Mode - Generating New Text
Step 11: Autoregressive Generation Loop

    Start with just the BOS token

    Run forward pass (Steps 1-7) to get probabilities for next character

    Sample a character from the probability distribution (with temperature control for randomness)

    Add that character to your sequence

    Repeat until BOS token is generated again (signals "I'm done")

    Output: A newly generated name like "emma" or "oliver"

Key Principle

The entire architecture runs on pure Python scalars - no NumPy, no PyTorch, no GPU. Every single number is wrapped in a custom Value object that tracks both its value and its gradient, building a computation graph that enables learning through the chain rule.

In essence: Characters get personalities → talk to each other → think deeply → predict what comes next → learn from mistakes → repeat.
```
https://www.youtube.com/watch?v=7xTGNNLPyMI 

https://habr.com/ru/articles/996404/
http://karpathy.github.io/2026/02/12/microgpt/    
https://microgpt.boratto.ca/  
https://github.com/karpathy/minGPT  

### Reznikov Ivan
https://www.linkedin.com/in/reznikovivan/

https://habr.com/ru/articles/995838/

https://www.mlacademy.ai/ml-system-design-sign-up-external Free course

https://habr.com/ru/articles/993824/

https://habr.com/ru/articles/994376/

https://www.youtube.com/watch?v=ChfEO8l-fas   Visualization of ML

https://visualrambling.space/neural-network/  Visualization of ML

https://www.youtube.com/watch?v=qx7hirqgfuU 
Why Deep Learning Works Unreasonably Well [How Models Learn Part 3]

https://github.com/rasbt/LLMs-from-scratch Sebastian Rashka. Build LLM From Scratch

https://www.freecodecamp.org/news/code-an-llm-from-scratch-theory-to-rlhf

https://karpathy.ai/zero-to-hero.html

https://www.amazon.com/Hands-Deep-Learning-Building-Scratch-ebook/dp/B0GDMNQSMZ 

https://eli.thegreenplace.net/2025/notes-on-implementing-attention/



https://zekcrates.quarto.pub/deep-learning-library/

https://github.com/Niki110607/CNN-from-scratch-numpy-

https://github.com/mohamedrxo/simplegrad

https://www.tensortonic.com/


coding a machine learning library in c from scratch
https://www.youtube.com/watch?v=hL_n_GljC0I 
