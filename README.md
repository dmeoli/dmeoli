## Donato Meoli

Optimization at the **University of Pisa**, coming from symbolic AI and working between the
two. What holds them together is one idea: the difficulty of a problem lies in how it is
written, so the useful move is to rewrite it, as a set of smaller problems or in a different
formalism altogether. Knowledge representation and expert systems on one side, decomposition
methods for large-scale optimization on the other, and learned heuristics inside exact solvers
where the two meet.

→ **[dmeoli.github.io](https://dmeoli.github.io)** · [CV](https://dmeoli.github.io/cv.pdf) · [ORCID](https://orcid.org/0009-0001-2500-2606) · [GitLab](https://gitlab.com/dmeoli) · [LinkedIn](https://www.linkedin.com/in/donato-meoli/)

### Publications

- A. Frangioni, C. Gentile, **D. Meoli**. *Dynamic programming for the single-unit commitment
  problem with spinning reserves and reactive power*. Submitted, 2026.
- D. Fioriti et al. (incl. **D. Meoli**). *Enhancing energy system modelling with advanced
  mathematical decomposition techniques: feasibility of coupling SMS++ and PyPSA*.
  IEEE EEEIC / I&CPS Europe, 2025.
  [doi:10.1109/EEEIC/ICPSEurope64998.2025.11169291](https://doi.org/10.1109/EEEIC/ICPSEurope64998.2025.11169291)

### What I build

| | |
|---|---|
| [**SMS++**](https://gitlab.com/smspp) | C++ framework for block-structured optimization: a model is a tree of `Block`s, an algorithm is a `Solver` that attaches to one. One of its two main maintainers, with Antonio Frangioni. `SVMBlock`, `TwoStageStochasticBlock`, `MultiStageStochasticBlock`, `BendersDecompositionSolver` and `BranchAndXSolver` are mine end to end; large parts of `UCBlock` (including the exact DP solvers for the single-unit commitment problem), of `BundleSolver`, `MILPSolver` and the core are as well. |
| [**aima-python**](https://github.com/aimacode/aima-python) | Fourth-most-active contributor to Russell & Norvig's reference code: CDCL SAT solving, AC3b/AC4/GAC, planning-as-search translators, SVMs, the missing 4th-edition algorithms. |
| [**optiml**](https://github.com/dmeoli/optiml) | Optimizers, from line search to proximal bundle and interior point, wired to scikit-learn-compatible models trained with them. |
| [**pypsa2smspp**](https://github.com/SPSUnipi/pypsa2smspp) · [**pySMSpp**](https://github.com/SPSUnipi/pySMSpp) | Driving SMS++ from Python, and importing models written elsewhere into it. |

Also upstream in SciPy, HiGHS, qpsolvers, MCFClass, FastFlow and the COIN-OR conda-forge feedstocks.
