## Physics projects


## 💡 Solo Project Ideas

### Quantum Mechanics

**1. Interactive Schrödinger Equation Solver with Modern UI**
A web-based tool (FastAPI + React or Datastar/HTMX, given your recent interest) that lets users draw arbitrary 1D/2D potentials and solve the time-dependent or time-independent Schrödinger equation numerically — with real-time animation. NumPy/SciPy for the numerics, rendered via canvas or WebGL. The gap here is that most existing solvers are Jupyter notebooks or CLI tools. A polished, shareable web app would be genuinely useful for students and educators.

**2. Tight-Binding Model Explorer**
A Python library + interactive dashboard for building and visualizing tight-binding Hamiltonians on arbitrary lattices (square, honeycomb, kagome, etc.). Computes band structures, density of states, Berry curvature, and Chern numbers. You'd leverage PySpark/Dask for parameter sweeps across thousands of configurations (think materials screening). Nothing in this space has great UX — most are research scripts.

**3. Quantum Circuit ↔ Physics Hamiltonian Translator**
A tool that lets you express a condensed matter Hamiltonian (e.g., Heisenberg, Hubbard, transverse-field Ising) and automatically maps it to a quantum circuit for execution on Qiskit/Cirq simulators, then compares results with classical exact diagonalization. Useful for researchers prototyping variational quantum eigensolver (VQE) experiments.

---

### Solid State Physics

**4. Band Structure + Fermi Surface Visualizer (ML-accelerated)**
Wrap an existing DFT code (GPAW or ASE) with a Python backend that caches results in a vector store and uses an ML surrogate model to interpolate band structures for nearby crystal structures — dramatically reducing compute. Your MLOps background is directly applicable here. The output: a web app where materials scientists can explore band structures interactively.

**5. Phonon Dispersion + Thermal Properties Pipeline**
Using ASE (Atomic Simulation Environment) + Phonopy, build an automated pipeline that takes a crystal structure file (CIF), computes force constants via finite differences, and produces phonon dispersion curves, heat capacity, and thermal conductivity — packaged as a CLI tool + REST API. Your pipeline architecture experience maps directly.

---

### Spintronics

**6. Macrospin LLG Simulator with Python-native API**
The Landau–Lifshitz–Gilbert (LLG) equation governs magnetization dynamics. Packages like `cmtj` exist for macrospin analysis of multilayer spintronic devices, but the APIs are often MATLAB-era style. A clean, modern Python library using JAX (for auto-differentiation and GPU acceleration via Apple MPS, which you've explored) that solves the stochastic LLG equation would be very useful for spintronics researchers running parameter sweeps on MTJ devices.

**7. Spin Hall & Anomalous Hall Effect Calculator**
A tool that takes Wannier90 output (tight-binding model from DFT) and computes spin Hall conductivity, anomalous Hall conductivity, and spin Berry curvature tensor across the Brillouin zone using the Kubo formula — parallelized with Dask or Ray. Currently this requires stitching together multiple research codes.

---

## 🤝 Existing Projects to Contribute To

| Project | Domain | Why it fits you |
|---|---|---|
| **[QuTiP](https://github.com/qutip/qutip)** | Quantum optics / open systems | QuTiP simulates the dynamics of open quantum systems and is used in quantum optics, trapped ions, superconducting circuits, and nanomechanical resonators. Active community, needs performance, docs, and GPU acceleration work. |
| **[mumax³](https://mumax.github.io/)** | Micromagnetics / spintronics | GPU-accelerated micromagnetic simulation achieving ~100x speedups even with inexpensive gaming GPUs. Could benefit from Python interface improvements and MLX/Apple GPU support. |
| **[ASE (Atomic Simulation Environment)](https://gitlab.com/ase/ase)** | Solid state / DFT | Huge Python codebase, good first-issues, you could contribute workflow/pipeline tooling. |
| **[Quantify](https://gitlab.com/quantify-os/quantify-core)** | Solid state experiments | A data acquisition platform focused on quantum computing and solid-state physics experiments. Your data pipeline expertise is directly applicable. |
| **[scqubits](https://github.com/scqubits/scqubits)** | Superconducting qubits | Simulates superconducting qubits, obtains energy spectra, and plots energy levels. Actively maintained, Python-native, good documentation culture. |
| **[SPIRIT](https://github.com/spirit-code/spirit)** | Spin dynamics / spintronics | Atomistic spin dynamics for skyrmions and spin waves. C++ core with Python bindings — your C++ interest (LLVM, LevelDB) maps well. |
| **[Ubermag](https://github.com/ubermag/workshop)** | Micromagnetics | A Python interface wrapping OOMMF and mumax3 for spintronics simulations, actively developed, very welcoming to contributors. |

---

## My Top Recommendation for You Specifically

Given your ML infrastructure angle, the **Band Structure + ML Surrogate** project (#4) or contributing to **Quantify** is the most differentiated path — you'd be one of the very few people bringing production data pipeline thinking into a field that desperately needs it. The physics community is full of brilliant scientists writing research-quality Python scripts; what's missing is someone who knows how to build *infrastructure* around those scripts.
