**LightFM** is a **Python library** for building **hybrid recommendation systems**. It combines:

- **Collaborative filtering** (e.g., matrix factorization)
- **Content-based filtering** (e.g., user and item metadata)
- Into one **flexible model** using **latent factor models** and **stochastic gradient descent**.

---

## 🔍 Key Features of LightFM

| Feature | Description |
|--------|-------------|
| ✅ **Hybrid modeling** | Uses both interaction data and metadata (user/item features) |
| 🧠 **Latent factor model** | Learns embeddings for users and items |
| ⚙️ **Loss functions** | Supports **ranking** (e.g., BPR), **classification** (e.g., logistic), and **regression** |
| 🚀 **Fast** | Optimized Cython backend, fast for moderate-scale datasets |
| 🧩 **Flexible input** | Accepts sparse matrices (e.g., CSR) for interactions and features |

---

## 📦 Installation

```bash
pip install lightfm
