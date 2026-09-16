// geometry.cpp — see geometry.h. Pure computational geometry, no I/O.

#include "geometry.h"

namespace ff {

bool makeFlightLine(double x0, double y0, double x1, double y1, VecLine& out) {
    const double dx = x1 - x0;
    const double dy = y1 - y0;
    if (!std::isfinite(dx) || !std::isfinite(dy)) {
        return false;  // non-finite endpoint coordinates
    }
    const double len = std::hypot(dx, dy);
    if (!(len > 0.0)) {
        return false;  // entry and exit points coincide (also rejects NaN)
    }
    out.a = dy / len;
    out.b = -dx / len;
    out.c = (dx * y0 - dy * x0) / len;
    return true;
}

std::optional<Seg> clipLineToSquare(const VecLine& l, double L) {
    // Point on the line nearest the origin: q0 = -c * (a, b).
    const Pt q0{-l.c * l.a, -l.c * l.b};
    // Unit direction along the line.
    const double dx = -l.b;
    const double dy = l.a;

    // Slab clip against [0, L] on each axis (§5.4).
    bool have_range = false;
    double lo = 0.0, hi = 0.0;

    if (std::abs(dx) < 1e-15) {
        if (q0.x < 0.0 || q0.x > L) return std::nullopt;  // parallel, outside
    } else {
        double ta = (0.0 - q0.x) / dx;
        double tb = (L - q0.x) / dx;
        if (ta > tb) std::swap(ta, tb);
        lo = ta;
        hi = tb;
        have_range = true;
    }

    if (std::abs(dy) < 1e-15) {
        if (q0.y < 0.0 || q0.y > L) return std::nullopt;
    } else {
        double ta = (0.0 - q0.y) / dy;
        double tb = (L - q0.y) / dy;
        if (ta > tb) std::swap(ta, tb);
        if (!have_range) {
            lo = ta;
            hi = tb;
        } else {
            lo = std::max(lo, ta);
            hi = std::min(hi, tb);
        }
    }

    if (hi < lo) {
        if (hi - lo > -1e-12) {
            hi = lo;  // touch at a corner: keep the degenerate segment
        } else {
            return std::nullopt;
        }
    }
    return Seg{l, q0, lo, hi};
}

std::optional<Pt> intersectLines(const VecLine& l1, const VecLine& l2) {
    const double det = l1.a * l2.b - l2.a * l1.b;
    if (std::abs(det) < 1e-12) {
        return std::nullopt;  // parallel (or nearly) — no unique crossing
    }
    Pt p;
    p.x = (l1.b * l2.c - l2.b * l1.c) / det;
    p.y = (l1.c * l2.a - l2.c * l1.a) / det;
    return p;
}

}  // namespace ff
