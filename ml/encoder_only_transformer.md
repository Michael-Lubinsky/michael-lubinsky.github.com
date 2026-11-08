## Encoder-only Transformer 
An encoder-only transformer is the left half of the original "Attention Is All You Need" architecture, used alone. It takes a whole sequence and turns it into contextual vectors, one per token. It does **not** generate text one token at a time. BERT is the classic example.

## The key difference: no causal mask

In your notes, the GPT-style section uses a causal mask so each token can only see earlier tokens. An encoder drops that mask, so every token attends to **every** token, both left and right:

$$
\text{Attention}(Q,K,V)=\text{softmax}\left(\frac{QK^T}{\sqrt{d_k}} + M\right)V
$$

- **Decoder (GPT):** M has −∞ above the diagonal, so token i sees tokens 1…i.
- **Encoder (BERT):** M = 0 everywhere, except −∞ on padding columns. Token i sees the whole sentence.

So in "The bank of the river", the vector for "bank" is computed with "river" already in view. That makes it better at *understanding* text, and the price is that it can't generate text left to right.

## Architecture

```
tokens → token embedding + position embedding (+ segment embedding in BERT)
       → [ bidirectional multi-head self-attention → Add & Norm
           → FFN → Add & Norm ] × N
       → hidden states H ∈ ℝ^(n × d_model)   (one vector per token)
```

There's no cross-attention and no autoregressive loop. One forward pass gives you all n output vectors at once.

## How it's trained: masked language modeling (MLM)

Next-token prediction would be trivial here, because the model can see the next token. So BERT hides tokens instead:

1. Pick about 15% of the positions.
2. For those positions, replace the token with `[MASK]` 80% of the time, with a random token 10% of the time, and leave it unchanged 10% of the time.
3. Predict the original tokens at those positions only:

$$
L = -\sum_{i \in \mathcal{M}} \log P(x_i \mid x_{\setminus \mathcal{M}})
$$

Compare this with your causal loss $-\sum_i \log P(x_i \mid x_{<i})$. Here the context is everything *except* the masked tokens, from both sides. One cost is that only about 15% of tokens produce a training signal, compared with 100% in causal LM.

Variations on this:
- **Next Sentence Prediction:** original BERT only. RoBERTa showed it wasn't needed.
- **ELECTRA's replaced-token detection:** a small generator swaps in plausible tokens, and the encoder classifies every token as real or replaced. Every position gives a training signal, so it's more sample-efficient.

## How you use the output

The encoder gives you a matrix H. What you do with it depends on the task:

| Task | What you take from H | Head on top |
|---|---|---|
| Sentence classification (sentiment, intent) | `h_[CLS]` or the mean of H | Linear → softmax over classes |
| Token classification (NER, POS tagging) | every $h_i$ | Linear per token |
| Extractive QA (SQuAD) | every $h_i$ | Two linear layers that score start and end positions |
| Embeddings / semantic search | mean-pooled H (masked), normalized | none; compare with cosine similarity |
| Reranking (cross-encoder) | `h_[CLS]` of "[query] [SEP] [doc]" | Linear → relevance score |

The embeddings row is the link to the RAG section of your notes. The "embedding model" in a RAG pipeline is almost always an encoder-only transformer fine-tuned with a contrastive loss, so that queries and the passages that answer them end up close together. Examples are Sentence-BERT, E5, BGE and GTE. That's why your notes describe CLS and mean pooling: those are the two standard ways to turn an encoder's n token vectors into one vector.

## Encoder vs decoder vs encoder-decoder

| | Encoder-only | Decoder-only | Encoder-decoder |
|---|---|---|---|
| Attention | bidirectional | causal | bidirectional encoder + causal decoder + cross-attention |
| Pretraining | MLM / replaced-token detection | next-token prediction | span corruption / denoising |
| Output | one vector per input token | next-token distribution | generated sequence |
| Good at | classification, NER, retrieval, reranking | generation, chat, reasoning | translation, summarization |
| Examples | BERT, RoBERTa, DeBERTa, ELECTRA, ModernBERT | GPT, LLaMA, Claude | T5, BART |

## Why use one when LLMs can do everything

- **Cost and speed:** A 100M–400M-parameter encoder classifies or embeds text in one forward pass, with no decoding loop. That's orders of magnitude cheaper than prompting an LLM, which matters when you're processing millions of rows, e.g. in a Databricks pipeline.
- **Better per-token representations:** Each token is conditioned on both sides, which helps with NER, span extraction and embeddings.
- **Fine-tuning is simple:** Add a linear head and train on a few thousand labeled examples.

The limitations:
- It can't generate free text.
- The context length is usually short (512 tokens for classic BERT; ModernBERT extends it to 8k).
- `[MASK]` never appears at inference time, which is a mismatch between pretraining and fine-tuning. That's part of why the 80/10/10 trick exists.

## Minimal PyTorch sketch

The only change from your notes' self-attention code is that there's no causal mask. There's just a padding mask:

```python
import torch, torch.nn as nn

class EncoderClassifier(nn.Module):
    def __init__(self, vocab, d_model=256, n_heads=4, n_layers=4, n_classes=2, max_len=512):
        super().__init__()
        self.tok = nn.Embedding(vocab, d_model)
        self.pos = nn.Embedding(max_len, d_model)
        layer = nn.TransformerEncoderLayer(d_model, n_heads, 4*d_model,
                                           batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, n_layers)
        self.head = nn.Linear(d_model, n_classes)

    def forward(self, ids, pad_id=0):
        pos = torch.arange(ids.size(1), device=ids.device)
        x = self.tok(ids) + self.pos(pos)
        pad_mask = ids == pad_id                      # True = ignore this key
        h = self.encoder(x, src_key_padding_mask=pad_mask)   # bidirectional
        keep = (~pad_mask).unsqueeze(-1).float()
        pooled = (h * keep).sum(1) / keep.sum(1)      # masked mean pooling
        return self.head(pooled)
```

This also fixes the issue in your notes' PyTorch example: there, sequences padded with `0` attend to the padding tokens because no mask is applied.

I can also write a short version of this as a new section for `attention.md` that matches the notation you use there.
