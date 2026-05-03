## QM Software

https://github.com/euphoricrhino/sakurai-notes

https://github.com/osscar-org/quantum-mechanics

https://github.com/mholtrop/QMPython

https://github.com/mkuznets/quantum-mechanics-lectures

https://github.com/kirsion/Quantum-Mechanics-Mcintyre-solutions

 
### Primary Project
- **QM (mlubinsky/QM)**: [https://github.com/mlubinsky/QM](https://github.com/mlubinsky/QM) (the one you asked to review)

### Key Comparables

- **QMsolve**: [https://github.com/quantum-visualizations/qmsolve](https://github.com/quantum-visualizations/qmsolve) — Python library for 1D/2D/3D Schrödinger solving and visualization.

- **Schrodinger Equation Simulator (web-based 1D TDSE)**: [http://www.schrodingerequation.online/](http://www.schrodingerequation.online/)  
  GitHub: [https://github.com/marekyggdrasil/Schroedinger](https://github.com/marekyggdrasil/Schroedinger) (related/mentioned implementation)

### Other Notable Ones

- **PhET Interactive Simulations** (Quantum Wave Interference, Quantum Tunneling, Models of the Hydrogen Atom, etc.):  
  Main site: [https://phet.colorado.edu/](https://phet.colorado.edu/)  
  Source code: [https://github.com/phetsims](https://github.com/phetsims) (multiple repos)

- **QuTiP** (Quantum Toolbox in Python — open systems, master equations, dynamics): [https://qutip.org/](https://qutip.org/) (GitHub linked from site)

- **Jake Vanderplas Quantum Python** (classic TDSE animation example):  
  Blog: [http://jakevdp.github.io/blog/2012/09/05/quantum-python/](http://jakevdp.github.io/blog/2012/09/05/quantum-python/)  
  Related code often in pySchrodinger repos.

### Additional Relevant Repos
- Double-slit 2D Crank-Nicolson example: [https://github.com/artmenlope/double-slit-2d-schrodinger](https://github.com/artmenlope/double-slit-2d-schrodinger)
- Various 1D TDSE Crank-Nicolson implementations: Search GitHub for "Crank-Nicolson Schrödinger" (many small educational repos).

These cover the spectrum from full Python libraries (QMsolve) to browser applets (PhET, web sims) to research-grade tools (QuTiP).  

**Your closest competitor is qmsolve.** It overlaps on the core physics (1D Schrödinger, hydrogen, custom potentials, atomic units) but goes wider with 2D/3D and two-particle systems.   
The critical difference is interface: qmsolve is a Python library that produces matplotlib windows — you need to write code to use it. Your project is a running web app a student can open and immediately interact with. That's a fundamentally different user.

**PhET is the other meaningful competitor for the browser niche.** Their Stern-Gerlach and Quantum Tunneling simulations are beautifully polished. But PhET simulations are closed pedagogical tools — fixed scenarios, no API, no extensibility, no atomic units. Yours is an open, extensible, physicist-facing tool.

**QuTiP overlaps on spin and Bloch sphere** but is a research library with a programmatic interface, not a visualizer. Their Bloch sphere is a matplotlib figure you generate from a script. Yours is an interactive drag-and-click 3D sphere. Different audience entirely.

**The most actionable gap is the analytic ψ_nlm.** Adding `scipy.special.sph_harm` + `genlaguerre` to `hydrogenic/wavefunctions.py` (alongside the existing radial solver) would let you render true 3D isosurfaces — the iconic orbital shapes that every QM student knows — and it would fill the only feature where a tiny single-file script (ssebastianmag) currently does something your project cannot. That's a weekend addition with significant visual impact for the JOSS paper.


**QM (mlubinsky/QM)** stands out as one of the most comprehensive, polished, and education-focused open-source browser-based quantum mechanics explorers available. It combines a FastAPI Python backend (sparse numerics, Crank-Nicolson TDSE, ARPACK eigen-solvers, hydrogenic radial solver) with a modern React/TypeScript frontend (interactive plots, 3D Bloch sphere via Three.js, Grotrian diagram, URL sharing).

### Key Comparison Projects
Here are the most relevant open-source alternatives (focusing on Schrödinger equation solvers/visualizers for 1D/TDSE, stationary states, and educational use):

1. **QMsolve (quantum-visualizations/qmsolve)** — Python library for solving & visualizing the Schrödinger equation (1D/2D/3D, stationary + time-dependent).
   - Supports single/multi-particle, custom potentials, superpositions, and animations.
   - Time evolution: Split-step Fourier (preferred) or Crank-Nicolson.
   - Visualizations: Matplotlib/Mayavi (some interactive sliders).
   - Strengths: Easy Python API, multi-particle/3D support, GPU options (CuPy), good for scripting/research.
   - Weaknesses: Primarily a library (run scripts/notebooks), less "app-like" browser UX. No built-in spin/hydrogenic atomic orbitals/Grotrian. Older activity (main updates ~2022).

2. **Web-based 1D TDSE Simulators** (e.g., schrodingerequation.online / marekyggdrasil/Schroedinger and similar) — Pure JS/HTML5 interactive demos.
   - Features: Gaussian packets, various potentials (harmonic, barrier, double-well), phase-colored |ψ| visualizations, momentum space, expectation values.
   - Strengths: Instant browser access, no install, great for quick demos/tunneling visualization.
   - Weaknesses: Limited potentials/customization, no eigenstate solver table, no hydrogenic/spin modules, simpler numerics (often not explicitly Crank-Nicolson with full diagnostics).

3. **PhET Quantum Simulations** (phet.colorado.edu) — High-quality educational browser applets (Quantum Wave Interference, Quantum Tunneling, Models of the Hydrogen Atom, etc.).
   - Strengths: Extremely intuitive UI/UX, designed for intro undergrad/high-school, excellent visualizations (double-slit, tunneling, atomic models). Open-source (HTML5/JS).
   - Weaknesses: Black-box "applets" rather than full solver with API/custom potentials/eigen-decompositions. Limited advanced features (no full TDSE control, no Bloch sphere, no Grotrian diagram).

4. **Other Notable Python Scripts/Libraries**
   - Jake Vanderplas' Quantum Python animations, various Crank-Nicolson 1D/2D repos (e.g., artmenlope double-slit), QuTiP (open systems, master equations).
   - These are often single-purpose notebooks/scripts: excellent for learning numerics but lack integrated UI, multi-mode (stationary + TD + atomic + spin), or shareable web deployment.

### Feature-by-Feature Comparison

**Core Solvers & Physics**:
- **QM**: Stationary (ARPACK, multiple presets + custom expr), TDSE (Crank-Nicolson with norm/current/momentum/expectation diagnostics), Hydrogenic (radial + 2D orbital density + Grotrian with selection rules), Spin-1/2 (Bloch sphere, precession, Stern-Gerlach with shots).
- **QMsolve**: Strong 1D/2D/3D stationary + TD (split-step/CN), multi-particle. No dedicated hydrogenic atomic or spin modules.
- **Web 1D Sims**: Basic TDSE + packets/potentials. Minimal eigen-solvers.
- **PhET**: Conceptual visualizations (tunneling, interference, atomic models). No raw solver access.

**User Experience & Accessibility**:
- **QM** excels with browser-based full app (dropdown modes, sliders, animations, URL persistence, exports, API docs/Swagger, physics reference modals). Local run (backend+frontend) but very app-like.
- QMsolve: Script/notebook-driven (flexible but requires Python/Matplotlib).
- Web Sims: Zero-install browser, but narrower scope.
- PhET: Best-in-class intuitive browser UX for education.

**Educational Depth**:
- **QM** is strongest here: Exact comparisons (ISW/HO), node counting, Re/Im(ψ), expectation/uncertainty plots, Grotrian transitions, Bloch measurement history/collapse, norm conservation diagnostics. Designed as an "explorer."
- Others: Good basics; PhET shines for intuition-building; QMsolve for deeper multi-particle exploration.

**Technical Implementation**:
- **QM**: Sparse matrices (efficient), safe potential parser (asteval), tests for physics invariants, FastAPI backend + React frontend. Atomic units throughout.
- QMsolve: Flexible discretization, ARPACK/LOBPCG, GPU support.
- Most scripts: Direct NumPy/SciPy implementations (educational but less optimized/scalable).

**Maintenance & Polish**:
- QM shows very recent, active development (2026 features in CHANGELOG: Re/Im, Grotrian enhancements, spin tabs, etc.) with excellent docs (README, TESTING, TODO).
- QMsolve: Solid but less active recently.
- PhET: Professionally maintained, widely used.
- Scripts: Vary widely (many one-offs).

### Summary: Where QM Stands Out
- **Best overall educational web app** for a broad QM curriculum (1D stationary/TD + atomic orbitals + spin).
- Combines numerical rigor with rich, shareable visualizations in one package. Few projects match its scope + polish in browser form.
- **Trade-offs**: Requires local run (two terminals: backend + frontend) vs. pure browser (PhET/web sims) or pure Python library (QMsolve). No native 2D/3D multi-particle yet (focus is deeper 1D + atomic/spin).
- **Use Cases**:
  - **Classroom/Exploration**: QM or PhET.
  - **Research/Scripting**: QMsolve or QuTiP.
  - **Quick Demos**: Web 1D sims.

QM fills a nice niche as a "full-stack" interactive QM laboratory. If expanded with 2D capabilities or cloud deployment (e.g., via Docker/Streamlit alternative), it could become the go-to tool.


 TODO:
 **Here’s a prioritized set of feature recommendations** to make **QM** more competitive with **QMsolve** (deeper multi-dimensional/multi-particle physics + scripting) and **PhET** (polished educational intuition, accessibility, and "wow" factor). 

QM already leads in **integrated browser UX**, **spin/hydrogenic modules**, **Grotrian diagrams**, and **educational depth** (references, diagnostics, URL sharing). These suggestions build on that strength while closing key gaps.

### 1. High-Impact Quick Wins (Easy → Medium Effort)
**Target: Match PhET’s educational polish and QMsolve’s flexibility.**

- **2D Support (Biggest Gap vs. QMsolve)**  
  Add time-dependent and stationary 2D solver (e.g., double-slit, 2D harmonic oscillator, quantum billiards). Use finite-difference or split-step Fourier.  
  *Visualization*: Heatmap + contour for |ψ|², optional vector field for probability current.  
  *Why competitive?* QMsolve shines here; PhET has wave interference simulations. This would be a major differentiator for QM.

- **Preset "Labs" / Guided Scenarios** (Strong PhET alignment)  
  Curated experiments with explanations:  
  - Tunneling resonance  
  - Coherent states in HO (no spreading)  
  - Double-slit interference  
  - Hydrogen Stark/Zeeman effect  
  - Sequential Stern-Gerlach  
  Include one-paragraph physics background + "what to observe" prompts.

- **Classical Comparison Overlays**  
  For harmonic oscillator: overlay classical probability density.  
  For free particle/wave packet: group vs. phase velocity.  
  *Educational value*: Directly addresses correspondence principle (QMsolve/PhET strength).

- **Improved Initial State Composer**  
  Drag-and-drop or graphical superposition builder (bars for |cₙ|² with phases). Eigen-decomposition chart for any initial state (already in TODO).

### 2. Medium-Term Features (Differentiation)
**Target: Broaden appeal and usability.**

- **Export / Shareable Animations**  
  GIF/MP4 export of time evolutions + parameter summary. Embeddable links or WebGL snapshots. PhET excels at shareability.

- **Keyboard Shortcuts + Accessibility**  
  Space = play/pause, arrow keys for stepping, high-contrast mode, screen-reader support for plots. Makes it more PhET-like for classrooms.

- **Multi-Particle / Entanglement Mode** (vs. QMsolve)  
  Start with two non-interacting particles (symmetric/antisymmetric states) → identical particles visualization. Later add interaction potentials.

- **Perturbation Theory Tools**  
  First-order corrections, visualize perturbed vs. unperturbed states (already in TODO). Great for undergrad quantum courses.

- **Wigner Function** (Advanced but distinctive)  
  Phase-space visualization for time evolution — shows negative regions (purely quantum). Few educational tools have this interactively.

### 3. Longer-Term / Ambitious Enhancements
- **3D Visualization** (e.g., hydrogen orbitals in full 3D with volume rendering or isosurfaces) — builds on existing 2D cross-sections.
- **AI Assistant** — Natural language queries ("show me tunneling through a barrier with E < V0") that auto-configures parameters and explains results. Leverages QM’s strong physics backend.
- **Mobile / Touch Optimization** — Better for classroom tablets.
- **Standalone Web Version** (e.g., WASM backend or hosted demo) — reduces barrier vs. PhET’s zero-install.
- **Python / API Export** — Allow exporting a Python script reproducing the current setup (bridges to QMsolve users).

### Prioritization Advice
1. **First**: 2D solver + Preset Labs + Classical overlays (biggest immediate competitiveness boost).
2. **Second**: Export/share + accessibility + eigenstate decomposition.
3. **Then**: Multi-particle and Wigner.

### Why These Close the Gaps
- **Vs. QMsolve**: Adds multi-dimensional depth and scripting-like reproducibility while keeping superior web interactivity.
- **Vs. PhET**: Adds deeper numerical control, custom potentials, exact solvers, and advanced topics (spin, hydrogen fine structure) that PhET keeps conceptual.

**QM’s current advantages** (browser app feel, spin module, Grotrian, URL state, API) are already excellent — lean into **"the most complete interactive QM laboratory"** positioning rather than trying to become a pure Python library.




