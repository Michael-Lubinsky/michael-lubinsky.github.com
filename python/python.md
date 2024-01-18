## Python notes

### Cosine similarity
First attempt
```
def cosine_distance(a, b):
    dot_product = sum(ai * bi for ai, bi in zip(a, b))
    magnitude_a = math.sqrt(sum(ai * ai for ai in a))
    magnitude_b = math.sqrt(sum(bi * bi for bi in b))
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    return 1 - cosine_similarity
```
More performant:
```
def cosine_distance(a, b):
    dot_product = 0
    magnitude_a = 0
    magnitude_b = 0
    for ai, bi in zip(a, b):
        dot_product += ai * bi
        magnitude_a += ai * ai
        magnitude_b += bi * bi
    cosine_similarity = dot_product / (magnitude_a * magnitude_b)
    return 1 - cosine_similarity
```
Cosine similarity with NumPy 
```
    def cosine_distance(vector1, vector2):
        dot_product = np.dot(vector1, vector2)
        norm_vector1 = np.linalg.norm(vector1)
        norm_vector2 = np.linalg.norm(vector2)
        cosine_similarity = dot_product / (norm_vector1 * norm_vector2)
        cosine_distance = 1 - cosine_similarity
        return cosine_distance
```

### import

### __init__

### pip

### SimPy discrete event simulation
https://simpy.readthedocs.io/en/latest/
