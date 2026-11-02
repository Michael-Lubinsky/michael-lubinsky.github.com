### The Metropolis–Hastings algorithm and the Viterbi algorithm 
are both methods for inference in probabilistic models, but they solve fundamentally different problems.


### Viterbi

https://en.wikipedia.org/wiki/Viterbi_algorithm
Goal: найти наиболее правдоподобный путь в скрытой марковской цепи

Viterbi Beam Search

- Metropolis–Hastings (MH) is a stochastic sampling algorithm. It generates samples from a probability distribution.
- Viterbi is a dynamic programming algorithm. It finds the single most probable sequence of hidden states in a Hidden Markov Model (HMM).

Their connection is that both can operate on the same probabilistic model, but answer different questions.

## 1. Mathematical comparison

Suppose we have a Hidden Markov Model with hidden states

$$Z=(z_1,z_2,\ldots,z_T)$$

and observations

$$X=(x_1,x_2,\ldots,x_T)$$

We want to infer the hidden states given the observations.

The posterior distribution is

$$P(Z\mid X)\propto P(X\mid Z)P(Z)$$

Both algorithms can use this distribution.

### Viterbi: Find the most probable sequence

Viterbi computes

$$\boxed{Z^\*=\arg\max_Z P(Z\mid X)}$$

This is called maximum a posteriori (MAP) sequence estimation.

The result is one optimal sequence.

### Metropolis–Hastings: Sample possible sequences

MH instead constructs a Markov chain whose stationary distribution is

$$\boxed{\pi(Z)=P(Z\mid X)}.$$

It repeatedly proposes changes to the current sequence and accepts or rejects them according to

$$\alpha(Z,Z') = \min\left( 1, \frac{P(Z'\mid X)q(Z\mid Z')} {P(Z\mid X)q(Z'\mid Z)} \right)$$

After convergence, the generated sequences approximate samples from the posterior.

## 2. A simple example

Imagine a person moving between two locations:

- H = Home
- W = Work

We observe their phone's GPS signals over four time steps, but the observations are noisy.

There are \\(2^4=16\\) possible hidden-state sequences.

Suppose the posterior assigns the following probabilities to some of them:

Illustrative posterior probabilities

<img width="662" height="395" alt="image" src="https://github.com/user-attachments/assets/e51d0a78-3f7f-41a8-a12d-ddb5b0307a06" />


The other 12 sequences have a combined probability of 0.20.

Viterbi returns:

`H → H → W → W`

because that is the most probable complete sequence, with probability 0.40.

Metropolis–Hastings generates many sequences. For example, among 10,000 samples after convergence, we would expect approximately 4,000 copies of `H H W W`, 2,500 of `H W W W`, and so on.

This provides information about uncertainty that Viterbi does not provide.

## 3. How the algorithms work internally

Viterbi: Computes the optimal path using dynamic programming.

Metropolis–Hastings: Explores possible states through random proposals.

<img width="669" height="442" alt="image" src="https://github.com/user-attachments/assets/765784a4-6a7b-480e-a5b2-e54dd69bf7e0" />

### Viterbi recurrence

For an HMM, let

- \\(a\_{ij}=P(z_t=j\mid z\_{t-1}=i)\\)
- \\(b_j(x_t)=P(x_t\mid z_t=j)\\)

Define \\(\delta_t(j)\\) as the highest joint probability of any path ending at state \\(j\\) at time \\(t\\).

Then

$$\delta_t(j)=b_j(x_t)\max_i\left[\delta\_{t-1}(i)a\_{ij}\right]$$

By storing which previous state achieves each maximum and backtracking, Viterbi recovers the optimal path.

For \\(T\\) observations and \\(K\\) hidden states, its computational complexity is

\\[ O(TK^2). \\]

### Metropolis–Hastings iteration

A simple MH algorithm for the same HMM could be:

1. Start with a candidate hidden-state sequence \\(Z\\).
2. Randomly choose a time step \\(t\\).
3. Propose replacing \\(z_t\\) with another state.
4. Compute the acceptance probability.
5. Accept or reject the proposal.
6. Repeat.

For a symmetric proposal changing one state, most probability factors cancel. The acceptance ratio depends only on the emission probability at \\(t\\) and the adjacent transition probabilities.

This makes each local MH proposal potentially inexpensive, although many iterations may be needed for adequate mixing.

## 4. Important conceptual difference

| Property             | Viterbi                                            | Metropolis–Hastings                    |
| -------------------- | -------------------------------------------------- | -------------------------------------- |
| Main objective       | Find most probable sequence                        | Sample from posterior                  |
| Method               | Dynamic programming                                | Markov chain Monte Carlo               |
| Randomness           | Deterministic, given tie-breaking                  | Stochastic                             |
| Output               | One optimal sequence                               | Many samples                           |
| Exactness            | Exact MAP for standard finite-state HMMs           | Approximate sampling after convergence |
| Uncertainty          | Does not directly quantify it                      | Can estimate posterior uncertainty     |
| Applicable models    | Models with suitable dynamic-programming structure | Broad class of distributions           |
| Convergence concerns | None for finite HMM                                | Burn-in, mixing, autocorrelation       |

## 5. There is a third algorithm worth comparing: Forward–Backward

For Hidden Markov Models, three different inference questions naturally arise.

| Question                                                              | Algorithm                                                                                              |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| What is the most probable complete hidden-state sequence?             | Viterbi                                                                                                |
| What is the probability of each hidden state at each time?            | Forward–Backward                                                                                       |
| How can we sample possible hidden-state sequences from the posterior? | Metropolis–Hastings, or preferably exact forward-filtering backward-sampling for a standard finite HMM |

Forward–Backward uses sums over possible paths, whereas Viterbi uses maxima.

This is an important mathematical relationship:

\\[ \underbrace{\max}\_{\text{Viterbi}} \qquad\text{versus}\qquad \underbrace{\sum}\_{\text{Forward–Backward}} \\]

Both exploit the HMM's Markov structure.

Metropolis–Hastings takes a different approach: rather than systematically summing or maximizing over paths, it explores the posterior through random transitions.

## 6. Can they be combined?

Yes. For example, in a complex HMM with unknown transition probabilities:

- Use Metropolis–Hastings to sample model parameters from their posterior.
- For each sampled parameter set, run Viterbi to obtain the most probable state sequence conditional on those parameters.
- Examine how the optimal sequence changes as the parameters vary.

However, these conditional Viterbi paths are not themselves posterior samples of the hidden-state sequence. For that, one should sample the hidden states conditionally as well.

## 7. Which should you study first?

Given your interest in implementing probabilistic and causal algorithms from scratch in Python, I would suggest the following progression:

1. Implement Viterbi for a two-state HMM.
2. Implement Forward–Backward for the same HMM.
3. Implement Metropolis–Hastings to sample complete hidden-state sequences.
4. Compare the exact posterior probabilities with empirical frequencies from MH.
5. Investigate how MH mixing deteriorates as the sequence length increases.

This is a particularly instructive experiment because the exact HMM algorithms provide a reference against which you can verify your MCMC implementation.

The central distinction: Viterbi solves an optimization problem; Metropolis–Hastings solves a sampling problem. They can operate on the same posterior distribution, but they are not interchangeable.
