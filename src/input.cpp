// input.cpp — lenient parsing per A-2/A-3. See input.h for the policy.

#include "input.h"

#include <istream>
#include <sstream>
#include <string>

namespace ff {
namespace {

template <typename T>
bool readToken(std::istream& in, T& out) {
    if (!(in >> out)) {
        return false;
    }
    return true;
}

}  // namespace

bool readProblem(std::istream& in, Problem& out) {
    double L = 0.0;
    if (!readToken(in, L)) return false;
    // `!(L > 0 && L <= 1000)` also rejects NaN (all comparisons false).
    if (!(L > 0.0 && L <= 1000.0)) return false;
    if (!std::isfinite(L)) return false;

    long long n = 0;
    if (!readToken(in, n)) return false;
    if (n < 1 || n > 100) return false;

    Problem p;
    p.L = L;
    p.flights.reserve(static_cast<size_t>(n));

    for (long long i = 0; i < n; ++i) {
        double x0, y0, x1, y1;
        if (!readToken(in, x0) || !readToken(in, y0) ||
            !readToken(in, x1) || !readToken(in, y1)) {
            return false;
        }
        if (!std::isfinite(x0) || !std::isfinite(y0) ||
            !std::isfinite(x1) || !std::isfinite(y1)) {
            return false;
        }
        VecLine line;
        if (!makeFlightLine(x0, y0, x1, y1, line)) {
            return false;  // coincident entry/exit points
        }
        p.flights.push_back(Flight{line});
    }

    std::string extra;
    if (in >> extra) return false;  // extra trailing tokens are an error (A-2)

    out = std::move(p);
    return true;
}

bool readProblemFromString(const std::string& text, Problem& out) {
    std::istringstream iss(text);
    return readProblem(iss, out);
}

}  // namespace ff
