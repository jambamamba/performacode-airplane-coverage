// scanner.cpp — the fence-and-poke exact scan (§5.1, §5.3).
//
// 1. Fences: 2 band-edge lines per flight + 4 square edges (M <= 204).
// 2. Clip each fence to the square; split every fence at every crossing
//    that falls strictly inside another fence's clipped span.
// 3. For each elementary piece, poke eps perpendicular to both sides of
//    its midpoint; keep pokes inside the square; a poke whose minimum
//    distance to all flight lines exceeds 50 + kMarginAccept proves an
//    uncovered region. Track the best-margin poke; none -> OK.

#include "scanner.h"

#include <algorithm>
#include <limits>
#include <vector>

namespace ff {
namespace {

constexpr double kSplitTol = 1e-9;   // interior test tolerance for split ts
constexpr double kSquareTol = 1e-9;  // tolerance for "intersection in square"

void addSplitIfInterior(const Seg& s, const Pt& p, std::vector<double>& ts) {
    // Project onto the unit direction: t = (p - q0) . d, d unit.
    const double dx = -s.line.b;
    const double dy = s.line.a;
    const double t = (p.x - s.q0.x) * dx + (p.y - s.q0.y) * dy;
    if (t > s.t0 + kSplitTol && t < s.t1 - kSplitTol) {
        ts.push_back(t);
    }
}

}  // namespace

double minDistanceToFlights(const Problem& p, double x, double y) {
    double best = std::numeric_limits<double>::infinity();
    for (const Flight& f : p.flights) {
        const double d = std::abs(f.line.a * x + f.line.b * y + f.line.c);
        if (d < best) best = d;
    }
    return best;
}

ScanResult scanSquare(const Problem& p) {
    const double L = p.L;

    // ---- Phase 1: build fence lines -------------------------------------
    std::vector<VecLine> lines;
    lines.reserve(2 * p.flights.size() + 4);
    for (const Flight& f : p.flights) {
        const VecLine& l = f.line;
        lines.push_back(VecLine{l.a, l.b, l.c - kBandHalfWidth});
        lines.push_back(VecLine{l.a, l.b, l.c + kBandHalfWidth});
    }
    lines.push_back(VecLine{1.0, 0.0, 0.0});     // x = 0
    lines.push_back(VecLine{1.0, 0.0, -L});      // x = L
    lines.push_back(VecLine{0.0, 1.0, 0.0});     // y = 0
    lines.push_back(VecLine{0.0, 1.0, -L});      // y = L

    // ---- Phase 2: clip and split ----------------------------------------
    std::vector<Seg> segs;
    segs.reserve(lines.size());
    for (const VecLine& l : lines) {
        if (auto s = clipLineToSquare(l, L)) {
            segs.push_back(*s);
        }
    }

    std::vector<std::vector<double>> ts(segs.size());
    for (size_t i = 0; i < segs.size(); ++i) {
        ts[i].push_back(segs[i].t0);
        ts[i].push_back(segs[i].t1);
    }

    for (size_t i = 0; i < segs.size(); ++i) {
        for (size_t j = i + 1; j < segs.size(); ++j) {
            auto ip = intersectLines(segs[i].line, segs[j].line);
            if (!ip) continue;
            if (ip->x < -kSquareTol || ip->x > L + kSquareTol ||
                ip->y < -kSquareTol || ip->y > L + kSquareTol) {
                continue;  // crossing lies outside the square
            }
            addSplitIfInterior(segs[i], *ip, ts[i]);
            addSplitIfInterior(segs[j], *ip, ts[j]);
        }
    }

    // ---- Phase 3: poke beside every piece's midpoint ---------------------
    ScanResult result;
    result.covered = true;
    result.x = 0.0;
    result.y = 0.0;
    result.margin = kMarginAccept;

    std::vector<double> sorted;
    for (size_t i = 0; i < segs.size(); ++i) {
        const Seg& s = segs[i];
        sorted = ts[i];
        std::sort(sorted.begin(), sorted.end());

        const double dx = -s.line.b;  // unit direction along the fence
        const double dy = s.line.a;

        for (size_t k = 0; k + 1 < sorted.size(); ++k) {
            const double tm = 0.5 * (sorted[k] + sorted[k + 1]);
            const Pt m{s.q0.x + tm * dx, s.q0.y + tm * dy};

            for (int sign : {1, -1}) {
                // Perpendicular poke across the fence: along +/- (a, b).
                const Pt probe{m.x + sign * kNudgeEps * s.line.a,
                               m.y + sign * kNudgeEps * s.line.b};
                if (probe.x < 0.0 || probe.x > L || probe.y < 0.0 ||
                    probe.y > L) {
                    continue;  // poke left the square (square-edge fences)
                }

                // Coverage probe: one pass over the flights.
                bool covered = false;
                double minD = std::numeric_limits<double>::infinity();
                for (const Flight& f : p.flights) {
                    const double d =
                        std::abs(f.line.a * probe.x + f.line.b * probe.y +
                                 f.line.c);
                    if (d <= kBandHalfWidth) {
                        covered = true;
                        break;
                    }
                    if (d < minD) minD = d;
                }
                if (covered) continue;

                const double margin = minD - kBandHalfWidth;
                if (margin > result.margin) {
                    result.margin = margin;
                    result.x = probe.x;
                    result.y = probe.y;
                    result.covered = false;
                }
            }
        }
    }
    return result;
}

}  // namespace ff
