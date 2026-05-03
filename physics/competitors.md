## QM Software

https://github.com/euphoricrhino/sakurai-notes

https://github.com/osscar-org/quantum-mechanics

https://github.com/mholtrop/QMPython

https://github.com/mkuznets/quantum-mechanics-lectures


Here is a structured comparison of all the meaningful overlapping projects, organized by how closely they compete with your specific feature set.

The three tabs give you cards, a full feature matrix, and a honest diff. A few things worth calling out beyond the table:

**Your closest competitor is qmsolve.** It overlaps on the core physics (1D Schrödinger, hydrogen, custom potentials, atomic units) but goes wider with 2D/3D and two-particle systems. The critical difference is interface: qmsolve is a Python library that produces matplotlib windows — you need to write code to use it. Your project is a running web app a student can open and immediately interact with. That's a fundamentally different user.

**PhET is the other meaningful competitor for the browser niche.** Their Stern-Gerlach and Quantum Tunneling simulations are beautifully polished. But PhET simulations are closed pedagogical tools — fixed scenarios, no API, no extensibility, no atomic units. Yours is an open, extensible, physicist-facing tool.

**QuTiP overlaps on spin and Bloch sphere** but is a research library with a programmatic interface, not a visualizer. Their Bloch sphere is a matplotlib figure you generate from a script. Yours is an interactive drag-and-click 3D sphere. Different audience entirely.

**The most actionable gap is the analytic ψ_nlm.** Adding `scipy.special.sph_harm` + `genlaguerre` to `hydrogenic/wavefunctions.py` (alongside the existing radial solver) would let you render true 3D isosurfaces — the iconic orbital shapes that every QM student knows — and it would fill the only feature where a tiny single-file script (ssebastianmag) currently does something your project cannot. That's a weekend addition with significant visual impact for the JOSS paper.
