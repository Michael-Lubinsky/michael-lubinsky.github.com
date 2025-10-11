https://eli.thegreenplace.net/2025/notes-on-implementing-attention/

Writing an LLM from scratch:
https://www.gilesthomas.com/python

https://medium.com/@royrimo2006/understanding-and-implementing-transformers-from-scratch-3da5ddc0cdd6

https://nlp.seas.harvard.edu/annotated-transformer/  
https://news.ycombinator.com/item?id=45002896

https://habr.com/ru/companies/bothub/articles/922938/

### Input Representation: Word Embeddings

Before you can project anything, each word in your input string needs to be represented numerically. This is usually done using word embeddings.

What are Word Embeddings? They are dense vector representations of words where words with similar meanings have similar vector representations.   
Popular pre-trained word embeddings include Word2Vec, GloVe, and FastText.   
More advanced methods like BERT, GPT, and others use contextual embeddings, where the embedding for a word changes based on its surrounding words in a sentence.


 **2\. Learnable Linear Transformations (Weight Matrices)**

Projecting input strings into Query (Q), Key (K), and Value (V) vectors for each word is a core component of self-attention mechanisms, notably the Transformer architecture.  
The magic of projecting into Q, K, and V vectors lies in **learnable linear transformations**. For each word embedding, you multiply it by three different weight matrices:

$W^Q$ (Weight Matrix for Queries)  
$W^K$ (Weight Matrix for Keys)  
$W^V$ (Weight Matrix for Values)  

These weight matrices are parameters of the model that are learned during the training process (e.g., via backpropagation and gradient descent). Each matrix has a specific dimensionality:

If your word embedding has dimension $d_{model}$ (e.g., 512), and you want your Q, K, V vectors to have dimension $d_k$ (often $d_{model} / h$, where $h$ is the number of attention heads), then:
$W^Q$ will be of shape $(d_{model}, d_k)$
$W^K$ will be of shape $(d_{model}, d_k)$
$W^V$ will be of shape $(d_{model}, d_v)$ (where $d_v$ is often equal to $d_k$, but can be different)
3. The Projection Calculation
For each word's embedding ($Emb_{word}$), you perform the following matrix multiplications:

Query (Q) for word i: Q_i = Emb_{word_i} \cdot W^Q
Key (K) for word i: K_i = Emb_{word_i} \cdot W^K
Value (V) for word i: V_i = Emb_{word_i} \cdot W^V
Example with "The quick brown fox":

Let's assume our word embeddings ($Emb$) are 512-dimensional vectors, and we want our Q, K, V vectors to be 64-dimensional.

$W^Q$ will be a $512 \times 64$ matrix.
$W^K$ will be a $512 \times 64$ matrix.
$W^V$ will be a $512 \times 64$ matrix.


For the word "The":

$$Q_{The} = Emb_{The} \cdot W^Q$$
 
$$K_{The} = Emb_{The} \cdot W^K$$
 
$$V_{The} = Emb_{The} \cdot W^V$$

You repeat this process for "quick," "brown," and "fox," generating a Q, K, and V vector for each.



### Why three distinct vectors (Q, K, V)?

This separation is crucial for the self-attention mechanism:

Query (Q): Represents "what I'm looking for" or "what information is relevant to me."   
When a word computes its attention score, it uses its Query vector to compare against other words' Key vectors.

Key (K): Represents "what I contain" or "what information I offer." Each word's Key vector is compared against other words' Query vectors to determine relevance.

Value (V): Represents "the actual information to be passed along." Once attention scores are calculated (based on Q and K), the Value vectors of relevant words are weighted and summed to form the output of the attention mechanism.

This design allows the model to learn different aspects of each word's role in the attention calculation, leading to a powerful mechanism for capturing contextual relationships.  

These weight matrices are parameters of the model that are learned during the training process (e.g., via backpropagation and gradient descent). Each matrix has a specific dimensionality:


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


A Transformer is a stack of layers that use self-attention and feed-forward networks.

Designed to process entire sequences in parallel.

In the context of self-attention mechanisms in machine learning, particularly in models like Transformers, projecting an input string into Query (Q), Key (K), and Value (V) vectors is a crucial step. 

Below, I explain how this process works for each word in the input string, assuming the input is tokenized into words or subwords and represented as embeddings. The

explanation is concise yet detailed to aid your learning.

## Step-by-Step Process to Project Input String into Q, K, V Vectors

### Tokenize and Embed the Input String:

Input String: Suppose your input string is "The cat sleeps".
Tokenization: Split the string into tokens (e.g., words or subwords). For simplicity, assume one token per word: ["The", "cat", "sleeps"].
Embedding: Convert each token into a dense vector (embedding) using an embedding layer.

For a vocabulary and embedding dimension 
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow><annotation encoding="application/x-tex"> d_{model} </annotation></semantics>
</math> 

$$  d_{model}  $$

(e.g., 512), each word is represented as a vector of length <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow><annotation encoding="application/x-tex"> d_{model} </annotation></semantics></math>.

Example: For "The", the embedding might be a 512-dimensional vector <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>1</mn></msub></mrow><annotation encoding="application/x-tex"> x_1 </annotation></semantics></math>, 

for "cat" <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>2</mn></msub></mrow><annotation encoding="application/x-tex"> x_2 </annotation></semantics></math>, and for "sleeps" <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>3</mn></msub></mrow><annotation encoding="application/x-tex"> x_3 </annotation></semantics></math>.

Result: An input matrix <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>X</mi><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><mi>n</mi><mo>×</mo><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> X \in \mathbb{R}^{n \times d_{model}} </annotation></semantics></math>, where <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>n</mi></mrow><annotation encoding="application/x-tex"> n </annotation></semantics></math> is the number of tokens (here, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>n</mi><mo>=</mo><mn>3</mn></mrow><annotation encoding="application/x-tex"> n = 3 </annotation></semantics></math>).




### Define Learnable Weight Matrices:

For self-attention, three weight matrices are defined to project the input embeddings into Query, Key, and Value vectors:

<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>Q</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mo>×</mo><msub><mi>d</mi><mi>k</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> W^Q \in \mathbb{R}^{d_{model} \times d_k} </annotation></semantics></math>: Weight matrix for Queries.
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>K</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mo>×</mo><msub><mi>d</mi><mi>k</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> W^K \in \mathbb{R}^{d_{model} \times d_k} </annotation></semantics></math>: Weight matrix for Keys.
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>V</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mo>×</mo><msub><mi>d</mi><mi>v</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> W^V \in \mathbb{R}^{d_{model} \times d_v} </annotation></semantics></math>: Weight matrix for Values.


Here, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>k</mi></msub></mrow><annotation encoding="application/x-tex"> d_k </annotation></semantics></math> and <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>v</mi></msub></mrow><annotation encoding="application/x-tex"> d_v </annotation></semantics></math> 
are the dimensions of the Query/Key and Value vectors, respectively (often <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><msub><mi>d</mi><mi>v</mi></msub><mo>=</mo><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mi mathvariant="normal">/</mi><mi>h</mi></mrow><annotation encoding="application/x-tex"> d_k = d_v = d_{model}/h </annotation></semantics></math> in multi-head attention, where <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>h</mi></mrow><annotation encoding="application/x-tex"> h </annotation></semantics></math> is the number of heads, but for simplicity, assume <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><msub><mi>d</mi><mi>v</mi></msub><mo>=</mo><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow><annotation encoding="application/x-tex"> d_k = d_v = d_{model} </annotation></semantics></math>).

These matrices are learned during training and are part of the model's parameters.


### Project Each Word’s Embedding into Q, K, V Vectors:

For each token’s embedding vector <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mi>i</mi></msub><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></msup></mrow><annotation encoding="application/x-tex"> x_i \in \mathbb{R}^{d_{model}} </annotation></semantics></math> (e.g., <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>1</mn></msub></mrow><annotation encoding="application/x-tex"> x_1 </annotation></semantics></math> for "The"):

Query Vector: Compute <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> q_i = x_i W^Q </annotation></semantics></math>.

This projects the embedding <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mi>i</mi></msub></mrow><annotation encoding="application/x-tex"> x_i </annotation></semantics></math> into a Query vector <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mi>i</mi></msub><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><msub><mi>d</mi><mi>k</mi></msub></msup></mrow><annotation encoding="application/x-tex"> q_i \in \mathbb{R}^{d_k} </annotation></semantics></math>.


Key Vector: Compute <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>k</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>K</mi></msup></mrow><annotation encoding="application/x-tex"> k_i = x_i W^K </annotation></semantics></math>.

This projects the embedding into a Key vector <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>k</mi><mi>i</mi></msub><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><msub><mi>d</mi><mi>k</mi></msub></msup></mrow><annotation encoding="application/x-tex"> k_i \in \mathbb{R}^{d_k} </annotation></semantics></math>.


Value Vector: Compute <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>v</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> v_i = x_i W^V </annotation></semantics></math>.

This projects the embedding into a Value vector <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>v</mi><mi>i</mi></msub><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><msub><mi>d</mi><mi>v</mi></msub></msup></mrow><annotation encoding="application/x-tex"> v_i \in \mathbb{R}^{d_v} </annotation></semantics></math>.




Mathematically, for the entire input matrix <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>X</mi></mrow><annotation encoding="application/x-tex"> X </annotation></semantics></math>:

Queries: <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>Q</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>Q</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><mi>n</mi><mo>×</mo><msub><mi>d</mi><mi>k</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> Q = X W^Q \in \mathbb{R}^{n \times d_k} </annotation></semantics></math>

Keys: 
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>K</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>K</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><mi>n</mi><mo>×</mo><msub><mi>d</mi><mi>k</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> K = X W^K \in \mathbb{R}^{n \times d_k} </annotation></semantics></math>

Values: 
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>V</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>V</mi></msup><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><mi>n</mi><mo>×</mo><msub><mi>d</mi><mi>v</mi></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> V = X W^V \in \mathbb{R}^{n \times d_v} </annotation></semantics></math>


Example: For the input string with <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>n</mi><mo>=</mo><mn>3</mn></mrow><annotation encoding="application/x-tex"> n = 3 </annotation></semantics></math>:

<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>Q</mi><mo>=</mo><mo stretchy="false">[</mo><msub><mi>q</mi><mn>1</mn></msub><mo separator="true">,</mo><msub><mi>q</mi><mn>2</mn></msub><mo separator="true">,</mo><msub><mi>q</mi><mn>3</mn></msub><mo stretchy="false">]</mo></mrow><annotation encoding="application/x-tex"> Q = [q_1, q_2, q_3] </annotation></semantics></math>, where <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mn>1</mn></msub></mrow><annotation encoding="application/x-tex"> q_1 </annotation></semantics></math> is the Query vector for "The", etc.

Similarly, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>K</mi><mo>=</mo><mo stretchy="false">[</mo><msub><mi>k</mi><mn>1</mn></msub><mo separator="true">,</mo><msub><mi>k</mi><mn>2</mn></msub><mo separator="true">,</mo><msub><mi>k</mi><mn>3</mn></msub><mo stretchy="false">]</mo></mrow><annotation encoding="application/x-tex"> K = [k_1, k_2, k_3] </annotation></semantics></math> and <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>V</mi><mo>=</mo><mo stretchy="false">[</mo><msub><mi>v</mi><mn>1</mn></msub><mo separator="true">,</mo><msub><mi>v</mi><mn>2</mn></msub><mo separator="true">,</mo><msub><mi>v</mi><mn>3</mn></msub><mo stretchy="false">]</mo></mrow><annotation encoding="application/x-tex"> V = [v_1, v_2, v_3] </annotation></semantics></math>.




### Intuition Behind Q, K, V:

Query (Q): Represents the "question" a token asks to find relevant other tokens in the sequence. It determines what information the token is looking for.

Key (K): Represents the "label" or "identifier" of each token, used to match with Queries to compute attention scores.

Value (V): Contains the actual content or information of the token, which is weighted by attention scores to produce the output.

The projections allow the model to learn different representations of the same input for computing attention (e.g., similarity between Queries and Keys).


Matrix Operations for Efficiency:

Instead of computing <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mi>i</mi></msub><mo separator="true">,</mo><msub><mi>k</mi><mi>i</mi></msub><mo separator="true">,</mo><msub><mi>v</mi><mi>i</mi></msub></mrow><annotation encoding="application/x-tex"> q_i, k_i, v_i </annotation></semantics></math> for each token individually, the projections are performed in a single matrix multiplication for the entire sequence:

Input embeddings:
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>X</mi><mo>=</mo><mo stretchy="false">[</mo><msub><mi>x</mi><mn>1</mn></msub><mo separator="true">;</mo><msub><mi>x</mi><mn>2</mn></msub><mo separator="true">;</mo><msub><mi>x</mi><mn>3</mn></msub><mo stretchy="false">]</mo><mo>∈</mo><msup><mi mathvariant="double-struck">R</mi><mrow><mn>3</mn><mo>×</mo><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow></msup></mrow><annotation encoding="application/x-tex"> X = [x_1; x_2; x_3] \in \mathbb{R}^{3 \times d_{model}} </annotation></semantics></math>.

Compute: 
<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>Q</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> Q = X W^Q </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>K</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>K</mi></msup></mrow><annotation encoding="application/x-tex"> K = X W^K </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>V</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> V = X W^V </annotation></semantics></math>.


This produces matrices <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>Q</mi><mo separator="true">,</mo><mi>K</mi><mo separator="true">,</mo><mi>V</mi></mrow><annotation encoding="application/x-tex"> Q, K, V </annotation></semantics></math>, where each row corresponds to the Q, K, V vectors for one token.


Example (Simplified):

Suppose <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mo>=</mo><mn>4</mn></mrow><annotation encoding="application/x-tex"> d_{model} = 4 </annotation></semantics></math>, and the embedding for "The" is <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>1</mn></msub><mo>=</mo><mo stretchy="false">[</mo><mn>0.1</mn><mo separator="true">,</mo><mn>0.2</mn><mo separator="true">,</mo><mn>0.3</mn><mo separator="true">,</mo><mn>0.4</mn><mo stretchy="false">]</mo></mrow><annotation encoding="application/x-tex"> x_1 = [0.1, 0.2, 0.3, 0.4] </annotation></semantics></math>.
Assume weight matrices (random for illustration):

<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>Q</mi></msup><mo>=</mo><mrow><mo fence="true">[</mo><mtable rowspacing="0.16em" columnalign="center center" columnspacing="1em"><mtr><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.1</mn></mstyle></mtd><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.2</mn></mstyle></mtd></mtr><mtr><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.3</mn></mstyle></mtd><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.4</mn></mstyle></mtd></mtr><mtr><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.5</mn></mstyle></mtd><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.6</mn></mstyle></mtd></mtr><mtr><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.7</mn></mstyle></mtd><mtd><mstyle scriptlevel="0" displaystyle="false"><mn>0.8</mn></mstyle></mtd></mtr></mtable><mo fence="true">]</mo></mrow></mrow><annotation encoding="application/x-tex"> W^Q = \begin{bmatrix} 0.1 &#x26; 0.2 \\ 0.3 &#x26; 0.4 \\ 0.5 &#x26; 0.6 \\ 0.7 &#x26; 0.8 \end{bmatrix} </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>K</mi></msup><mo>=</mo><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> W^K = W^Q </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>V</mi></msup><mo>=</mo><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> W^V = W^Q </annotation></semantics></math> (for simplicity, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><msub><mi>d</mi><mi>v</mi></msub><mo>=</mo><mn>2</mn></mrow><annotation encoding="application/x-tex"> d_k = d_v = 2 </annotation></semantics></math>).


Compute:

<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mn>1</mn></msub><mo>=</mo><msub><mi>x</mi><mn>1</mn></msub><msup><mi>W</mi><mi>Q</mi></msup><mo>=</mo><mo stretchy="false">[</mo><mn>0.1</mn><mo separator="true">,</mo><mn>0.2</mn><mo separator="true">,</mo><mn>0.3</mn><mo separator="true">,</mo><mn>0.4</mn><mo stretchy="false">]</mo><mo>⋅</mo><msup><mi>W</mi><mi>Q</mi></msup><mo>=</mo><mo stretchy="false">[</mo><mn>0.34</mn><mo separator="true">,</mo><mn>0.46</mn><mo stretchy="false">]</mo></mrow><annotation encoding="application/x-tex"> q_1 = x_1 W^Q = [0.1, 0.2, 0.3, 0.4] \cdot W^Q = [0.34, 0.46] </annotation></semantics></math>
Similarly compute <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>k</mi><mn>1</mn></msub></mrow><annotation encoding="application/x-tex"> k_1 </annotation></semantics></math> and <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>v</mi><mn>1</mn></msub></mrow><annotation encoding="application/x-tex"> v_1 </annotation></semantics></math>.


Repeat for "cat" (<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>2</mn></msub></mrow><annotation encoding="application/x-tex"> x_2 </annotation></semantics></math>) and "sleeps" (<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>x</mi><mn>3</mn></msub></mrow><annotation encoding="application/x-tex"> x_3 </annotation></semantics></math>).
In practice, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub></mrow><annotation encoding="application/x-tex"> d_{model} </annotation></semantics></math> is larger (e.g., 512), and weight matrices are learned to capture meaningful projections.


### Multi-Head Attention (Optional Context):

In Transformers, the above process is often done in multiple "heads," where <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>Q</mi></msup><mo separator="true">,</mo><msup><mi>W</mi><mi>K</mi></msup><mo separator="true">,</mo><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> W^Q, W^K, W^V </annotation></semantics></math> are split into smaller matrices for each head, and <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>d</mi><mi>k</mi></msub><mo>=</mo><msub><mi>d</mi><mi>v</mi></msub><mo>=</mo><msub><mi>d</mi><mrow><mi>m</mi><mi>o</mi><mi>d</mi><mi>e</mi><mi>l</mi></mrow></msub><mi mathvariant="normal">/</mi><mi>h</mi></mrow><annotation encoding="application/x-tex"> d_k = d_v = d_{model}/h </annotation></semantics></math>. 

Each head computes its own Q, K, V, allowing the model to capture different types of relationships.

However, the core projection process remains the same: linear transformations via matrix multiplication.



### Summary
To project an input string into Query, Key, and Value vectors for each word:

Tokenize the string into words (e.g., ["The", "cat", "sleeps"]).
Convert each word into an embedding vector, forming matrix <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>X</mi></mrow><annotation encoding="application/x-tex"> X </annotation></semantics></math>.
Use three learnable weight matrices <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msup><mi>W</mi><mi>Q</mi></msup><mo separator="true">,</mo><msup><mi>W</mi><mi>K</mi></msup><mo separator="true">,</mo><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> W^Q, W^K, W^V </annotation></semantics></math> to project each embedding:

<math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>q</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> q_i = x_i W^Q </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>k</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>K</mi></msup></mrow><annotation encoding="application/x-tex"> k_i = x_i W^K </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><msub><mi>v</mi><mi>i</mi></msub><mo>=</mo><msub><mi>x</mi><mi>i</mi></msub><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> v_i = x_i W^V </annotation></semantics></math>.


Compute all Q, K, V vectors efficiently via matrix multiplications: <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>Q</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>Q</mi></msup></mrow><annotation encoding="application/x-tex"> Q = X W^Q </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>K</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>K</mi></msup></mrow><annotation encoding="application/x-tex"> K = X W^K </annotation></semantics></math>, <math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mrow><mi>V</mi><mo>=</mo><mi>X</mi><msup><mi>W</mi><mi>V</mi></msup></mrow><annotation encoding="application/x-tex"> V = X W^V </annotation></semantics></math>.

These Q, K, V vectors are then used in the self-attention mechanism to compute attention scores and produce context-aware representations. If you’d like a deeper dive into the attention computation (e.g., scaled dot-product attention) or code examples (e.g., in Python/PyTorch), let me know!
