// run.cpp — read INPUT, scan, write OUTPUT. Defensive: any unexpected
// exception (e.g. bad_alloc) degrades to ERROR, never a crash (§7.3).

#include "run.h"

#include <exception>
#include <istream>
#include <ostream>

#include "input.h"
#include "output.h"
#include "scanner.h"

namespace ff {

int runProgram(std::istream& in, std::ostream& out) {
    Problem problem;
    if (!readProblem(in, problem)) {
        writeError(out);
        return 0;
    }
    try {
        const ScanResult r = scanSquare(problem);
        if (r.covered) {
            writeOk(out);
        } else {
            writePoint(out, r.x, r.y);
        }
    } catch (...) {
        writeError(out);
    }
    return 0;
}

}  // namespace ff
