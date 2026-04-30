##  Code Review: Schrödinger Solver

  Overview

  A well-structured 1D quantum solver with a FastAPI backend and React frontend. The overall
  architecture is clean and the numerical methods are correctly implemented. Below are the
  issues found, ordered by severity.

  ---
##  Bug 1 (Critical): Wrong ARPACK which parameter — eigenvalue_solver.py:104

  eigenvalues, eigenvectors = eigsh(hamiltonian, k=k, which="SM")

  which='SM' finds eigenvalues with smallest magnitude (closest to zero). This is wrong for
  potentials with negative eigenvalues. The correct choice is which='SA' (Smallest Algebraic —
  most negative first).

  Impact: For finite_square_well (V = -10 inside), step_potential, and any potential with
  negative-energy bound states, ARPACK returns near-zero energy states (free-particle-like)
  instead of the actual bound states. The ground state at E ≈ -9.8 a.u. would be missed
  entirely. The test suite doesn't catch this because ISW and HO have all-positive eigenvalues
  where SM = SA.

  Fix:
  eigenvalues, eigenvectors = eigsh(hamiltonian, k=k, which="SA")

  ---
##  Bug 2 (Medium): URL state not preserved for time-evolution solve — App.tsx:124–138

  The pushUrlParams call in the evolve branch is missing several parameters:

  pushUrlParams({
    ...DEFAULTS,
    ...initialParams,   // uses stale initial params, not current solve params
    mode: 'time-evolution',
    potential: req.potential_preset ?? DEFAULTS.potential,
    // missing: initState, nSuperStates, coefficients, potentialParams
    ...
  })

  initState, nSuperStates, coefficients, and potentialParams (slider values) are never written
  to the URL after a solve. Shared links for superposition initial states or parametric
  potentials silently drop those parameters — the link reloads with defaults.

  ---
##  Bug 3 (Medium): Misleading field name in API response — app.py:127, 240

  class EvolveResponse(BaseModel):
      psi_frames: list[list[float]]   # actually stores |ψ|², not ψ

  app.py:240 computes prob_frames = (np.abs(result.psi_frames) ** 2).tolist() and assigns it to
  psi_frames. The field stores probability density |ψ(x,t)|², not the complex wavefunction. This
   trips up any future code that treats psi_frames as an amplitude (e.g., computing phases,
  interference, or re-running Crank-Nicolson from a saved frame).

  Fix: rename to prob_frames or density_frames throughout the API and frontend types/api.ts.

  ---
##  Issue 4 (Minor): saveEvery is invisible and immutable in the UI — ControlPanel.tsx:110

  const saveEvery = initialParams?.saveEvery ?? 10   // plain const, never state

  There's no UI control for save_every. It's set once from URL params and frozen. If the user
  changes n_steps drastically (e.g., to 10000) but save_every was 10, they'll get 1001 frames —
  potentially slow/large. Worse, the save_every > n_steps validation error from the backend
  would appear with no visible way for the user to fix it from the UI (they'd have to manually
  edit the URL).

  ---
  ## Issue 5 (Minor): Normalization uses psi**2 not |psi|**2 — eigenvalue_solver.py:120

  psi /= np.sqrt(np.sum(psi ** 2) * dx)

  This is correct only because ARPACK returns real eigenvectors for a real symmetric
  Hamiltonian. It would silently produce wrong normalization for a complex Hermitian H. The
  defensive form is:

  psi /= np.sqrt(np.sum(np.abs(psi) ** 2) * dx)

  Same issue applies on line 128.

  ---
 ## Issue 6 (Minor): Stale closure in animation useEffect — App.tsx:100

  }, [state.playing, state.currentFrame, state.evolveResult, state.speed])

  The interval is recreated every frame because state.currentFrame is in the deps. This is
  functionally correct (the interval captures the latest frame index) but creates unnecessary GC
   pressure — 60+ setInterval/clearInterval calls per second at 4x speed. Standard fix: use a
  ref for the frame counter inside the interval, or use useRef + requestAnimationFrame.

  ---
  ## Issue 7 (Low): __builtins__ override in potential_parser.py is not reliable —
  potential_parser.py:41

  aeval.symtable.update({"__builtins__": {}})

  In CPython, __builtins__ in a non-__main__ module is the builtins module object, not the dict.
   Setting it to {} may not suppress builtins depending on how asteval evaluates expressions
  internally. The real protection here is asteval's own AST-level restrictions. This line gives
  a false sense of additional security — remove it and rely on asteval's built-in sandboxing, or
   add a proper comment explaining it's belt-and-suspenders.

  ---
 ##  Test coverage gap

  The test suite covers ISW and HO validation well, but there are no tests for
  finite_square_well or step_potential eigenvalue correctness — the two presets where Bug 1
  would produce wrong results. Adding a test that checks the finite square well has at least one
   negative-energy bound state would have caught this.

  ---
  Summary

  ┌──────────┬───────┬──────┬──────┐
  │ Severity │                      Issue                      │         File         │ Line │
  ├──────────┼─────────────────────────────────────────────────┼──────────────────────┼──────┤
  │ Critical │ which='SM' misses negative-energy bound states  │ eigenvalue_solver.py │ 104  │
  ├──────────┼─────────────────────────────────────────────────┼──────────────────────┼──────┤
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Medium   │ URL state drops initState/superposition      │ App.tsx              │ 124    │
  │          │ params after solve                           │                      │        │
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Medium   │ psi_frames actually holds probability        │ app.py               │ 127,   │
  │          │ density |ψ|²                                 │                      │ 240    │
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Minor    │ saveEvery frozen from URL, no UI control     │ ControlPanel.tsx     │ 110    │
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Minor    │ psi**2 normalization assumes real            │ eigenvalue_solver.py │ 120,   │
  │          │ eigenvectors                                 │                      │ 128    │
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Minor    │ Animation useEffect recreates interval every │ App.tsx              │ 100    │
  │          │  frame                                       │                      │        │
  ├──────────┼──────────────────────────────────────────────┼──────────────────────┼────────┤
  │ Low      │ Unreliable __builtins__ override             │ potential_parser.py  │ 41     │
  └──────────┴──────────────────────────────────────────────┴──────────────────────┴────────┘

  The which='SM' → which='SA' fix is one line and should be done immediately — it makes
  finite_square_well and step_potential return physically meaningless results for their primary
  use case (bound states).

  finite_square_well and step_potential return physically meaningless results for their primary
  use case (bound states).

  │ Low      │ Unreliable __builtins__ override             │ potential_parser.py  │ 41     │
  └──────────┴──────────────────────────────────────────────┴──────────────────────┴────────┘

  The which='SM' → which='SA' fix is one line and should be done immediately — it makes
  finite_square_well and step_potential return physically meaningless results for their primary
  use case (bound states).
