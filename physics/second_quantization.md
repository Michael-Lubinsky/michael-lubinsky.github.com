## Second quantization 
is a formalism in quantum mechanics where **the number of particles is allowed to change**, and particles are treated as excitations of quantum states rather than as individually labeled objects.

Historically, the terminology is confusing:

* **First quantization**: quantize a classical particle.

  * Position (x) and momentum (p) become operators.
  * The wavefunction is (\psi(x)).

* **Second quantization**: quantize the wavefunction itself.

  * The wavefunction becomes an operator.
  * Particles can be created and destroyed.

Today physicists usually think of second quantization as the first step toward quantum field theory.

---

## Why do we need it?

Suppose you have three electrons.

In ordinary quantum mechanics you write

$$
\Psi(x_1,x_2,x_3)
$$

where (x_1,x_2,x_3) are coordinates of the three electrons.

For (N) particles:

$$
\Psi(x_1,\ldots,x_N)
$$

This becomes cumbersome when:

* (N) is very large ((10^{23}) electrons in a metal),
* particles are identical,
* particles can be created or annihilated.

Second quantization solves this elegantly.

---

## Main idea

Instead of tracking particles, we track **occupation numbers** of quantum states.

Suppose available states are:

$$
|1\rangle,\ |2\rangle,\ |3\rangle,\ldots
$$

A state of the system is described by

$$
|n_1,n_2,n_3,\ldots\rangle
$$

where (n_i) tells how many particles occupy state (i).

Example:

$$
|2,0,1,0,\ldots\rangle
$$

means:

* 2 particles in state 1,
* 0 particles in state 2,
* 1 particle in state 3.

---

## Creation operator

The creation operator

$$
a^\dagger_i
$$

adds a particle to state (i).

For bosons:

$$a^\dagger_i |n_i\rangle=\sqrt{n_i+1},|n_i+1\rangle$$

Example:

$$a^\dagger_3|2,0,1\rangle= \sqrt2,|2,0,2\rangle$$

One more particle appears in state 3.

---

## Annihilation operator

The annihilation operator

$$
a_i
$$

removes a particle.

$$
a_i |n_i\rangle=\sqrt{n_i},|n_i-1\rangle
$$

Example:

$$
a_1|2,0,1\rangle=\sqrt2,|1,0,1\rangle
$$

---

## Bosons

Bosons can share the same state.

Examples:

* photons
* phonons
* helium-4 atoms

Their operators satisfy

$$
[a_i,a_j^\dagger]=\delta_{ij}
$$

where

$$
[A,B]=AB-BA.
$$

---

## Fermions

Fermions obey the Pauli principle.

A state can contain only:

$$
n_i=0 \quad \text{or} \quad 1.
$$

Examples:

* electrons
* protons
* neutrons
* quarks

Operators satisfy anticommutation relations:

$$
{c_i,c_j^\dagger}=\delta_{ij}
$$

where

$$
{A,B}=AB+BA.
$$

This automatically enforces the Pauli exclusion principle.

---

## Example: electrons in an atom

Instead of writing

$$
\Psi(x_1,x_2,\ldots,x_N),
$$

we write

$$
|\text{occupation numbers}\rangle.
$$

For example:

$$
|1s\uparrow,,
1s\downarrow,,
2s\uparrow\rangle.
$$

The operators automatically handle exchange symmetry.

---

## Field operators

The next step is to define

$$
\hat{\psi}(\mathbf r)=\sum_i \phi_i(\mathbf r),a_i.
$$

This operator destroys a particle at position (\mathbf r).

Its adjoint

$$
\hat{\psi}^\dagger(\mathbf r)
$$

creates a particle at position (\mathbf r).

Now particles are viewed as excitations of a field.

This is the bridge to quantum field theory.

---

## Harmonic oscillator connection

The creation and annihilation operators first appear in the quantum harmonic oscillator:

$$
a^\dagger,\ a.
$$

There they raise and lower energy levels:

$$
|n\rangle
\to
|n+1\rangle.
$$

Second quantization generalizes this idea:

* one oscillator ↔ one quantum state,
* excitation number ↔ particle number.

A photon is literally one quantum of excitation of an electromagnetic field mode.

---

## Why condensed matter physicists love it

A crystal may contain

$$
10^{23}
$$

electrons.

Writing a giant wavefunction is impossible.

Using second quantization:

$$
H=\sum_k \epsilon_k,c_k^\dagger c_k
$$

describes the whole electron gas compactly.

Most of modern condensed matter theory—superconductivity, phonons, magnons, excitons, quantum Hall effect, topological matter—is written almost entirely in second-quantized language.

 The square root factor

$$
a^\dagger |n\rangle=
\sqrt{n+1},|n+1\rangle
$$

is not arbitrary. It is required so that the creation and annihilation operators satisfy the bosonic commutation relation

$$
[a,a^\dagger] = 1.
[a,a^\dagger]=1
$$

### Why can't we simply write

$$
a^\dagger |n\rangle = |n+1\rangle ?
$$

Suppose we tried

$$
a^\dagger |n\rangle = c_n |n+1\rangle,
$$

where (c_n) is some unknown coefficient.

Similarly,

$$
a |n\rangle = d_n |n-1\rangle.
$$

The coefficients must be chosen so that

$$
[a,a^\dagger]|n\rangle = |n\rangle.
$$

Solving this condition gives

$$
c_n=\sqrt{n+1},
\qquad
d_n=\sqrt{n}.
$$

Therefore

$$
a^\dagger |n\rangle=\sqrt{n+1},|n+1\rangle,
$$

$$
a |n\rangle=\sqrt{n},|n-1\rangle.
$$

### Physical interpretation

The probability amplitude for adding a boson to a state containing (n) bosons grows as

$$
\sqrt{n+1}.
$$

Therefore the probability itself grows as

$$
|\sqrt{n+1}|^2 = n+1.
$$

This is called **bosonic enhancement** or **stimulated emission**.

A boson prefers to enter a state that already contains bosons.

Examples:

* Laser photons
* Bose-Einstein condensates
* Phonons in a crystal

If a mode already contains (n) photons, emission into that mode is (n+1) times more likely than emission into an empty mode.

### Example

For (n=0):

$$
a^\dagger|0\rangle=|1\rangle.
$$

The coefficient is

$$
\sqrt{1}=1.
$$

For (n=3):

$$
a^\dagger|3\rangle=

2|4\rangle.
$$

because

$$
\sqrt{4}=2.
$$

The amplitude doubles, and the probability of creating another boson in that state is four times larger than for the vacuum.

### Connection to the harmonic oscillator

The same square roots appear in the quantum harmonic oscillator:

$$
a^\dagger|n\rangle=

\sqrt{n+1}|n+1\rangle,
$$

$$
a|n\rangle=\sqrt{n}|n-1\rangle.
]

Second quantization essentially treats each quantum state as a harmonic oscillator. The occupation number (n) becomes the oscillator's excitation number, which is why the same square-root factors appear.

