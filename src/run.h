#pragma once
// run.h — wiring of one full program pass over an istream/ostream
// (FR-01..FR-12 dispatch). main() is a thin file adapter around this.

#include <iosfwd>

namespace ff {

// Returns the process exit code (0 on any completed pass; ERROR outputs are
// a *correct* outcome, not a failure). Never throws.
int runProgram(std::istream& in, std::ostream& out);

}  // namespace ff
