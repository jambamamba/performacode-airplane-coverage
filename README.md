# Forest Fire Coverage — Task 1

Determine whether N airplanes collectively viewed an entire square forest, and
if not, name one unviewed point. This repository contains a fully verified C++17
solution plus the complete engineering record behind it.

**Start here → [ASSIGNMENT.md](ASSIGNMENT.md)** is the original task statement.

## The problem in one paragraph

A square forest `[0, L] × [0, L]` (L ≤ 1000 km) was scanned by N ≤ 100
airplanes. Each flew a straight line between an entry and an exit point and
sees every point within 50 km perpendicular distance of its flight line. The
program reads `INPUT` (L, N, then N flights as `x0 y0 x1 y1`) and writes
`OUTPUT`: `OK` if the whole square was viewed, otherwise the coordinates of one
unviewed point inside or on the square (accurate to 1 m); `ERROR` for invalid
input. Limits: 10 s wall time, 4 GB RAM, correct termination, C/C++ standard
library only.

## How AI was used

This solution was developed **with an AI pair-programmer (Codebuff)** working
interactively with the developer:

- **Design discussion** — the candidate algorithms (grid sampling, incremental
  uncovered-polygon set, arrangement/"fence" scan) were debated with explicit
  pros and cons, worst-case complexity, and numerical-robustness analysis; the
  trade-off review and the final selection are recorded in
  [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) (§5.1, §5.5, §5.6).
- **Implementation** — the AI wrote the C++ sources, the test suite, the
  verification tooling (Python oracle, Gherkin runner, renderers), and the
  Make targets, with the developer reviewing and steering at every step.
- **Verification** — every layer was executed and re-checked by the AI:
  unit and acceptance tests, ASan/UBSan, gcov coverage, randomized
  differential testing against an independently written oracle, and a
  55-scenario Gherkin suite with rendered coverage images. Results are pinned
  in [docs/BUILD_RECORD.md](docs/BUILD_RECORD.md).

The AI also documented its own work: edge cases, defensive branches that
cannot be covered (with justification), and re-verification after refactors
are all written up in the documents below rather than left in chat logs.

## How the solution was chosen

Three algorithm families were compared before any code was written:

| Candidate | Verdict |
|---|---|
| Grid sampling of candidate points | Rejected: can miss narrow holes; no proof of coverage |
| Incremental uncovered-polygon set (Boolean subtraction) | Correct but rejected: pieces can double every pass (2ⁿ worst case), sliver robustness, no early exit (§5.5) |
| **Fence-and-poke arrangement scan (selected)** | Exact, O(M²) ≈ 41.6k pieces at N=100, ~0.1 s, stateless, early-exit (§5.1, §5.6) |

The full reasoning — including why the selected algorithm cannot suffer the
exponential blow-up of the polygon method — is in the plan (§5.5–§5.6).

## Build and run

```bash
make all            # build the graded binary: build/forest
./build/forest      # reads ./INPUT, writes ./OUTPUT
```

Requires a C++17 compiler (toolchain pinned in docs/BUILD_RECORD.md).

### Verify everything

```bash
make test            # unit tests (TC-U01..U22) + acceptance fixtures (TC-01..TC-17, TC-20)
make sanitize        # ASan + UBSan over all fixtures
make coverage        # gcov structural coverage (merged fixtures + unit tests)
make oracle          # randomized differential testing vs independent Python oracle
make timing          # N=100 stress wall-time / peak-RSS
make cucumber        # Gherkin suite: 55 scenarios, PNG coverage images, timing table
make gherkin-report  # cucumber run + tracked images + BUILD_RECORD report section
```

Reports land in `build/reports/` and `build/cucumber/`; the tracked,
checked-in equivalents live in `docs/BUILD_RECORD.md` and `assets/cucumber/`.

## Suggested reading order for reviewers

1. **[ASSIGNMENT.md](ASSIGNMENT.md)** — the task being solved (you are solving
   it for a grader; start here to know the rules).
2. **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** — requirements, decisions
   A-1..A-5, algorithm design with figures, alternative-algorithms analysis
   (§5.5/§5.6), numerical-robustness contract (§6), test plan (§9),
   DO-178C/DO-330 alignment (§8), traceability matrix.
3. **`src/`** — the implementation: `input.cpp` → `geometry.cpp` →
   `scanner.cpp` → `output.cpp` → `run.cpp` (data-flow order); each file's
   header comment ties it to plan sections.
4. **[docs/BUILD_RECORD.md](docs/BUILD_RECORD.md)** — pinned toolchain, how to
   reproduce every check, structural-coverage results (with justifications for
   the few non-covered defensive lines), the full Gherkin scenario report with
   per-scenario timings and coverage images.
5. **`tests/` and `tools/`** — unit tests (`tests/test_unit.cpp`), acceptance
   fixtures (`tests/fixtures/`), Gherkin features (`tests/features/`), the
   independent Python oracle and report generators (`tools/`).
6. **[assets/](assets/)** — the task diagram, algorithm figures used by the
   plan, and the rendered coverage images (`assets/cucumber/`) referenced by
   the Gherkin report.

## Repository layout

```
ASSIGNMENT.md            this task's statement (original brief)
docs/                    PROJECT_PLAN.md, BUILD_RECORD.md
src/                     C++17 sources (input, geometry, scanner, output, run)
tests/                   unit tests, acceptance fixtures, Gherkin features
tools/                   Python oracle, Gherkin runner, report generators
assets/                  diagrams + tracked coverage images (cucumber/*.png)
Makefile                 build + all verification targets
```
