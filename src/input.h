#pragma once
// input.h — parsing and validation of INPUT (FR-01..FR-03, DR-01..DR-03).
// Validation policy: lenient superset per stakeholder decisions A-2, A-3.

#include <iosfwd>
#include <string>

#include "geometry.h"

namespace ff {

// Parses L, N and the N flight reports. Returns false (and leaves `out`
// unmodified) for any input rejected by the A-2 policy:
//   - missing/unparseable tokens, missing required tokens
//   - L outside (0, 1000] (fractional L accepted; NaN/inf rejected)
//   - N outside [1, 100]
//   - non-finite flight coordinates
//   - coincident entry/exit points of one flight
//   - extra trailing tokens
bool readProblem(std::istream& in, Problem& out);

// Convenience for tests: parse from a string.
bool readProblemFromString(const std::string& text, Problem& out);

}  // namespace ff
