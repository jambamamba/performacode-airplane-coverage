// main.cpp — file adapter only: open INPUT/OUTPUT in the current working
// directory and hand the streams to runProgram. All logic lives in the
// core library so the GTest suites can drive the same paths.

#include <fstream>
#include <iostream>

#include "output.h"
#include "run.h"

int main() {
    std::ifstream in("INPUT");
    if (!in.is_open()) {
        std::ofstream out("OUTPUT");
        if (out.is_open()) {
            ff::writeError(out);
        }
        return 0;
    }
    std::ofstream out("OUTPUT");
    if (!out.is_open()) {
        return 1;  // cannot honor the contract at all
    }
    return ff::runProgram(in, out);
}
