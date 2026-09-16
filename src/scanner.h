#pragma once
// scanner.h — exact cell scan (§5.1): build fences, chop at crossings,
// poke epsilon beside every piece's midpoint, report an unseen poke or OK.
//
// Numerical contract (§6):
//   kNudgeEps     = 1e-4 km (10 cm)  — poke distance from each fence
//   kMarginAccept = 1e-6 km (1 mm)   — required min-distance surplus to
//                                      report a point as uncovered
//   FP noise floor for inputs <= 1000 km is ~4.4e-13 km, far below both.
// A hole narrower than kMarginAccept is reported as covered (OK): with a
// 1 m output tolerance such a distinction is not decidable anyway.

#include "geometry.h"

namespace ff {

inline constexpr double kBandHalfWidth = 50.0;  // km
inline constexpr double kNudgeEps = 1e-4;       // km (10 cm)
inline constexpr double kMarginAccept = 1e-6;   // km (1 mm)

struct ScanResult {
    bool covered;   // true -> whole square viewed -> print OK
    double x;       // uncovered point (valid when !covered), inside the square
    double y;
    double margin;  // (min distance to flights) - 50 at (x, y)
};

ScanResult scanSquare(const Problem& p);

// Minimum distance from (x, y) to all flight lines (diagnostic / tests).
double minDistanceToFlights(const Problem& p, double x, double y);

}  // namespace ff
