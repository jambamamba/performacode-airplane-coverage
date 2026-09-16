#!/usr/bin/env python3
"""verify_random.py — independent oracle for the Forest Fire program (plan §9.1).

DO-330 tool-criterion-2 tool: it may fail to detect an error, so it is never
trusted alone; it is validated against analytic cases (the fixtures) and used
for differential testing against the C++ binary.

Modes:
  verify  INPUT OUTPUT           verify one INPUT/OUTPUT pair (exit 0 ok, 1 bad)
  random  --bin B [options]      randomized differential testing (default mode)

Checks performed:
  * ERROR is accepted only when the input is genuinely invalid per policy A-2
    (independently re-implemented here in Python).
  * A reported point must lie inside the closed square and be unviewed:
    min over flight lines of perpendicular distance > 50 km (+ tiny slack).
  * OK is accepted unless the brute-force sampler finds a clearly unviewed
    sample point (heuristic false-OK detector -> exit 2, manual analysis).
"""

import argparse
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

TOL = 1e-9          # geometric slack for boundary decisions
MARGIN = 1e-6       # same acceptance margin as the C++ scanner (kMarginAccept)
BAND = 50.0


def parse_input(text):
    """Return (L, flights) or None when the input is invalid per A-2."""
    tokens = text.split()
    if len(tokens) < 2:
        return None
    try:
        L = float(tokens[0])
        N = int(tokens[1])
    except ValueError:
        return None
    if not math.isfinite(L) or not (0.0 < L <= 1000.0):
        return None
    if str(tokens[1]) != str(N) or not (1 <= N <= 100):
        return None
    if len(tokens) != 2 + 4 * N:
        return None
    flights = []
    vals = []
    for t in tokens[2:]:
        try:
            v = float(t)
        except ValueError:
            return None
        if not math.isfinite(v):
            return None
        vals.append(v)
    for i in range(N):
        x0, y0, x1, y1 = vals[4 * i:4 * i + 4]
        if math.hypot(x1 - x0, y1 - y0) <= 0.0:
            return None
        flights.append((x0, y0, x1, y1))
    return L, flights


def line_coeff(f):
    """Normalized (a, b, c) with a^2 + b^2 = 1; signed distance a*x+b*y+c."""
    x0, y0, x1, y1 = f
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    return dy / length, -dx / length, (dx * y0 - dy * x0) / length


def min_distance(flights, x, y):
    return min(abs(a * x + b * y + c) for a, b, c in flights)


def verify_pair(inp_text, out_text, sample=400):
    """Return (ok, detail). ok=False means the oracle rejects the output."""
    problem = parse_input(inp_text)
    out_line = out_text.strip()
    if problem is None:
        return (out_line == "ERROR", "invalid input, output must be ERROR")
    L, flights = problem
    coeffs = [line_coeff(f) for f in flights]

    if out_line == "ERROR":
        return (False, "ERROR emitted for a valid input")

    parts = out_line.split()
    if len(parts) == 1 and parts[0] == "OK":
        # Brute-force false-OK detector (heuristic, per plan §9.1).
        step = L / sample
        for i in range(sample + 1):
            x = min(L, i * step)
            for j in range(sample + 1):
                y = min(L, j * step)
                if min_distance(coeffs, x, y) > BAND + 0.05:
                    return (False, f"false OK: ({x},{y}) unviewed")
        return (True, "OK accepted (sampler clean)")

    if len(parts) != 2:
        return (False, f"malformed output line: {out_line!r}")
    try:
        x, y = float(parts[0]), float(parts[1])
    except ValueError:
        return (False, f"malformed output line: {out_line!r}")
    if not (math.isfinite(x) and math.isfinite(y)):
        return (False, "non-finite point")
    if not (-TOL <= x <= L + TOL and -TOL <= y <= L + TOL):
        return (False, f"point ({x},{y}) outside the square")
    dmin = min_distance(coeffs, x, y)
    if dmin <= BAND + MARGIN:
        return (False, f"point ({x},{y}) is viewed (dmin={dmin})")
    return (True, f"point ({x},{y}) unviewed, dmin={dmin:.6f}")


def random_problem(rng):
    L = rng.choice([1.0, 100.0, 120.0, 1000.0])
    n = rng.randint(1, 12)
    flights = []
    for _ in range(n):
        # Mix of boundary-crossing lines, near-parallel pairs, degenerate-ish.
        kind = rng.random()
        if kind < 0.3:  # horizontal-ish
            y = rng.uniform(-0.2 * L, 1.2 * L)
            flights.append((0.0, y, L, y + rng.uniform(-1e-3, 1e-3) * L))
        elif kind < 0.6:  # vertical-ish
            x = rng.uniform(-0.2 * L, 1.2 * L)
            flights.append((x, 0.0, x + rng.uniform(-1e-3, 1e-3) * L, L))
        else:  # arbitrary chord or outside line
            flights.append((rng.uniform(-0.5 * L, 1.5 * L),
                            rng.uniform(-0.5 * L, 1.5 * L),
                            rng.uniform(-0.5 * L, 1.5 * L),
                            rng.uniform(-0.5 * L, 1.5 * L)))
    return L, flights


def format_problem(L, flights):
    lines = [f"{L}", f"{len(flights)}"]
    lines += [f"{x0} {y0} {x1} {y1}" for x0, y0, x1, y1 in flights]
    return "\n".join(lines) + "\n"


def run_random(args):
    rng = random.Random(args.seed)
    failures = 0
    for trial in range(args.trials):
        L, flights = random_problem(rng)
        inp_text = format_problem(L, flights)
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / "INPUT"
            inp.write_text(inp_text)
            proc = subprocess.run(
                [str(Path(args.bin).resolve())], cwd=td, timeout=30,
                capture_output=True, text=True)
            out_file = Path(td) / "OUTPUT"
            out_text = out_file.read_text() if out_file.exists() else ""
            ok, detail = verify_pair(inp_text, out_text, sample=args.sample)
            if proc.returncode != 0:
                ok, detail = False, f"exit code {proc.returncode}"
            if not ok:
                failures += 1
                print(f"FAIL trial {trial}: {detail}")
                print(f"  INPUT:\n{inp_text}")
                print(f"  OUTPUT: {out_text!r}")
            elif args.verbose:
                print(f"ok   trial {trial}: {detail}")
    print(f"{args.trials - failures}/{args.trials} trials passed "
          f"(seed {args.seed})")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode")

    apv = sub.add_parser("verify", help="verify one INPUT/OUTPUT pair")
    apv.add_argument("input")
    apv.add_argument("output")
    apv.add_argument("--sample", type=int, default=400)

    apr = sub.add_parser("random", help="randomized differential testing")
    apr.add_argument("--bin", default="build/forest")
    apr.add_argument("--trials", type=int, default=50)
    apr.add_argument("--seed", type=int, default=20260915)
    apr.add_argument("--sample", type=int, default=200)
    apr.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args()
    if args.mode == "verify":
        ok, detail = verify_pair(
            Path(args.input).read_text(), Path(args.output).read_text(),
            sample=args.sample)
        print(("PASS: " if ok else "FAIL: ") + detail)
        sys.exit(0 if ok else 1)
    sys.exit(run_random(args))


if __name__ == "__main__":
    main()
