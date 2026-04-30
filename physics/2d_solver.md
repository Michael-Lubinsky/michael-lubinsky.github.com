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

  What 2D genuinely adds

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

  Bottom line: 2D is a better fit for a computational physics showcase than a QM teaching tool.
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
