## Fourier Transform

## Fourier Series vs. Fourier Transform

They're two sides of the same coin — the Fourier Transform is essentially the **generalization of the Fourier Series to non-periodic functions**.

---

### Fourier Series (Periodic Functions)

For a function $f(x)$ that is **periodic** with period $L$, you decompose it into a discrete sum of harmonics:

$$f(x) = \sum_{n=-\infty}^{\infty} c_n \, e^{i \frac{2\pi n}{L} x}$$

where the coefficients are:

$$c_n = \frac{1}{L} \int_{0}^{L} f(x)\, e^{-i \frac{2\pi n}{L} x} \, dx$$

The frequencies present are **discrete**: $\nu_n = n/L$ for integer $n$.

---

### Fourier Transform (Aperiodic Functions)

For a function $f(x)$ that is **not periodic** (defined on all of $\mathbb{R}$), you get a **continuous spectrum**:

$$\hat{f}(\xi) = \int_{-\infty}^{\infty} f(x)\, e^{-i 2\pi \xi x} \, dx$$

with reconstruction:

$$f(x) = \int_{-\infty}^{\infty} \hat{f}(\xi)\, e^{i 2\pi \xi x} \, d\xi$$

---

### The Key Limiting Argument

The connection is clean: take a Fourier Series and let the period $L \to \infty$. Then:

- The discrete frequencies $\xi_n = n/L$ become **dense** in $\mathbb{R}$
- The spacing $\Delta\xi = 1/L \to d\xi$ becomes a continuous differential
- The sum $\sum_n c_n \, e^{i 2\pi \xi_n x}$ becomes the **integral** of the Fourier Transform
- The coefficients $c_n = \hat{f}(\xi_n)/L$ become $\hat{f}(\xi)\, d\xi$

So the Fourier Transform is just the Fourier Series **in the limit of infinite period**.

---

### Summary Table

| Property | Fourier Series | Fourier Transform |
|---|---|---|
| Domain of $f$ | Periodic, period $L$ | Aperiodic, all of $\mathbb{R}$ |
| Frequency spectrum | **Discrete** ($n/L$) | **Continuous** ($\xi \in \mathbb{R}$) |
| Representation | Sum $\sum c_n e^{i\omega_n x}$ | Integral $\int \hat{f}(\xi) e^{i2\pi\xi x} d\xi$ |
| "Coefficients" | $c_n$ (a sequence) | $\hat{f}(\xi)$ (a function) |
| Limiting relation | Base case | $L \to \infty$ limit |

---

### One More Unifying View

In the language of groups and harmonic analysis, both are instances of the same idea:

- Fourier Series = harmonic analysis on the **circle group** $\mathbb{T} = \mathbb{R}/L\mathbb{Z}$ (compact), giving a **discrete** dual group $\mathbb{Z}$
- Fourier Transform = harmonic analysis on $\mathbb{R}$ (locally compact), giving a **continuous** dual group $\mathbb{R}$

This is Pontryagin duality — the deeper reason they're the same phenomenon.

<https://www.youtube.com/watch?v=08mmKNLQVHU>

<https://www.youtube.com/watch?v=9bqrTYCS6DQ>

<https://www.youtube.com/playlist?list=PLB24BC7956EE040CD>

The Unreasonable Effectiveness of the Fourier Transform
<https://joshuawise.com/resources/ofdm/>

<https://news.ycombinator.com/item?id=45132810>  Fourier Transform 

### DFT
Дискретное преобразование Фурье 

<https://www.youtube.com/watch?v=h7apO7q16V0>

<https://nima101.github.io/dft>

<https://connorboyle.io/2025/09/11/fft-cooley-tukey.html>

<https://www.byhand.ai/p/28-discrete-fourier-transform>

### Fouroer Series

<img width="1440" height="1800" alt="image" src="https://github.com/user-attachments/assets/4731109a-63a6-41ec-ab2a-f9e42c7a7cf9" />

<img width="1440" height="1800" alt="image" src="https://github.com/user-attachments/assets/5376d1c8-dd77-4556-8482-95f3a2288ebc" />

<img width="1440" height="1800" alt="image" src="https://github.com/user-attachments/assets/e203fd85-7459-4ff2-831e-d04fac825b4f" />

<img width="1440" height="1800" alt="image" src="https://github.com/user-attachments/assets/00c9cbe3-90e9-43a1-b040-5bbdbeb19121" />


