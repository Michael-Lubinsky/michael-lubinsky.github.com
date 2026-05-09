## Quantum Explorer. 
TODO:
  - README behind of implemented features
  - Top level URL https://mlubinsky.github.io/quantum-explorer/ does not reflect current button
  - Line "Exact analytical quantum mechanics — no backend, no approximations" is useless
  -  it is better to have individual line per button just below with shrodinger equation;
  -  for hydrogen atom move the line with equation to the top
 -   for free particle button move Schrödinger equation:
Coulomb potential (a.u.)  to top line instead of current location
   


## ChatGPT review:

 
### Specific issues in **Stationary States**:

1. **Harmonic oscillator matrix panel uses the wrong x-grid**

In `StationaryExplorer`, `gridX` is always created as:

```ts
const dx = L / (N_POINTS - 1)
const gridX = Array.from({ length: N_POINTS }, (_, i) => i * dx)
```

This is correct for the infinite square well, but **wrong for harmonic oscillator**, whose eigenfunctions are generated on a symmetric grid `[-xMax, xMax]`. Then `MatrixPanel` receives HO wavefunctions on one grid but `gridX/dx` from `[0, L]`, so HO `X` and `P` matrix elements are wrong. ([GitHub][1])

Fix: get `x` and `dx` from the generated eigenstate:

```ts
const states = Array.from({ length: N_LEVELS }, (_, i) =>
  hoEigenstate(i, omega, N_POINTS)
)

const gridX = states[0].x
const dx = gridX[1] - gridX[0]
const wavefunctions = states.map(s => s.psi)
```

2. **HO momentum distribution formula has wrong normalization for `ω ≠ 1`**

Current code says:

```ts
|φₙ(k; ω)|² = |ψₙ(k; 1/ω)|²
```

and implements:

```ts
const psi = hoWavefunction(n, k, 1 / omega)
return psi * psi
```

But the correct scaling needs an extra factor:

```ts
|φ_n(k;ω)|² = (1/ω) |ψ_n(k/ω; 1/ω)|²
```

Without this, the momentum distribution is not normalized correctly and `σ_p` will be wrong for `ω ≠ 1`. ([GitHub][2])

3. **`P` matrix animation is conceptually wrong**

`MatrixPanel` stores only `Im⟨m|p|n⟩`, but `heisenbergRe()` treats the input as a real matrix and multiplies by `cos((Em-En)t)`. For a purely imaginary operator matrix element, the real part evolves with a **sine**, not cosine. So animated `P(t)` is wrong. ([GitHub][3])

4. **Infinite well momentum amplitude pole sign is simplified incorrectly**

In `iswMomentumAmplitude()`, the pole case says:

```ts
// sign depends on which branch; use +i for simplicity
```

That is dangerous because time-evolved superpositions depend on relative complex phases. This can make momentum-space interference wrong in time evolution. ([GitHub][2])

5. **README/App overclaim “no approximations”**

The stationary feature uses finite grids for plotting and matrix elements, and `P` uses finite-difference derivatives. That is normal and useful, but the app text says “no approximations.” Better wording: **“Analytical formulas with numerical visualization/matrix-element evaluation where needed.”** ([GitHub][4])

Highest-priority fix: fix the **HO grid passed into `MatrixPanel`**, because it directly makes displayed matrix elements incorrect.

[1]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/components/StationaryExplorer.tsx "raw.githubusercontent.com"
[2]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/physics/momentumSpace.ts "raw.githubusercontent.com"
[3]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/components/MatrixPanel.tsx "raw.githubusercontent.com"
[4]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/App.tsx "raw.githubusercontent.com"

## Time Evolution
Yes — specific issues in **Time Evolution**:

1. **Re(ψ) / Im(ψ) buttons do not work for HO modes**

The UI always shows:

```ts
prob | re | im
```

but `hoData` and `hoSqData` only compute `yProb`, not `yPsi`. So for **HO Coherent** and **HO Squeezed**, selecting `Re(ψ)` or `Im(ψ)` cannot show the actual wavefunction phase. Either hide these buttons for HO modes, or implement complex HO wavefunctions. ([GitHub][1])

2. **Squeezed state notation is misleading**

The UI/help says squeezed state is:

```text
S(r)|α⟩
```

but the code evolves the center exactly like an unsqueezed coherent state:

```ts
hoCoherentExpectX(...)
hoCoherentExpectP(...)
```

That corresponds more naturally to a **displaced squeezed state** like:

```text
D(α)S(r)|0⟩
```

not necessarily `S(r)|α⟩`. This is a physics-label issue, but important for students. ([GitHub][1])

3. **Energy decomposition for squeezed state is wrong**

For both `ho` and `ho-sq`, `decompData` uses the same Poisson distribution based only on `alpha`:

```ts
exp(-alpha²) alpha^(2n) / n!
```

That is correct for coherent states, but **not** for squeezed states. Squeezed states have a different number-state distribution depending on `r`. ([GitHub][1])

4. **Momentum distribution for ISW has a pole-sign bug**

`iswMomentumAmplitude()` says:

```ts
sign depends on which branch; use +i for simplicity
```

For a time-evolving superposition, this relative phase matters. The probability `|φ(k,t)|²` can be wrong near `k = ±nπ/L`. ([GitHub][2])

5. **Norm history is not actually computed**

The norm plot is hardcoded as a flat line at `1.0`. That is okay for an analytical demo, but the label “Norm history” makes it look like the app numerically checked normalization. Better label:

```text
Analytic norm = 1
```

or actually integrate the plotted grid. ([GitHub][1])

6. **History can mix different parameter regimes**

`histRef` is appended whenever `t`, `subMode`, `L`, `alpha`, `omega`, `r`, etc. change, but it is not clearly reset when all physical parameters change. So expectation-value history can contain old values after parameter edits. Add reset effects for mode and parameter changes. ([GitHub][1])

Highest-priority fixes:

```ts
// Hide Re/Im buttons for HO modes
{subMode === 'isw' && displayModeButtons}
```

and fix squeezed-state energy decomposition; currently that is the most serious physics issue.

[1]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/components/TimeEvolutionExplorer.tsx "raw.githubusercontent.com"
[2]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/physics/momentumSpace.ts "raw.githubusercontent.com"


1. **Hydrogen 2D orbital density bug at origin**
   `orbitalDensity2D()` returns `0` when `r < 1e-12`, but for `s` orbitals, especially `1s`, density at `r=0` is **maximum**, not zero. Fix similarly to `orbitalDensity3D()`: return finite value for `l === 0`. ([GitHub][1])

2. **README overclaims “no approximations”**
   README says “no approximations” and “every feature uses exact analytical solution,” but `iswExpectX2()` explicitly computes an integral numerically on a 400-point grid. This is fine educationally, but README should say “mostly analytical; some visualization/expectation plots use numerical quadrature.” ([GitHub][2])

3. **Scattering wavefunction inside barrier is likely approximate / phase-inconsistent**
   `scatteringPsiSq()` claims exact stationary wavefunction, but the evanescent inside coefficients use real `sqrtT` and discard the complex transmission phase. This can make inside-barrier density visually wrong or discontinuous near boundaries. ([GitHub][3])

4. **Potential numerical overflow in tunnelling**
   For thick/high barriers, `Math.sinh(kappaTilde * L)` and `Math.exp(kappa * half)` can overflow. Transmission can become `0`, but inside wavefunction plotting may become `Infinity`/`NaN`. Add clamping or log-domain handling. ([GitHub][3])

5. **No CI quality gates before deploy**
   GitHub Actions runs only `npm ci` and `npm run build`; it does **not** run `npm run typecheck`, `npm run lint`, or `npm run test`, even though these scripts exist. Add them before build. ([GitHub][4]) ([GitHub][5])

Suggested deploy change:

```yaml
- run: npm ci
- run: npm run typecheck
- run: npm run lint
- run: npm run test
- run: npm run build
  env:
    VITE_BASE: /quantum-explorer/
```

6. **Minor UI issue**
   `ParameterSlider` always shows `value.toFixed(2)`. For quantum numbers or integer-like parameters this can look strange, e.g. `n = 3.00`. Add optional `digits` prop. ([GitHub][6])

Overall: the project structure is good, and the separation of physics formulas from React UI is a strong design choice. The highest-priority fixes are hydrogen density at origin, README accuracy, and adding test/lint/typecheck to CI.


## Specific issues in **Spin 1/2 Bloch Sphere: Precession, Measurements, Bell**:

1. **Bell simulation repeats the same “random” result**
   In `simulatePairs()`, the LCG seed is reset every call:

```ts
let seed = 0x12345678
```

So pressing “Run simulation” again with same θ and N gives the same counts. That is bad for an educational “random measurement” demo. Use `Math.random()` or pass seed as optional parameter. ([GitHub][1])

2. **Precession sign convention should be documented**
   `rodriguezRotate()` rotates using `axis × r`. For spin in magnetic field, the direction depends on Hamiltonian convention:

```ts
H = -(ω0/2) σ·B
```

versus

```ts
H = +(ω0/2) σ·B
```

Your code is fine mathematically, but the UI/help should explicitly state which sign convention is used. Otherwise students may compare with textbooks and think direction is wrong. ([GitHub][2])

3. **Measurement panel does not show measurement axis on Bloch sphere**
   `BlochSphere` supports `measureAxis?: Vec3`, but `SpinExplorer` does not appear to pass the currently selected Stern–Gerlach axis into it. That means the student chooses x/y/z/custom, but the sphere does not visually show the analyzer axis. This is a missed teaching opportunity. ([GitHub][3])

4. **N-shot measurement after collapse may confuse students**
   In `SternGerlachPanel`, “Measure once” collapses the parent state. Then “Run N shots” uses the current collapsed state, not the original state, unless the user locked a prep state. This is physically defensible, but pedagogically confusing. Rename buttons:

```text
Measure once and collapse current state
Run N shots from current state without collapse
Lock prepared state for repeated trials
```

5. **Bell CHSH angles are limited to one plane**
   This is okay for CHSH, but label it as “coplanar analyzer angles.” Otherwise students may think Bell tests only involve 2D angle settings.

6. **README is outdated**
   README says Bell states are “Planned,” but the repo now has `BellDemo.tsx`, `BellInfoPanel.tsx`, and `physics/bell.ts`. Update README feature list. The repo file list confirms Bell files exist. ([GitHub][4])

Highest priority fixes:

```ts
// physics/bell.ts
export function simulatePairs(theta: number, n: number, rng = Math.random) {
  ...
  if (rng() < pOpposite) oppositePairs++
}
```

And pass measurement axis into the sphere, possibly by lifting `axisPreset/customTheta/customPhi` state from `SternGerlachPanel` into `SpinExplorer`.


## Free Particle
Yes. I see a few issues.

1. **Main bug: Re(ψ) / Im(ψ) are not exact**

`fpProb()` is correct for the probability density, but `fpRePsi()` / `fpImPsi()` use an “approximate carrier”:

```ts
phase = k0 * (x - x0) - k0 * k0 * t / 2
```

This misses the quadratic chirp phase created by free-particle spreading. So the app says “Exact Gaussian wavepacket solution,” but Re/Im plots are only approximate. ([GitHub][1])

2. **x-grid is wrong for negative k₀**

```ts
const xLeft = x0 - 4 * sigma0
const xRight = x0 + Math.max(Math.abs(k0) * tMax, 1) + 4 * sigmaFinal
```

For `k0 < 0`, the packet moves left, but the grid does not extend left enough. Use center positions at both start and end:

```ts
const c0 = x0
const c1 = x0 + k0 * tMax
const xLeft = Math.min(c0, c1) - 4 * sigmaFinal
const xRight = Math.max(c0, c1) + 4 * sigmaFinal
```

Current code is at `makeProbGrid()`. ([GitHub][1])

3. **Changing x₀ or k₀ does not reset time/history**

You reset only when `sigma0` changes. If user changes `x0` or `k0`, the history plot mixes old and new parameter regimes. Reset should depend on all physical parameters:

```ts
useEffect(() => {
  setT(0)
  setPlaying(false)
  histRef.current = []
}, [x0, k0, sigma0])
```

Current reset is only `[sigma0]`. ([GitHub][1])

4. **History is updated after every render**

This effect has no dependency array:

```ts
useEffect(() => {
  histRef.current.push(...)
})
```

It can add duplicate points when unrelated state changes, e.g. opening help or toggling sections. Use `[t, expectX, deltaX, uxp]`. ([GitHub][1])

5. **Norm history is misleading**

It always plots `1.0`, not computed normalization. That is okay as a statement of theory, but the label “history” can mislead users into thinking the app verified the plotted finite grid. Better label: **“Analytic norm = 1”**.


## Scattering

Yes — specifically in **Scattering / Tunnelling**, I see several important issues.

1. **`scatteringPsiSq()` is not really exact**

The comment says:

```ts
Exact stationary scattering wavefunction |ψ(x)|²
```

but the implementation contains approximations / phase hacks. For example, near `E ≈ V0`, inside the barrier it simply returns:

```ts
return transmissionT(E, V0, L)
```

That makes `|ψ|²` constant inside the barrier, which is not the correct linear-solution limit. ([GitHub][1])

2. **Evanescent inside-barrier wavefunction is wrong**

For `E < V0`, the code assumes real coefficients:

```ts
const { ARe, BRe } = insideCoeffsEvanescent(...)
const val = ARe * exp(kappa*x) + BRe * exp(-kappa*x)
return val * val
```

But the real stationary scattering solution generally has **complex** coefficients inside the barrier. Using only real coefficients loses phase information and can produce wrong density inside the barrier. ([GitHub][1])

3. **Reflection amplitude phase is suspicious**

The code computes `r`, then rescales it to force the magnitude:

```ts
const scale = rCalcSq > 1e-14 ? rMag / Math.sqrt(rCalcSq) : 1
return { rRe: rRe * scale, rIm: rIm * scale, tRe, tIm }
```

That may preserve `R = |r|²`, but it does not guarantee the correct phase. Since the left-side interference pattern depends on the phase of `r`, `|ψ(x)|²` on the incident side can be shifted incorrectly. ([GitHub][1])

4. **Possible overflow for thick/high barriers**

This can overflow:

```ts
Math.sinh(kappaTilde * L)
Math.cosh(kappaTilde * L)
Math.exp(kappaTilde * x)
```

For large `V0`, large `L`, or small `E`, this can create `Infinity`, `NaN`, or a broken plot. ([GitHub][1])

5. **WKB comparison is visually misleading near/above barrier**

`wkbT()` returns `1` for `E >= V0`, but WKB tunnelling formula is only meaningful below the barrier. The UI currently hides it above the barrier with `null`, which is good, but the function itself is mathematically misleading as a reusable API. Better:

```ts
export function wkbT(E: number, V0: number, L: number): number | null {
  if (E >= V0) return null
  const kappa = Math.sqrt(2 * (V0 - E))
  return Math.exp(-2 * kappa * L)
}
```

6. **Spatial plot range depends only on external wavelength**

```ts
const xL = -half - 6 / k
const xR = half + 6 / k
```

For very low `E`, this becomes huge; for high `E`, it may show too little interference structure. A better UI would let the user choose plot width or use a bounded adaptive range. ([GitHub][2])

Most important fix: rewrite `scatteringPsiSq()` using one consistent complex-number solution for `r`, `t`, `A`, and `B`, then verify continuity of both `ψ` and `ψ'` at `x = ±L/2`.

[1]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/physics/tunnelling.ts "quantum-explorer/src/physics/tunnelling.ts at main · mlubinsky/quantum-explorer · GitHub"
[2]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/components/TunnellingExplorer.tsx "quantum-explorer/src/components/TunnellingExplorer.tsx at main · mlubinsky/quantum-explorer · GitHub"




[1]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/components/FreeParticleExplorer.tsx "quantum-explorer/src/components/FreeParticleExplorer.tsx at main · mlubinsky/quantum-explorer · GitHub"





[1]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/physics/bell.ts "quantum-explorer/src/physics/bell.ts at main · mlubinsky/quantum-explorer · GitHub"
[2]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/utils/spinMath.ts "quantum-explorer/src/utils/spinMath.ts at main · mlubinsky/quantum-explorer · GitHub"
[3]: https://github.com/mlubinsky/quantum-explorer/raw/refs/heads/main/src/components/BlochSphere.tsx "raw.githubusercontent.com"
[4]: https://github.com/mlubinsky/quantum-explorer/tree/main/src/components "quantum-explorer/src/components at main · mlubinsky/quantum-explorer · GitHub"



[1]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/physics/hydrogen.ts "raw.githubusercontent.com"
[2]: https://github.com/mlubinsky/quantum-explorer "GitHub - mlubinsky/quantum-explorer · GitHub"
[3]: https://raw.githubusercontent.com/mlubinsky/quantum-explorer/main/src/physics/tunnelling.ts "raw.githubusercontent.com"
[4]: https://github.com/mlubinsky/quantum-explorer/blob/main/package.json "quantum-explorer/package.json at main · mlubinsky/quantum-explorer · GitHub"
[5]: https://github.com/mlubinsky/quantum-explorer/blob/main/.github/workflows/deploy.yml "quantum-explorer/.github/workflows/deploy.yml at main · mlubinsky/quantum-explorer · GitHub"
[6]: https://github.com/mlubinsky/quantum-explorer/blob/main/src/components/ParameterSlider.tsx "quantum-explorer/src/components/ParameterSlider.tsx at main · mlubinsky/quantum-explorer · GitHub"


## TODO

Almost all of the proposed features can be implemented fully in-browser with modern JavaScript/TypeScript.

Your current architecture (React + TypeScript + browser-only numerical computation) is actually a very good fit for educational QM simulations.

The main limitation is not “can it run in browser,” but:

* numerical grid size,
* animation FPS,
* memory,
* GPU usage,
* complexity of PDE solvers.

Here is a realistic breakdown.

---

# EASY TO IMPLEMENT FULLY IN BROWSER

These are very suitable for pure browser execution.

---

## 1. Double Slit / Interference

YES — absolutely.

### Typical implementation

* 2D complex grid
* Split-step Fourier method
* FFT in browser

### Browser tech

* ndarray
* fft.js
* gpu.js
* WebGL canvas

### Complexity

Medium

### Browser performance

Very good for:

```text
256×256
512×512
```

even on laptops.

---

# 2. Density Matrix + Decoherence

YES — ideal for browser.

These are tiny matrices:

* 2×2
* 4×4
* maybe 8×8

Computational cost is negligible.

### Can easily support

* Lindblad evolution
* Kraus channels
* entropy
* purity
* Bloch shrinkage

### Performance

Instantaneous.

---

# 3. Entanglement Explorer

YES.

Even:

* 2 qubits
* 3 qubits
* small Hilbert spaces

are tiny computationally.

### Browser can easily handle:

```text
2^10 = 1024 amplitudes
```

without issue.

---

# 4. Fourier Transform Explorer

YES.

Browser FFT libraries are mature.

### Excellent fit for:

* live dragging
* uncertainty demos
* momentum-space visualization

---

# 5. Wigner Function

YES.

For 1D states:

* entirely feasible
* very visually impressive

### Complexity

Mostly FFTs and matrix transforms.

### Browser performance

Good for:

```text
128×128
256×256
```

phase-space grids.

---

# 6. Quantum Gates / Quantum Circuits

YES.

This is trivial computationally for small qubit counts.

You can even support:

* small circuit simulator
* tensor products
* gate animations

fully client-side.

---

# 7. Berry Phase

YES.

Computationally tiny.

---

# 8. Path Integral Visualization

YES.

Monte Carlo path sampling works well in browser.

Could even use Web Workers for smooth animation.

---

# MEDIUM DIFFICULTY BUT STILL GOOD IN BROWSER

---

# 9. 2D Schrödinger Solver

YES — but careful.

This is probably the largest feature still realistically browser-only.

### Feasible:

* 256×256 grids
* split-step FFT
* finite differences

### Potential issues

* mobile devices
* battery
* FPS

### Solution

Use:

* WebGL
* GPU.js
* WebGPU
* OffscreenCanvas
* Web Workers

### Very realistic today.

Modern browsers are surprisingly powerful.

---

# 10. Time-dependent Potentials

YES.

Examples:

* moving barrier
* oscillating well
* driven oscillator

Still browser-feasible.

---

# BORDERLINE / NEED OPTIMIZATION

---

# 11. Large-scale Many-body Systems

NOT ideal browser-only.

Examples:

* exact diagonalization of large spin chains
* large Hilbert spaces
* many-electron systems

Hilbert space grows exponentially.

### Example

```text
20 qubits = 1,048,576 amplitudes
```

Already heavy.

---

# 12. Advanced 3D PDE Solvers

Possible but difficult.

Examples:

* full 3D time-dependent Schrödinger equation
* fine volumetric grids

Memory explodes quickly.

### Example

```text
256^3 ≈ 16 million voxels
```

Too heavy for casual browser execution.

---

# 13. Relativistic Dirac 3D Solver

Possible in theory,
but not ideal browser-only.

---

# WHAT MODERN BROWSERS CAN ACTUALLY HANDLE

Modern browsers + WebGL/WebGPU are much stronger than many people expect.

Reasonable browser-only targets:

| Feature                  | Browser Feasible? |
| ------------------------ | ----------------- |
| Bloch sphere             | Excellent         |
| Bell states              | Excellent         |
| Density matrices         | Excellent         |
| Wigner functions         | Excellent         |
| 1D TDSE                  | Excellent         |
| 2D TDSE                  | Good              |
| Double slit              | Excellent         |
| Decoherence              | Excellent         |
| Quantum circuits (small) | Excellent         |
| Path integrals           | Good              |
| 3D orbitals              | Good              |
| Large many-body          | Poor              |

---

# IMPORTANT ARCHITECTURAL SUGGESTION

Your current architecture is already good.

But for future advanced features, consider adding:

---

# 1. Web Workers

Move heavy numerics off UI thread.

Perfect for:

* FFT
* PDE stepping
* Monte Carlo

This prevents UI freezing.

---

# 2. Typed Arrays

Use:

```ts
Float64Array
Float32Array
```

instead of nested JS arrays.

Huge speedup.

---

# 3. Complex Number Struct Optimization

Avoid:

```ts
{re: x, im: y}
```

inside large grids.

Instead:

```ts
re[] and im[]
```

Much faster.

---

# 4. WebGL / WebGPU

Very important for:

* 2D wave evolution
* Wigner
* volumetric plots

---

# 5. WASM (optional future)

For:

* FFT
* LAPACK
* sparse solvers

Possible stack:

* Rust → WASM
* C++ → WASM
* Eigen
* FFTW

But not immediately necessary.

---

# MY STRONGEST RECOMMENDATION

For your project specifically:

## Best fully-browser-only next features:

### 1. Double slit

### 2. Density matrix + decoherence

### 3. Wigner function

### 4. Fourier transform explorer

### 5. 2D TDSE


Your project already covers a surprisingly broad range for a QM learning tool. The strongest differentiator is that it combines:

* stationary states
* time evolution
* Bloch sphere / spin
* hydrogen orbitals
* Bell physics

inside one consistent browser application.

The best next features are the ones that:

1. deepen conceptual understanding,
2. produce visually distinctive demos,
3. are still feasible for a solo project.

Here are the highest-value additions grouped by difficulty.

---

# HIGH VALUE / LOW-MEDIUM DIFFICULTY

## 1. Double-Slit + Interference Simulator

This is probably the single most important missing QM visualization.

### Features

* Gaussian packet incident on two slits
* Time evolution after slit passage
* Interference buildup
* Which-path detector toggle
* Partial decoherence slider

### Why valuable

Students immediately connect:

* wavefunction
* probability
* measurement
* decoherence

### Strong extension

Add:

* delayed-choice experiment
* quantum eraser

### Difficulty

Medium

### Visual value

Extremely high

---

# 2. Density Matrix + Decoherence Explorer

Currently your Bloch sphere mostly uses pure states.

Add:

* density matrix ρ
* purity Tr(ρ²)
* mixed states inside Bloch sphere
* dephasing
* amplitude damping
* depolarization channels

### Visuals

* Bloch vector shrinking
* purity gauge
* entropy display

### Educational impact

Huge.

Most QM educational tools completely skip open quantum systems.

### Difficulty

Medium

---

# 3. Quantum Measurement Explorer

A dedicated module for:

* projective measurement
* POVMs
* repeated measurement
* weak measurement

### Features

* collapse animation
* expectation value before/after
* non-commuting observables
* measurement disturbance

### Nice demo

Measure:

* σx then σz
* compare to σz then σx

### Difficulty

Medium

---

# 4. Entanglement Explorer

You already have Bell.

Extend to:

* arbitrary 2-qubit states
* Schmidt decomposition
* concurrence
* partial trace
* reduced density matrices

### Visuals

* correlation matrix heatmap
* entanglement entropy
* separable vs entangled states

### Difficulty

Medium-high

### Very valuable for students.

---

# 5. Interactive Fourier Transform Explorer

This naturally connects:

* x-space
* momentum-space
* uncertainty principle

### Features

* draggable wavepacket
* live Fourier transform
* phase visualization
* chirped packet
* windowing effects

### Difficulty

Low-medium

---

# HIGH VALUE / HIGHER DIFFICULTY

## 6. 2D Schrödinger Equation Solver

This would dramatically elevate the project.

### Examples

* double slit
* 2D harmonic oscillator
* finite well
* tunneling through barriers

### Numerical methods

* split-step Fourier
* Crank–Nicolson ADI

### Visuals

* animated 2D density maps
* phase coloring

### Difficulty

High

### But:

This would make the project much more unique than existing educational tools.

---

# 7. Path Integral Visualization

Very few educational apps do this well.

### Features

* sum over paths
* classical limit emergence
* phase cancellation

### Amazing demo

Show:

* many random paths
* constructive/destructive interference

### Difficulty

High conceptually
Medium numerically

### Huge educational value.

---

# 8. Quantum Computing Bridge

Since you already have Bloch sphere:

Add:

* Hadamard
* phase gates
* CNOT
* simple circuits

### Then:

show the actual statevector evolution.

### Bonus

Export OpenQASM or Qiskit.

### Difficulty

Medium-high

---

# VERY DISTINCTIVE / UNIQUE FEATURES

These could make your project stand out from almost every open-source QM visualizer.

---

## 9. Wigner Function Visualization

For:

* coherent states
* squeezed states
* cat states

### Visual

Quasi-probability with negative regions.

### Educational value

Extremely high.

### Difficulty

Medium-high

---

# 10. Adiabatic Theorem / Landau-Zener Explorer

Show:

* slowly changing Hamiltonian
* avoided crossings
* transition probabilities

### Visuals

* instantaneous eigenstates
* state tracking

### Excellent for advanced students.

---

# 11. Berry Phase / Geometric Phase

Since you already have Bloch sphere:
this is a natural extension.

### Show

* cyclic evolution
* geometric phase accumulation

### Very visually compelling.

---

# 12. Relativistic QM / Dirac Spinors

Long-term ambitious feature.

### Examples

* Zitterbewegung
* Klein paradox
* spinor rotations

### Difficulty

Very high

But almost nobody has this in browser educational tools.

---

# INFRASTRUCTURE / QUALITY FEATURES

These are not flashy, but would greatly improve the project.

---

## 13. Formula Derivation Panel

For every visualization:

* “Show derivation”
* expandable math steps

This would transform the project from demo → learning platform.

---

# 14. Preset Scenarios

Example:

* coherent state
* minimum uncertainty packet
* Rabi oscillation
* Bell singlet
* tunneling resonance

One-click loading helps beginners enormously.

---

# 15. Save/Share URLs

Encode state in URL:

```text
?mode=bell&theta=45&n=1000
```

Very useful for teaching.

---

# 16. Phase Coloring

Instead of only density:
display:

* complex phase hue
* magnitude brightness

This dramatically improves understanding of complex wavefunctions.

---

# 17. Interactive Eigenstate Builder

Allow:

```text
ψ = Σ c_n φ_n
```

with draggable complex coefficients.

### Then animate:

* revival
* beating
* interference

Very educational.

---

# 18. GPU/WebGL Acceleration

For:

* 2D evolution
* large grids
* many particles

Potential stack:

* regl
* three.js
* WebGPU

---

# MOST STRATEGIC FEATURES

If your goal is to make the project genuinely notable/open-source-popular:

## Best ROI:

1. Double slit
2. Decoherence / density matrix
3. Wigner function
4. 2D solver
5. Interactive Fourier transform

These would clearly differentiate the project from:

* PhET
* QMsolve
* typical Bloch demos

because they connect foundational QM ideas into one coherent system.


These are:

* feasible,
* visually impressive,
* educationally deep,
* differentiating,
* performant in browser.

