##  Current solver is 1-D only. How difficult it would be to make 2-D solver and add 2-D
  potential to the app and visualize it?


❯ what is pedagogical value of 2-D solver?

⏺ Honestly, not much beyond what 1D already teaches.

  What 1D already covers completely

  - Quantization of energy levels
  - Wavefunctions, probability densities, normalization
  - Tunneling, superposition, time evolution
  - Expectation values, uncertainty principle
  - All the standard potentials (HO, square well, double well, barriers)

  These are the core QM concepts. A student learns all of them from 1D.

  ## What 2D genuinely adds

  Degeneracy — the most valuable addition. A 2D square box has states (n,m) and (m,n) with
  identical energies. Students can see that degenerate states can be mixed arbitrarily, and that
   any linear combination is also an eigenstate. This is hard to motivate in 1D.

  Angular momentum — a 2D circular well produces states with definite angular momentum quantum
  number. Students see why the hydrogen atom wavefunctions have the shapes they do.

  Symmetry breaking — slightly break the 2D square well (make it rectangular) and watch
  degenerate states split. Connects to perturbation theory.

  The honest assessment

  Most undergraduate QM courses never need a 2D solver. The concepts above are better taught
  analytically, and a 1D solver with good potentials covers everything on a typical syllabus.

  2D becomes valuable in a computational physics course where students are learning numerical
  methods themselves — the Kronecker product Hamiltonian, sparse solvers, and visualization are
  the lesson, not the physics.

  Better use of the same effort

  If the goal is pedagogical value, these 1D additions would teach more than going to 2D:

  - Perturbation theory panel — show E_n^(1) = ⟨n|V'|n⟩ alongside the numerical result
  - WKB approximation overlay — compare semiclassical to exact for smooth potentials
  - Time-dependent potential — drive the system with an oscillating field, show resonance
  - Scattering coefficients — compute T and R for barrier potentials, plot vs energy

  Each of those stays 1D, is fast to compute, and directly connects to topics students are
  simultaneously learning analytically.


##  Perturbation theory panel - what it would show

  The app already computes exact numerical eigenvalues for any potential. The idea is to split
  the potential into a known base H₀ and a small perturbation V′, compute the first-order
  correction analytically from the already-computed eigenstates, then display both alongside the
   exact numerical answer:
```
  ┌───────┬──────────────────┬─────────────────┬──────────────┬────────────────────┬───────┐
  │ State │      E_n        │   E_n^(1) =     │  E_n (1st    │    E_n (exact      │ Error  │
  │       │  (unperturbed)  │    ⟨n|V′|n⟩     │    order)    │     numerical)     │        │
  ├───────┼─────────────────┼─────────────────┼──────────────┼────────────────────┼────────┤
  │ n=1   │ 4.935           │ 0.333           │ 5.268        │ 5.271              │ 0.06%  │
  ├───────┼─────────────────┼─────────────────┼──────────────┼────────────────────┼────────┤
  │ n=2   │ 19.739          │ 0.333           │ 20.072       │ 20.075             │ 0.01%  │
  ├───────┼─────────────────┼─────────────────┼──────────────┼────────────────────┼────────┤
  │ n=3   │ 44.413          │ 0.333           │ 44.746       │ 44.748             │ 0.004% │
  └───────┴─────────────────┴─────────────────┴──────────────┴────────────────────┴────────┘
```
  The student sees perturbation theory working — or failing when the perturbation is too large.

  ---
  Concrete example: ISW + small constant bump

  Base potential: infinite square well, V₀ = 0.
  Perturbation: V′ = ε·x² (turning it slightly toward a harmonic oscillator).

  First-order correction:
  E_n^(1) = ⟨ψ_n | εx² | ψ_n⟩ = ε ∫ |ψ_n(x)|² x² dx

  This integral is already computed — it's just expect_x2 from expectation_values.py, evaluated
  on the unperturbed eigenstates. No new numerics needed.

  The exact answer is obtained by running the solver on H₀ + V′ directly. The panel compares the
   two.

  ---
  What makes it pedagogically powerful

  Students learn perturbation theory by writing down the formula, but rarely get to see it work
  or fail. This panel makes three things concrete:

  1. When it works well
  Small ε, non-degenerate states, smooth perturbation → first-order is excellent. Students see
  the error column shrink as ε → 0. The formula isn't just a derivation step — it's a genuinely
  accurate prediction.

  2. When it breaks down
  Increase ε until first-order is noticeably wrong. Students discover the regime boundary
  themselves rather than being told "assume V′ is small."

  3. Degenerate perturbation theory
  Use a 2D-like situation: two states with nearly equal energies. First-order fails badly — the
  corrected energies are wrong. This motivates why degenerate PT needs a separate treatment.

  ---
  Implementation

  The computation is almost free — the unperturbed eigenstates are already available from the
  solve.

  Backend: one new function:

  def first_order_corrections(
      wavefunctions: np.ndarray,   # unperturbed eigenstates (k, N)
      V_prime: np.ndarray,         # perturbation on grid (N,)
      dx: float,
  ) -> np.ndarray:                 # shape (k,)
      # E_n^(1) = ∫ |ψ_n|² V′ dx
      return np.array([
          np.sum(np.abs(psi)**2 * V_prime) * dx
          for psi in wavefunctions
      ])

  That's it. The integral is a dot product — a few microseconds.

  The user workflow:

  1. User picks a base potential (e.g. ISW) and solves → gets unperturbed energies and
  wavefunctions
  2. User adds a perturbation expression in a new "Perturbation V′" input field
  3. Panel computes E_n^(1) instantly (no second solve needed)
  4. User optionally clicks "Solve perturbed H" to get the exact answer for comparison
  5. Table shows all three: E_n⁰, E_n⁰ + E_n^(1), E_n (exact)

  The "Solve perturbed H" step is already implemented — it's just a normal eigensolve on H₀ +
  V′.

  ---
  What the student learns that's hard to get from a textbook

  - The correction is just an expectation value — not some abstract formula but a concrete
  integral of a known function. Seeing ⟨x²⟩ appear as the correction for an x² perturbation
  makes the formula intuitive.
  - Accuracy depends on level spacing — perturbing a state whose nearest neighbor is far away
  gives a very accurate first-order correction. Perturbing near a degeneracy fails visibly. The
  error column makes this self-evident.
  - Second-order corrections can be added later: E_n^(2) = Σ_{m≠n} |⟨m|V′|n⟩|² / (E_n⁰ - E_m⁰).
  The off-diagonal matrix elements ⟨m|V′|n⟩ are also just dot products of already-computed
  wavefunctions.

  ---
  Estimated effort
```
  ┌───────────────────────────────────────┬────────┐
  │                 Piece                 │ Effort │
  ├───────────────────────────────────────┼───────────┤
  │ perturbation.py backend function      │ 1 hour    │
  ├───────────────────────────────────────┼───────────┤
  │ New API field in EigensolveResponse   │ 30 min    │
  ├───────────────────────────────────────┼───────────┤
  │ Perturbation V′ input in ControlPanel │ 1 hour    │
  ├───────────────────────────────────────┼───────────┤
  │ PerturbationPanel table component     │ 2–3 hours │
  ├───────────────────────────────────────┼───────────┤
  │ Tests                                 │ 2 hours   │
  └───────────────────────────────────────┴───────────┘
```
  Total: about 1 day. The heaviest part is the UI table, not the numerics — the math is already
  done by the eigenvalue solver.




##  Bottom line: 2D is a better fit for a computational physics showcase than a QM teaching tool.
  For JOSS, the 1D solver with strong validation and documentation will be more useful to more
  courses.
  

⏺ This is a significant but tractable extension. Here's the honest breakdown:

  Backend difficulty: Medium

  What's already designed for it:
  - grid.py already returns a shape tuple — that was explicitly future-proofed for 2D
  - eigsh and Crank-Nicolson are dimension-agnostic (they just need a sparse matrix)
  - potential_parser.py only needs y added to ALLOWED_SYMBOLS

  What needs new work:

  Hamiltonian (easiest part): 2D H is a Kronecker product:
  H = T_x ⊗ I_y  +  I_x ⊗ T_y  +  V(x,y)
  For a 100×100 grid that's a 10,000×10,000 sparse matrix with a 5-point stencil. SciPy's kron
  handles this in ~5 lines.

  Performance (the real problem): An N×N grid produces an N²×N² matrix. Full LU factorization
  (what splu does for Crank-Nicolson) on a 10k×10k matrix is slow — maybe 10–30 seconds per
  solve instead of milliseconds. The fix is operator splitting (ADI — Alternating Direction
  Implicit): apply CN in x, then CN in y, each 1D solve per step. Still O(N²) per step but with
  the same tridiagonal speed as 1D.

  Initial states: 2D Gaussian is straightforward. Superposition still works since eigenstates
  are just 2D arrays reshaped to 1D for the matrix.

  Frontend difficulty: Medium

  What changes:
  - |ψ(x,y)|² displays as a Plotly Heatmap or Surface trace instead of a line — not much code
  - The potential V(x,y) also becomes a heatmap
  - Animation frames are now 2D arrays — payload goes from ~4 KB/frame to ~80 KB/frame for a
  100×100 grid, so the precompute-all-frames approach stays reasonable for short runs but caps
  out sooner

  What's tricky:
  - The control panel needs a "2D mode" toggle and a way to enter expressions in x and y
  - Colorscale choice matters a lot for readability of wavefunctions
  - The exact solution panel and matrix panel would need 2D analogues or graceful disabling

  Summary estimate
```
  ┌────────────────────────────┬───────────┐
  │           Piece            │  Effort   │
  ├────────────────────────────┼───────────┤
  │ 2D Grid class              │ 1 hour    │
  ├────────────────────────────┼───────────┤
  │ 2D Hamiltonian (Kronecker) │ 2 hours   │
  ├────────────────────────────┼───────────┤
  │ ADI Crank-Nicolson         │ 1–2 days  │
  ├────────────────────────────┼───────────┤
  │ Eigenvalue solver          │ no change │
  ├────────────────────────────┼───────────┤
  │ API request/response types │ half day  │
  ├────────────────────────────┼───────────┤
  │ Potential parser (add y)   │ 30 min    │
  ├────────────────────────────┼───────────┤
  │ Frontend heatmap plots     │ 1 day     │
  ├────────────────────────────┼───────────┤
  │ UI controls for 2D mode    │ 1 day     │
  ├────────────────────────────┼───────────┤
  │ Tests                      │ 1 day     │
  └────────────────────────────┴───────────┘
```
  Rough total: 1–2 weeks for a solid MVP that matches the current 1D quality. The ADI time
  stepper is the most technically demanding piece — the rest is mechanical.

  The biggest risk is payload size: 1000 frames × 100×100 grid = 10M floats as JSON is ~80 MB.
  You'd likely need to either cap resolution (50×50), reduce saved frames, or switch to binary
  transport (numpy over streaming) before making it feel fast.

  Recommendation: Start with stationary states only (eigenstates of 2D H) — that's ~3 days of
  work and already visually compelling (2D harmonic oscillator, 2D square well, coupled double
  well). Add time evolution after.
