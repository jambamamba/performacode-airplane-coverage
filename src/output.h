#pragma once
// output.h — OUTPUT formatting (FR-10..FR-12).
// Uncovered points are printed with 6 decimals (1 mm), well inside the
// 1 m accuracy requirement.

#include <iosfwd>

namespace ff {

void writeOk(std::ostream& out);      // "OK\n"
void writeError(std::ostream& out);   // "ERROR\n"
void writePoint(std::ostream& out, double x, double y);

}  // namespace ff
