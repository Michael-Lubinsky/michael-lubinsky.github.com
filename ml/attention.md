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
