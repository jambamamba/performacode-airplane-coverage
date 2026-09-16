#!/usr/bin/env python3
"""gherkin_report.py — turn a cucumber.py timing report into the Gherkin
chapter of BUILD_RECORD.md.

Reads  build/cucumber/timing.md  (written by tools/cucumber.py) and the
feature files it was generated from, then regenerates the section of
BUILD_RECORD.md between

    <!-- GHERKIN-REPORT:BEGIN -->
    ...
    <!-- GHERKIN-REPORT:END -->

The report contains, per feature file: every scenario, its example rows
(the x0/y0/x1/y1 values actually exercised), the outcome, timing, and a
relative link to the rendered coverage image (assets/cucumber/*.png).

Usage:  python3 tools/gherkin_report.py [--record BUILD_RECORD.md]
Regenerating requires a prior
        python3 tools/cucumber.py --images-dir assets/cucumber
(which `make gherkin-report` does in one step).
"""

import argparse
import re
import sys
from pathlib import Path

BEGIN = "<!-- GHERKIN-REPORT:BEGIN -->"
END = "<!-- GHERKIN-REPORT:END -->"
IMG_DIR = "assets/cucumber"


def read_rows(timing_path):
    rows = []
    for line in Path(timing_path).read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 9 and cells[3] in ("PASS", "FAIL"):
            rows.append({
                "feature": cells[0].split(":")[0].strip(),
                "scenario": cells[0],
                "L": cells[1], "N": cells[2],
                "result": cells[3], "reported": cells[4], "dmin": cells[5],
                "run_ms": cells[6], "wall_ms": cells[7], "image": cells[8],
            })
    return rows


def read_features(features_dir):
    """display name -> {file, tables: {outline name -> example-table blocks}}.
    Each Examples: group becomes its own fenced block, keeping its caption."""
    features = {}
    for p in sorted(Path(features_dir).glob("*.feature")):
        display, cur = None, None
        groups = []          # [(caption, [lines])]
        caption, lines = None, []

        def flush():
            if lines:
                groups.append((caption, list(lines)))

        for line in p.read_text().splitlines():
            s = line.strip()
            if s.startswith("Feature:"):
                display = s.split(":", 1)[1].strip()
                features[display] = {"file": p.name, "tables": {}}
            elif s.startswith("Scenario Outline:") or s.startswith("Scenario:"):
                flush()
                if display and cur and groups:
                    features[display]["tables"][cur] = groups
                cur = s.split(":", 1)[1].strip()
                groups, caption, lines = [], None, []
            elif s.startswith("Examples:"):
                flush()
                caption = s.split(":", 1)[1].strip()
                lines = []
            elif s.startswith("|") and caption is not None:
                lines.append(s)
        flush()
        if display and cur and groups:
            features[display]["tables"][cur] = groups
    return features


def build_section(rows, features_dir, summary_line):
    features = read_features(features_dir)
    out = []
    out.append("## Gherkin (BDD) scenario report — `make cucumber`")
    out.append("")
    out.append(f"Generated from `tests/features/*.feature` by `tools/cucumber.py`; "
               f"last full run: **{summary_line}**. Every scenario executes the "
               f"graded binary in a sandbox and its output is independently "
               f"re-verified by the Python oracle (`tools/verify_random.py`) "
               f"before the expectation is asserted. A coverage image is rendered "
               f"per scenario into `{IMG_DIR}/` (green = viewed band, "
               f"red = unviewed, black = flight line, dashed gray = ±50 km band "
               f"edges, ✈ = plane at the segment midpoint, blue dot = reported "
               f"uncovered point); the first image of each outline is embedded, "
               f"the rest are linked from the result tables.")
    out.append("")

    # Group by feature display name, preserving run order.
    by_file, order = {}, []
    for r in rows:
        if r["feature"] not in by_file:
            by_file[r["feature"]] = []
            order.append(r["feature"])
        by_file[r["feature"]].append(r)

    idx = 0
    for display in order:
        meta = features.get(display, {"file": "?.feature", "tables": {}})
        frows = by_file[display]
        out.append(f"### Feature file: `tests/features/{meta['file']}` "
                   f"({len(frows)} scenarios)")
        out.append("")
        # Sub-group by scenario outline name.
        by_outline, outline_order = {}, []
        for r in frows:
            key = r["scenario"].split(": ", 1)[1].rsplit(" [example ", 1)[0]
            if key not in by_outline:
                by_outline[key] = []
                outline_order.append(key)
            by_outline[key].append(r)
        for key in outline_order:
            srows = by_outline[key]
            tbl = meta["tables"].get(key, "")
            out.append(f"#### {key}")
            out.append("")
            if tbl:
                out.append("Example rows exercised (from the feature source):")
                out.append("")
                for caption, tlines in tbl:
                    if caption:
                        out.append(f"*Examples: {caption}*")
                        out.append("")
                    out.append("```gherkin")
                    out.extend(tlines)
                    out.append("```")
                    out.append("")
            first_img = srows[0]["image"]
            if first_img:
                out.append(f"![coverage: {key}]({IMG_DIR}/"
                           f"{Path(first_img).name})")
                out.append("")
            out.append("| # | Result | Reported | dmin (km) | run ms | wall ms "
                       "| Coverage image |")
            out.append("|---|---|---|---|---|---|---|")
            for r in srows:
                idx += 1
                img = r["image"]
                if img:
                    name = Path(img).name
                    img_cell = (f"[{name.split('_', 1)[0]}]"
                                f"({IMG_DIR}/{name})")
                else:
                    img_cell = "-"
                out.append(f"| {idx} | {r['result']} | {r['reported']} | "
                           f"{r['dmin']} | {r['run_ms']} | {r['wall_ms']} | "
                           f"{img_cell} |")
            out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timing", default="build/cucumber/timing.md")
    ap.add_argument("--features", default="tests/features")
    ap.add_argument("--record", default="BUILD_RECORD.md")
    args = ap.parse_args()

    timing = Path(args.timing)
    if not timing.exists():
        sys.exit(f"{timing} not found — run: make cucumber "
                 f"--images-dir {IMG_DIR}")
    head = timing.read_text().splitlines()
    summary_line = head[2].strip() if len(head) > 2 else "?"

    rows = read_rows(timing)
    section = build_section(rows, args.features, summary_line)

    record = Path(args.record)
    text = record.read_text()
    if BEGIN in text and END in text:
        pre = text.split(BEGIN)[0]
        post = text.split(END, 1)[1]
    else:
        pre = text + ("" if text.endswith("\n") else "\n")
        post = ""
    record.write_text(pre + BEGIN + "\n" + section + "\n" + END + post)
    print(f"{record}: Gherkin report updated ({len(rows)} scenarios — "
          f"{summary_line})")


if __name__ == "__main__":
    main()
