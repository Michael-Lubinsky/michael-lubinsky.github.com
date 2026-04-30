The roadmap lays out your path across 5 phases. Here's the logic behind the ordering:

# Phase 1 — Hydrogen atom + Spin** 
come first because they are exact, analytically solvable problems. The hydrogen atom is the bridge between your 1D Schrödinger solver and full 3D QM — it introduces spherical harmonics, radial wavefunctions, and the quantum numbers n/l/m in a clean context. Spin is conceptually independent and short to learn, but you need it before anything else.


Here is the full study plan broken into 6 sequential stages, each building on the last. Click through the steps — the final stage is the app spec.A few things worth emphasizing as you work through this:

**The separation of variables in Stage 1 is the most important conceptual step.** Once you see that ψ = R(r)·Y(θ,φ) splits the problem cleanly, everything else is "just" solving two known ODEs. The angular part gives you orbital shapes; the radial part gives you energy quantization.

**Stage 3 is where the physics lives.** The centrifugal barrier `ℏ²ℓ(ℓ+1)/2mr²` is what prevents electrons from collapsing into the nucleus even without the Pauli exclusion principle. Watch how it pushes R(r) away from r=0 for ℓ > 0 — this is directly visible in your radial probability plots.

**The app builds naturally on your existing solver.** Your Crank-Nicolson stepper already handles ψ on a grid — the main new ingredient is `scipy.special.genlaguerre` for R_nℓ and `scipy.special.sph_harm` for Y_ℓm. The 2D cross-section heatmap of |ψ|² in the xz-plane is the killer feature that makes everything concrete: you can literally *see* the lobes, the nodes, and how n and ℓ shape the orbital.

**The energy level diagram with clickable transitions** (Stage 6, fourth feature) is also a perfect bridge to the Zeeman effect in Phase 2 — you'll just add a B-field and watch those levels split.

Hit "Get the Python code" on the last panel to get the full `ψ_nlm` implementation ready to drop into your FastAPI backend.
# Phase 2 — Perturbation theory before Zeeman** 
is the key sequencing decision. The Zeeman effect *is* an application of perturbation theory — you cannot understand it properly without first learning how small perturbations shift energy levels. Fine/hyperfine structure follows naturally from the same toolkit.

# Phase 3 — Many-body before condensed matter** 
is non-negotiable. Hartree-Fock, Slater determinants, and second quantization are the language in which crystals, metals, and semiconductors are actually described. Skipping this makes Phase 4 feel like memorizing formulas.

# Phase 4 — Condensed matter as a block.** 
Crystals → Metals → Semiconductors is the canonical order (each builds on Bloch's theorem). The Ising model is slightly detached — it's statistical physics more than QM — but it's excellent preparation for understanding phase transitions before tackling superconductivity. The Josephson effect sits last here because it requires Cooper pairs and BCS theory.

# Phase 5 — Dirac last** 
because it requires comfort with all of QM and some exposure to special relativity. It's the natural capstone before quantum field theory.

Each topic has a **complementary app** that reinforces the physics. Click any topic card for a deeper breakdown of what to study and how to build the app.
