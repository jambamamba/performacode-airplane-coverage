#!/usr/bin/env python3
"""cucumber.py — minimal Gherkin (BDD) runner for the Forest Fire program.

Stdlib-only runner (no behave/pytest-bdd in this environment, per plan §9.1
"no external test frameworks"). It:

  * parses tests/features/*.feature (Feature/Background/Scenario Outline/
    Examples tables, tags);
  * runs the binary in a sandbox per scenario and times it;
  * validates every result *properties* with the independent oracle
    (verify_random.py): a reported point must lie inside the square and be
    unviewed (perp. distance > 50 km), OK must be truly covered, ERROR only
    for genuinely invalid input (policy A-2);
  * renders one PNG per scenario in the style of the reference figure
    (square, flight line, dashed +/-50 km band edges, plane, 50/50 labels,
    viewed region shading, reported point) using Pillow;
  * prints a per-scenario timing table and saves build/cucumber/timing.md.

Usage:
  python3 tools/cucumber.py [--bin build/forest] [--tags @smoke]
      [--features tests/features] [--outdir build/cucumber] [--no-images]
"""

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_random import BAND, line_coeff, min_distance, parse_input, verify_pair

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("cucumber.py needs Pillow:  python3 -m pip install Pillow")


# --------------------------------------------------------------------------
# Gherkin parsing
# --------------------------------------------------------------------------

class Step:
    def __init__(self, keyword, text):
        self.keyword = keyword  # Given/When/Then/And/But
        self.text = text


class Scenario:
    def __init__(self, feature, name, tags, steps, examples, row=None):
        self.feature = feature
        self.name = name
        self.tags = tags
        self.steps = steps          # [Step] with <placeholder> text for outlines
        self.examples = examples    # [] of dict, empty for plain scenarios
        self.row = row              # raw example dict (outline instances)


def parse_feature(path):
    feature = {"name": path.stem, "tags": [], "background": [], "scenarios": []}
    cur = None            # current scenario dict or None
    mode = None           # None | "background" | "scenario" | "examples"
    new_table = False     # next table row is the header of a fresh Examples
    tags = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            tags.extend(line.split())
            continue
        if line.startswith("Feature:"):
            feature["name"] = line[len("Feature:"):].strip()
            feature["tags"] = tags
            tags = []
            mode = None
        elif line.startswith("Background:"):
            mode = "background"
        elif line.startswith("Scenario Outline:") or line.startswith("Scenario:"):
            cur = {"name": line.split(":", 1)[1].strip(), "tags": tags,
                   "steps": [], "groups": []}
            feature["scenarios"].append(cur)
            tags = []
            mode = "scenario"
        elif line.startswith("Examples:"):
            mode = "examples"
            cur["groups"].append({"header": None, "rows": []})
        elif line.startswith("|"):                       # table row
            cells = [c.strip() for c in line.strip("|").split("|")]
            if mode == "examples":
                grp = cur["groups"][-1]
                if grp["header"] is None:
                    grp["header"] = cells
                else:
                    grp["rows"].append(dict(zip(grp["header"], cells)))
        elif mode in ("background", "scenario") and re.match(
                r"^(Given|When|Then|And|But)\b", line):
            kw, text = line.split(None, 1)
            (feature["background"] if mode == "background"
             else cur["steps"]).append(Step(kw, text))
    scenarios = []
    for sc in feature["scenarios"]:
        groups = [g for g in sc["groups"] if g["header"] is not None]
        if not groups:
            scenarios.append(Scenario(feature["name"], sc["name"],
                                      feature["tags"] + sc["tags"],
                                      feature["background"] + sc["steps"], []))
        else:
            i = 0
            for grp in groups:
                for row in grp["rows"]:
                    i += 1
                    steps = []
                    for st in feature["background"] + sc["steps"]:
                        text = st.text
                        for col, val in row.items():
                            text = text.replace(f"<{col}>", val)
                        steps.append(Step(st.keyword, text))
                    name = f'{sc["name"]} [example {i}]'
                    scenarios.append(Scenario(feature["name"], name,
                                              feature["tags"] + sc["tags"],
                                              steps, [], row=row))
    return scenarios


# --------------------------------------------------------------------------
# Scenario context + step registry
# --------------------------------------------------------------------------

class Ctx:
    pass


REGISTRY = []


def step(pattern):
    rx = re.compile(pattern)
    def deco(fn):
        REGISTRY.append((rx, fn))
        return fn
    return deco


def dispatch(ctx, st):
    for rx, fn in REGISTRY:
        m = rx.fullmatch(st.text)
        if m:
            fn(ctx, m)
            return
    raise AssertionError(f"unimplemented step: {st.keyword} {st.text}")


@step(r"a square with side (\S+) km")
def _(ctx, m):
    ctx.L = float(m.group(1))
    if ctx.input_text is None:
        ctx.input_text = f"{ctx.L}\n"


def _append_flight(ctx, x0, y0, x1, y1):
    """Record a flight; the INPUT stream is assembled when the program runs."""
    ctx.flights.append((x0, y0, x1, y1))


@step(r"a flight from \(([^,)]+), ([^)]+)\) to \(([^,)]+), ([^)]+)\)")
def _(ctx, m):
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    _append_flight(ctx, x0, y0, x1, y1)


@step(r"the malformed input \"(.*)\"")
def _(ctx, m):
    ctx.input_text = m.group(1).replace("\\n", "\n")
    ctx.n_written = True            # stream is complete; never append N


@step(r"a stress input with (\d+) flights and side (\S+) km \(seed (\d+)\)")
def _(ctx, m):
    import random
    n, ctx.L, seed = int(m.group(1)), float(m.group(2)), int(m.group(3))
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        kind = rng.random()
        if kind < 0.35:      # near-horizontal chords
            y = rng.uniform(-0.2 * ctx.L, 1.2 * ctx.L)
            rows.append((0.0, y, ctx.L, y + rng.uniform(-1e-3, 1e-3) * ctx.L))
        elif kind < 0.7:     # near-vertical chords
            x = rng.uniform(-0.2 * ctx.L, 1.2 * ctx.L)
            rows.append((x, 0.0, x + rng.uniform(-1e-3, 1e-3) * ctx.L, ctx.L))
        else:                # arbitrary chords / outside lines
            rows.append((rng.uniform(-0.5 * ctx.L, 1.5 * ctx.L),
                         rng.uniform(-0.5 * ctx.L, 1.5 * ctx.L),
                         rng.uniform(-0.5 * ctx.L, 1.5 * ctx.L),
                         rng.uniform(-0.5 * ctx.L, 1.5 * ctx.L)))
    ctx.flights = rows
    ctx.n_written = True
    ctx.input_text = (f"{ctx.L}\n{n}\n" +
                      "\n".join(f"{x0} {y0} {x1} {y1}" for x0, y0, x1, y1
                                in rows) + "\n")


@step(r"the program runs")
def _(ctx, m):
    assert ctx.input_text is not None or ctx.L is not None, \
        "no input defined before running"
    if not ctx.n_written:                     # assemble: L header, N, flights
        assert ctx.L is not None, "square side not set before running"
        ctx.input_text = (f"{ctx.L}\n{len(ctx.flights)}\n" +
                          "".join(f"{x0} {y0} {x1} {y1}\n"
                                  for x0, y0, x1, y1 in ctx.flights))
    ctx.sandbox = tempfile.TemporaryDirectory()
    (Path(ctx.sandbox.name) / "INPUT").write_text(ctx.input_text)
    t0 = time.perf_counter()
    ctx.proc = subprocess.run([str(Path(ctx.bin).resolve())],
                              cwd=ctx.sandbox.name, timeout=15,
                              stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)
    ctx.elapsed = time.perf_counter() - t0
    out_file = Path(ctx.sandbox.name) / "OUTPUT"
    ctx.output_text = out_file.read_text() if out_file.exists() else ""

    # Property checks via the independent oracle (plan §9.1).
    assert ctx.proc.returncode == 0, f"exit code {ctx.proc.returncode}"
    ok, detail = verify_pair(ctx.input_text, ctx.output_text, sample=200)
    assert ok, f"oracle rejected output: {detail}"
    ctx.oracle_detail = detail

    problem = parse_input(ctx.input_text)
    line = ctx.output_text.strip()
    if problem is None or line == "ERROR":
        ctx.kind = "ERROR"
        ctx.point = None
        ctx.dmin = None
    elif line == "OK":
        ctx.kind, ctx.point = "OK", None
        ctx.dmin = None
    else:
        parts = line.split()
        ctx.point = (float(parts[0]), float(parts[1]))
        ctx.dmin = min_distance([line_coeff(f) for f in problem[1]],
                                *ctx.point)
        ctx.kind = "point"


@step(r"the result should be (OK|ERROR|a point)")
def _(ctx, m):
    want = {"OK": "OK", "ERROR": "ERROR", "a point": "point"}[m.group(1)]
    assert ctx.kind == want, f"expected {want}, got {ctx.kind} ({ctx.output_text!r})"


@step(r"the whole square should be viewed")
def _(ctx, m):
    assert ctx.kind == "OK", f"expected OK, got {ctx.kind}"


@step(r"the result should be a point at least (\S+) km from every flight")
def _(ctx, m):
    need = float(m.group(1))
    assert ctx.kind == "point", f"expected a point, got {ctx.kind}"
    assert ctx.dmin >= need - 1e-9, f"dmin {ctx.dmin} < {need}"


@step(r"the result should be OK or a point")
def _(ctx, m):
    # The input is valid by construction; the oracle (run above) has already
    # verified either the reported point or the OK via brute-force sampling.
    assert ctx.kind in ("OK", "point"), \
        f"expected OK or a point, got {ctx.kind} ({ctx.output_text!r})"


@step(r"the run should finish within (\S+) seconds")
def _(ctx, m):
    assert ctx.elapsed <= float(m.group(1)), f"took {ctx.elapsed:.3f} s"


@step(r"the run should produce a well-formed answer")
def _(ctx, m):
    assert ctx.kind in ("OK", "ERROR", "point"), "no well-formed answer"


# --------------------------------------------------------------------------
# Rendering (Pillow) — reference-figure style
# --------------------------------------------------------------------------

CANVAS = 920
MARGIN = 64


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _px(ctx, x, y):
    s = (CANVAS - 2 * MARGIN) / ctx.L
    return MARGIN + x * s, CANVAS - MARGIN - y * s


def _clip_line_pts(ctx, nx, ny, d):
    """Segment of the line nx*x+ny*y=d inside [0,L]^2; None if it misses."""
    dx, dy = -ny, nx            # unit direction along the line
    px, py = d * nx, d * ny     # a point on the line (closest to origin)
    lo, hi = -1e18, 1e18
    for p, v in ((px, dx), (py, dy)):          # p + t*v must stay in [0, L]
        if abs(v) < 1e-15:
            if not (0.0 <= p <= ctx.L):
                return None
            continue
        t0, t1 = (0.0 - p) / v, (ctx.L - p) / v
        if t0 > t1:
            t0, t1 = t1, t0
        lo, hi = max(lo, t0), min(hi, t1)
    if lo > hi:
        return None
    return (px + lo * dx, py + lo * dy), (px + hi * dx, py + hi * dy)


def _clip_poly_halfplane(poly, nx, ny, d):
    """Keep the part of polygon with nx*x+ny*y <= d (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = nx * p[0] + ny * p[1] - d
        fq = nx * q[0] + ny * q[1] - d
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _dashed(d, p1, p2, dash=12, gap=9, **kw):
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    t = 0.0
    while t < length:
        t2 = min(t + dash, length)
        d.line([x1 + ux * t, y1 + uy * t, x1 + ux * t2, y1 + uy * t2], **kw)
        t = t2 + gap


def _plane(d, cx, cy, angle, size=30, fill=(70, 70, 70)):
    ca, sa = math.cos(angle), math.sin(angle)
    pts = [(1.15, 0.0), (-0.75, 0.62), (-0.38, 0.0), (-0.75, -0.62)]
    pix = [(cx + size * (ca * x - sa * y), cy + size * (sa * x + ca * y))
           for x, y in pts]
    d.polygon(pix, fill=fill)


def _label(d, xy, text, anchor="mm", size=22, clamp=True):
    x = min(max(xy[0], MARGIN - 20), CANVAS - MARGIN + 20)
    y = min(max(xy[1], MARGIN - 26), CANVAS - MARGIN + 26)
    d.text((x, y), text, fill="black", font=_font(size), anchor=anchor)


def render(ctx, path, title):
    img = Image.new("RGB", (CANVAS, CANVAS), "white")
    d = ImageDraw.Draw(img, "RGBA")
    d.text((CANVAS // 2, 30), title, fill="black", font=_font(26), anchor="mm")

    if ctx.L is None:                     # malformed-input scenario
        d.text((CANVAS // 2, CANVAS // 2 - 20),
               "ERROR — invalid input", fill=(180, 30, 30),
               font=_font(34), anchor="mm")
        d.text((CANVAS // 2, CANVAS // 2 + 30), repr(ctx.input_text)[:90],
               fill=(90, 90, 90), font=_font(20), anchor="mm")
        img.save(path)
        return

    # Square background = unviewed (light red); viewed strips painted on top.
    d.rectangle([MARGIN, MARGIN, CANVAS - MARGIN, CANVAS - MARGIN],
                fill=(255, 205, 210, 160))
    square = [(0, 0), (ctx.L, 0), (ctx.L, ctx.L), (0, ctx.L)]
    coeffs = [line_coeff(f) for f in ctx.flights]
    for a, b, c in coeffs:
        strip = _clip_poly_halfplane(square, a, b, BAND - c)
        strip = _clip_poly_halfplane(strip, -a, -b, BAND + c)
        if len(strip) >= 3:
            d.polygon([_px(ctx, x, y) for x, y in strip],
                      fill=(165, 214, 167, 220))

    # Square border.
    d.rectangle([MARGIN, MARGIN, CANVAS - MARGIN, CANVAS - MARGIN],
                outline="black", width=3)

    # Flight lines: infinite line across the canvas (reference-figure style).
    for a, b, c in coeffs:
        seg = _clip_line_pts(ctx, a, b, -c)
        if seg:
            d.line([_px(ctx, *seg[0]), _px(ctx, *seg[1])],
                   fill=(20, 20, 20), width=4)
    # Dashed +/-50 km band edges.
    for a, b, c in coeffs:
        for s in (c - BAND, c + BAND):
            seg = _clip_line_pts(ctx, a, b, -s)
            if seg:
                _dashed(d, _px(ctx, *seg[0]), _px(ctx, *seg[1]),
                        fill=(128, 128, 128), width=3)

    # Segment endpoints + labels.
    for i, (x0, y0, x1, y1) in enumerate(ctx.flights[:6]):
        for (x, y), name in (((x0, y0), f"({x0:g}, {y0:g})"),
                             ((x1, y1), f"({x1:g}, {y1:g})")):
            px, py = _px(ctx, x, y)
            d.ellipse([px - 8, py - 8, px + 8, py + 8], fill="black")
            off = -30 if y < ctx.L / 2 else 30
            _label(d, (px, py + off), name)

    # First flight: 50/50 connector + plane at midpoint (reference-figure).
    if ctx.flights:
        x0, y0, x1, y1 = ctx.flights[0]
        a, b, c = coeffs[0]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        p_in = _px(ctx, mx - BAND * a, my - BAND * b)
        p_out = _px(ctx, mx + BAND * a, my + BAND * b)
        d.line([p_in, p_out], fill="black", width=2)
        _label(d, ((p_in[0] + p_out[0]) / 2 - 42, (p_in[1] + p_out[1]) / 2),
               "50", size=24)
        _label(d, ((p_in[0] + p_out[0]) / 2 + 42, (p_in[1] + p_out[1]) / 2),
               "50", size=24)
        pxc, pyc = _px(ctx, mx, my)
        if MARGIN <= pxc <= CANVAS - MARGIN and MARGIN <= pyc <= CANVAS - MARGIN:
            angle = math.atan2(-(y1 - y0), x1 - x0)
            _plane(d, pxc, pyc, angle)

    # Reported point.
    if ctx.point:
        px, py = _px(ctx, *ctx.point)
        d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(21, 101, 192))
        _label(d, (px, py - 34),
               f"({ctx.point[0]:.2f}, {ctx.point[1]:.2f})", size=22)
    elif ctx.kind == "OK":
        d.text((CANVAS // 2, CANVAS - MARGIN + 34), "OK — fully viewed",
               fill=(27, 94, 32), font=_font(26), anchor="mm")
    elif ctx.kind == "ERROR":
        d.text((CANVAS // 2, CANVAS - MARGIN + 34), "ERROR",
               fill=(180, 30, 30), font=_font(26), anchor="mm")
    img.save(path)


# --------------------------------------------------------------------------
# Runner + timing table
# --------------------------------------------------------------------------

def run_scenario(sc, args, idx):
    ctx = Ctx()
    ctx.bin = args.bin
    ctx.L = None
    ctx.flights = []
    ctx.n_written = False
    ctx.input_text = None
    ctx.output_text = ""
    ctx.kind = None
    ctx.point = None
    ctx.dmin = None
    ctx.elapsed = None
    ctx.sandbox = None
    failure = None
    t0 = time.perf_counter()
    try:
        for st in sc.steps:
            dispatch(ctx, st)
    except Exception as exc:                      # noqa: BLE001 — report all
        failure = f"{type(exc).__name__}: {exc}"
    wall = time.perf_counter() - t0

    slug = re.sub(r"[^\w.-]+", "_", f"{sc.feature}_{sc.name}")[:70]
    img_rel = None
    if not args.no_images:
        img_rel = f"images/{idx:03d}_{slug}.png"
        render(ctx, Path(args.outdir) / img_rel,
               f"{sc.feature}: {sc.name}")
    if ctx.sandbox:
        ctx.sandbox.cleanup()

    result = "PASS" if failure is None else "FAIL"
    if ctx.kind is None:
        shown = failure or "-"
    else:
        shown = ("OK" if ctx.kind == "OK" else
                 "ERROR" if ctx.kind == "ERROR" else
                 f"({ctx.point[0]:.2f}, {ctx.point[1]:.2f})")
    return {
        "feature": sc.feature, "scenario": sc.name, "result": result,
        "kind": ctx.kind, "reported": shown, "row": sc.row,
        "dmin": ctx.dmin, "run_ms": None if ctx.elapsed is None
        else ctx.elapsed * 1000.0, "wall_ms": wall * 1000.0,
        "L": ctx.L, "N": len(ctx.flights), "image": img_rel,
        "error": failure, "input": ctx.input_text, "output": ctx.output_text,
    }


def print_table(rows):
    cols = [("Scenario", 44), ("L", 6), ("N", 4), ("Result", 7),
            ("Reported", 18), ("dmin", 10), ("run ms", 9),
            ("wall ms", 9), ("Image", 26)]
    line = "-+-".join("-" * w for _, w in cols)
    def fmt(r):
        return [ (r["feature"] + ": " + r["scenario"])[:44],
                 f'{r["L"]:g}' if r["L"] is not None else "-",
                 str(r["N"]), r["result"],
                 r["reported"] if r["result"] == "PASS" else "-",
                 f'{r["dmin"]:.4f}' if r["dmin"] is not None else "-",
                 f'{r["run_ms"]:.1f}' if r["run_ms"] is not None else "-",
                 f'{r["wall_ms"]:.1f}',
                 (r["image"] or "-").replace("images/", "")[:26] ]
    widths = [w for _, w in cols]
    print(" | ".join(c.ljust(w) for c, w in zip((c for c, _ in cols), widths)))
    print(line)
    for r in rows:
        print(" | ".join(v.ljust(w) for v, w in zip(fmt(r), widths)))


def save_markdown(rows, path, total_s):
    with open(path, "w") as f:
        f.write("# Cucumber run timing report\n\n")
        n_pass = sum(r["result"] == "PASS" for r in rows)
        f.write(f"{n_pass}/{len(rows)} scenarios passed, total {total_s:.2f} s\n\n")
        f.write("| Scenario | L | N | Result | Reported | dmin (km) | run ms | wall ms | Image |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            l_cell = f'{r["L"]:g}' if r["L"] is not None else "-"
            n_cell = str(r["N"]) if r["L"] is not None else "-"
            rep = r["reported"] if r["result"] == "PASS" else "-"
            dmin = f"{r['dmin']:.4f}" if r["dmin"] is not None else "-"
            run_ms = f"{r['run_ms']:.1f}" if r["run_ms"] is not None else "-"
            img = r["image"] or "-"
            f.write(f'| {r["feature"]}: {r["scenario"]} | {l_cell} | '
                    f'{n_cell} | {r["result"]} | {rep} | {dmin} | '
                    f'{run_ms} | {r["wall_ms"]:.1f} | {img} |\n')
        fails = [r for r in rows if r["result"] != "PASS"]
        if fails:
            f.write("\n## Failures\n\n")
            for r in fails:
                f.write(f'- **{r["feature"]}: {r["scenario"]}** — {r["error"]}\n')
                f.write(f'  - INPUT: `{(r["input"] or "").strip()[:200]}`\n')
                f.write(f'  - OUTPUT: `{(r["output"] or "").strip()[:200]}`\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin", default="build/forest")
    ap.add_argument("--features", default="tests/features")
    ap.add_argument("--outdir", default="build/cucumber")
    ap.add_argument("--tags", default=None,
                    help="only run scenarios carrying this tag, e.g. @smoke")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--images-dir", default=None,
                    help="also copy rendered PNGs here (relative to cwd), "
                         "e.g. assets/cucumber")
    args = ap.parse_args()

    paths = sorted(Path(args.features).glob("*.feature"))
    assert paths, f"no .feature files under {args.features}"
    scenarios = [sc for p in paths for sc in parse_feature(p)]
    if args.tags:
        scenarios = [sc for sc in scenarios if args.tags in sc.tags]

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    if not args.no_images:
        (Path(args.outdir) / "images").mkdir(exist_ok=True)

    rows, t0 = [], time.perf_counter()
    for i, sc in enumerate(scenarios, 1):
        r = run_scenario(sc, args, i)
        rows.append(r)
        status = "PASS" if r["result"] == "PASS" else f'FAIL ({r["error"]})'
        print(f"[{i}/{len(scenarios)}] {status} {sc.feature}: {sc.name}")
    total = time.perf_counter() - t0

    print()
    print_table(rows)
    md = Path(args.outdir) / "timing.md"
    save_markdown(rows, md, total)

    # Optional tracked copy of the rendered images (e.g. assets/cucumber).
    if args.images_dir and not args.no_images:
        dst = Path(args.images_dir)
        dst.mkdir(parents=True, exist_ok=True)
        for r in rows:
            src = Path(args.outdir) / r["image"] if r["image"] else None
            if src and src.exists():
                shutil.copy2(src, dst / src.name)
        print(f"images copied to {dst}/")

    n_fail = sum(r["result"] != "PASS" for r in rows)
    print(f"\n{len(rows) - n_fail}/{len(rows)} scenarios passed "
          f"in {total:.2f} s  (report: {md})")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
