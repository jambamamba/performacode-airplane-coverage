// output.cpp — see output.h.

#include "output.h"

#include <iomanip>
#include <ostream>

namespace ff {

void writeOk(std::ostream& out) { out << "OK\n"; }

void writeError(std::ostream& out) { out << "ERROR\n"; }

void writePoint(std::ostream& out, double x, double y) {
    out << std::fixed << std::setprecision(6) << x << ' ' << y << '\n';
}

}  // namespace ff
