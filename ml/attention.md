Self-attention computes how each word in a sequence relates to every other word (including itself) and builds a weighted representation of the input. 

It's like saying: "To understand this word, how much should I pay attention to every other word?"

 Self-Attention Process

Input:  [ The, animal, didn't, cross, the, street, because, it, was, too, tired ]

Step 1: Project input into three vectors:
   For each word → Query (Q), Key (K), Value (V)

Step 2: Calculate attention scores:
   Q_i • K_j for all words j

Step 3: Softmax over scores:
   Normalize attention for each word

Step 4: Weighted sum of V using scores:
   Output_i = sum(attention_scores * V_j)
In matrix form:

 
     Input X  →  Q = XW_q
                 K = XW_k
                 V = XW_v

     Attention(Q, K, V) = softmax(QKᵀ / √d_k) • V

```python
import numpy as np

def softmax(x):
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / e_x.sum(axis=-1, keepdims=True)

def self_attention(X, W_q, W_k, W_v):
    # Step 1: Linear projections
    Q = X @ W_q
    K = X @ W_k
    V = X @ W_v

    # Step 2: Compute attention scores
    d_k = Q.shape[-1]
    scores = Q @ K.T / np.sqrt(d_k)

    # Step 3: Softmax to get attention weights
    attn_weights = softmax(scores)

    # Step 4: Weighted sum of V
    output = attn_weights @ V
    return output, attn_weights

# Toy example input: 3 "words", each represented by 4 features
np.random.seed(42)
X = np.random.rand(3, 4)  # (sequence_length, input_dim)

# Random projection matrices (4 -> 4)
W_q = np.random.rand(4, 4)
W_k = np.random.rand(4, 4)
W_v = np.random.rand(4, 4)

output, attn_weights = self_attention(X, W_q, W_k, W_v)

print("Attention Weights:\n", attn_weights)
print("\nOutput:\n", output)
```

What Does This Code Do?
Each "word" is a 4D vector (think embedding).

W_q, W_k, and W_v project the inputs to Query, Key, and Value spaces.

Attention weights are computed as dot products between Queries and Keys.

softmax converts these into probabilities.

Output is a weighted sum of Values according to attention scores.  
