Writing an LLM from scratch:
https://www.gilesthomas.com/python

## Self-attention

Self-attention computes how each word in a sequence relates to every other word (including itself) and builds a weighted representation of the input. 

It's like saying: "To understand this word, how much should I pay attention to every other word?"

### Self-Attention Process

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

## Multi-Head Attention:
Instead of using one attention function, we use multiple "heads", each with its own set of learned W_q, W_k, and W_v.

Each head learns different attention patterns—like focusing on syntax in one head and semantics in another.

Outputs of all heads are concatenated and passed to the next layer.

This technique is crucial in Transformers, allowing the model to learn richer representations of language.

In multi-head attention, a "head" refers to an independent attention mechanism.    
Each head computes its own set of self-attention weights using a separate set of projection matrices:

W_q (for queries)

W_k (for keys)

W_v (for values)

🔁 What Happens in Each Head?
Each head performs the full attention process:
 
Attention(Q, K, V) = softmax(QKᵀ / √d_k) • V  
But every head has its own learned linear projections, 
so it looks at the input from a different "perspective".

🧠 Why Use Multiple Heads?
Using multiple heads allows the model to:

Capture different relationships between tokens.

Head 1 might learn to focus on previous words (e.g., grammar).

Head 2 might learn to focus on next words (e.g., context).

Attend to different positions or features in parallel.

## Transformer

Transformer is — it’s a neural network architecture that has become the foundation of modern AI models, including ChatGPT, BERT, and GPT.

🔷 What is a Transformer?
The Transformer is a deep learning model architecture introduced in the 2017 paper “Attention Is All You Need”. It was originally designed for sequence transduction tasks like language translation, but it now powers a wide range of applications in NLP, vision, and more.

🧠 Core Idea:
Instead of relying on recurrence (like RNNs or LSTMs), Transformers use a mechanism called self-attention to model dependencies between input tokens, regardless of their position.

🔧 Transformer Architecture Overview
A Transformer has two main parts:

1. Encoder (left side)
Processes the input sequence.

Generates a representation of the input.

2. Decoder (right side)
Generates the output sequence (used in translation, summarization, etc.).

Takes the encoder's output and generates one token at a time.

| Component                     | Description                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------- |
| **Multi-Head Self-Attention** | Allows the model to focus on different parts of the sequence simultaneously. |
| **Feed-Forward Network**      | A fully connected layer applied to each position.                            |
| **Layer Normalization**       | Helps stabilize training.                                                    |
| **Residual Connections**      | Help gradients flow better during training.                                  |
| **Positional Encoding**       | Since Transformers lack recurrence, this provides a sense of word order.     |


A Transformer is:

A stack of layers that use self-attention and feed-forward networks.

Designed to process entire sequences in parallel.
