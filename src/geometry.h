#pragma once
// geometry.h — line representation, normalization, clipping, intersection.
// FR-04..FR-07 (docs/PROJECT_PLAN.md §3.1); formulas per §5.4.

#include <cmath>
#include <optional>
#include <vector>

namespace ff {

// Normalized infinite line: a*x + b*y + c = 0 with a^2 + b^2 == 1.
// Signed distance of point (x, y) from the line is a*x + b*y + c.
struct VecLine {
    double a = 0.0;
    double b = 0.0;
    double c = 0.0;
};

struct Pt {
    double x = 0.0;
    double y = 0.0;
};

struct Flight {
    VecLine line;  // the infinite line the airplane flew along (decision A-1)
};

struct Problem {
    double L = 0.0;                  // square side, 0 < L <= 1000
    std::vector<Flight> flights;     // 1 <= N <= 100
};

// Build the normalized line through two distinct points.
// Returns false for coincident (or non-finite) points -> input error.
bool makeFlightLine(double x0, double y0, double x1, double y1, VecLine& out);

// The portion of the line inside the square [0, L] x [0, L].
// Parameterization: p(t) = q0 + t * d, d = (-b, a) (unit), q0 = -c * (a, b).
// Returns nullopt when the line never enters the square.
struct Seg {
    VecLine line;
    Pt q0;
    double t0 = 0.0;
    double t1 = 0.0;
};
std::optional<Seg> clipLineToSquare(const VecLine& l, double L);

// Intersection of two non-parallel lines; nullopt when (near-)parallel.
std::optional<Pt> intersectLines(const VecLine& l1, const VecLine& l2);

}  // namespace ff
