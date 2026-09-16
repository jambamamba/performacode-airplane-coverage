# BUILD_RECORD.md — pinned toolchain and verification record

Per project-plan.md §8.2 (DO-330 tool qualification mindset): this file is
part of the release record. A compiler or flag change is a **re-verification
event**, not a dependency refresh.

## Toolchain

| Component | Version |
|---|---|
| OS | Linux (Ubuntu 25.x, x86-64) |
| `g++` | 15.2.0 (Ubuntu 15.2.0-16ubuntu1) |
| `python3` | 3.14 (oracle only; not part of the shipped artifact) |
| `make` | GNU Make |

## Standard build (graded artifact)

```sh
make all
# equivalent to:
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic \
    -o build/forest src/main.cpp src/input.cpp src/geometry.cpp \
    src/scanner.cpp src/output.cpp src/run.cpp
```

Flags rationale:

| Flag | Why |
|---|---|
| `-std=c++17` | Required language level; standard library only (task rule) |
| `-O2` | Speed with predictable codegen; **no** `-ffast-math` (determinism, DR-10) |
| `-Wall -Wextra -Wpedantic` | Zero-warning policy |

Notes:

- No third-party libraries; the submission translation units depend on the
  C++17 standard library only (plan §12).
- No parallelism, no clock reads in the decision path — bitwise-reproducible
  output on the pinned toolchain (DR-10).

## Verification configurations

| Target | Flags | Purpose |
|---|---|---|
| `make test` | as above | Unit tests TC-U01..U22 + acceptance fixtures |
| `make sanitize` | `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer` | ASan+UBSan over all fixtures; zero findings required (TC-19) |
| `make coverage` / `make report` | `-O0 -g --coverage` | gcov structural coverage; counters of both coverage binaries (same program name `forest` in `build/cov/fixture` and `build/cov/unit`) are overlaid with `gcov-tool merge` (TC + §9.5) |
| `make timing` | as graded build | TC-04/TC-17 wall time + peak RSS |
| `make oracle` | python3 tools/verify_random.py | Differential testing vs. independent oracle |
| `make cucumber` | python3 tools/cucumber.py | Gherkin BDD layer: 55 scenarios across 4 `.feature` files (many x0/y0/x1/y1 example rows); every run is verified by the independent oracle, rendered to a PNG (viewed band green / unviewed red, reference-figure style) in `build/cucumber/images/`, and reported in a per-scenario timing table (`build/cucumber/timing.md`). `make cucumber-smoke` runs the tagged @timing subset |

## Structural coverage result (§9.5, merged fixtures + unit tests)

| File | Line coverage |
|---|---|
| `src/main.cpp` | 100% |
| `src/output.cpp` | 100% |
| `src/geometry.cpp` | 100% |
| `src/scanner.cpp` | 100% |
| `src/input.cpp` | 97.7% — 1 defensive line, justified in project-plan.md §9.6 |
| `src/run.cpp` | 78.6% — `catch (...)` defensive handler, justified in §9.6 |

## Verification results — 2026-09-15

| Check | Result |
|---|---|
| Warning-free build (`-Wall -Wextra -Wpedantic`) | PASS (0 warnings) |
| Unit tests TC-U01..U22 | PASS (22/22) |
| Acceptance fixtures TC-01..TC-17 (+TC-10 synthesized) | PASS (18/18, exit 0, exact OUTPUT match) |
| Oracle validation of all fixture outputs | PASS (18/18) |
| Randomized differential testing (`make oracle`, 50 trials, seed 20260915) | PASS (50/50) |
| ASan + UBSan over all fixtures | PASS (0 findings) |
| TC-04/TC-17 timing (N=100 stress) | PASS (0.10 s wall vs 10 s limit) |
| Peak RSS | ~7.5 MB vs 4 GB limit |
| Structural coverage | 100% lines on main/output/geometry/scanner; residual lines justified (plan §9.6) |
| Gherkin scenarios (`make cucumber`) | PASS (55/55, oracle-verified, images + timing table generated) |
