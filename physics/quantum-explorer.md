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
