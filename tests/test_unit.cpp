// test_unit.cpp — function-level unit tests, TC-U01..U22 (plan §9.4).
// Assert-based, C++17 standard library only; each test prints PASS/FAIL.
//
// Build & run:  make test   (see Makefile)

#include <array>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "geometry.h"
#include "input.h"
#include "output.h"
#include "run.h"
#include "scanner.h"

using namespace ff;

namespace {

int g_failures = 0;

struct TestCase {
    const char* name;
    void (*fn)();
};

std::vector<TestCase>& registry() {
    static std::vector<TestCase> r;
    return r;
}

struct Registrar {
    Registrar(const char* name, void (*fn)()) { registry().push_back({name, fn}); }
};

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::cerr << "    CHECK failed: " #cond " (" << __FILE__ << ':'    \
                      << __LINE__ << ")\n";                                    \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

#define CHECK_NEAR(a, b, tol)                                                  \
    do {                                                                       \
        const double va_ = (a), vb_ = (b);                                     \
        if (!(std::abs(va_ - vb_) <= (tol))) {                                 \
            std::cerr << "    CHECK_NEAR failed: " #a " = " << va_ << " vs "   \
                      << #b " = " << vb_ << " (tol " << tol << ") at "         \
                      << __FILE__ << ':' << __LINE__ << "\n";                  \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

// ---- helpers ---------------------------------------------------------------

bool parseOk(const std::string& text, Problem& out) {
    return readProblemFromString(text, out);
}

Problem readProblemOrDie(const std::string& text) {
    Problem p;
    if (!readProblemFromString(text, p)) {
        std::cerr << "    FATAL: fixture parse failed\n";
        std::abort();
    }
    return p;
}

Problem makeProblem(double L, std::vector<std::array<double, 4>> flights) {
    Problem p;
    p.L = L;
    for (const auto& f : flights) {
        VecLine line;
        const bool ok = makeFlightLine(f[0], f[1], f[2], f[3], line);
        static_cast<void>(ok);
        assert(ok);
        p.flights.push_back(Flight{line});
    }
    return p;
}

// Reported points must always be inside the closed square (FR-10).
bool pointInsideSquare(const ScanResult& r, double L) {
    return r.x >= -1e-9 && r.x <= L + 1e-9 && r.y >= -1e-9 && r.y <= L + 1e-9;
}

// ---- TC-U01..U07: readProblem ----------------------------------------------

void tc_u01_valid_input() {
    Problem p;
    CHECK(parseOk("120\n2\n0 0 100 100\n10 20 30 40\n", p));
    CHECK_NEAR(p.L, 120.0, 0.0);
    CHECK(p.flights.size() == 2);
}

void tc_u02_non_numeric_token() {
    Problem p;
    CHECK(!parseOk("100\n1\n0 abc 1 1\n", p));
    // Non-finite literals are real-number tokens but rejected (A-2): the
    // stream may accept them, the range/finite checks must not.
    CHECK(!parseOk("100\n1\n0 inf 1 1\n", p));
    CHECK(!parseOk("100\n1\n0 1e400 1 1\n", p));   // overflow -> inf
    CHECK(!parseOk("100\n1\nnan inf 1 1\n", p));   // non-finite L
    CHECK(!parseOk("100\n1\n0 nan 1 1\n", p));     // non-finite coordinate
}

void tc_u03_missing_token() {
    Problem p;
    CHECK(!parseOk("100\n1\n0 40 100\n", p));  // only 3 of 4 coordinates
    CHECK(!parseOk("100\n", p));               // N present, flights missing
    CHECK(!parseOk("", p));                    // empty file
}

void tc_u04_extra_trailing_token() {
    Problem p;
    CHECK(!parseOk("100\n1\n0 40 100 40\n9 9\n", p));
    CHECK(!parseOk("100\n1\n0 40 100 40\nx\n", p));
}

void tc_u05_L_range() {
    Problem p;
    CHECK(!parseOk("0\n1\n0 0 1 1\n", p));           // L = 0 rejected (FR-05)
    CHECK(!parseOk("-5\n1\n0 0 1 1\n", p));          // negative
    CHECK(!parseOk("1000.001\n1\n0 0 1 1\n", p));    // above max
    CHECK(!parseOk("nan\n1\n0 0 1 1\n", p));         // NaN
    CHECK(!parseOk("inf\n1\n0 0 1 1\n", p));         // inf
    CHECK(parseOk("0.001\n1\n0 0 1 1\n", p));        // minimum accepted
    CHECK(parseOk("1000\n1\n0 0 1 1\n", p));         // maximum accepted
    CHECK(parseOk("17.5\n1\n0 0 1 1\n", p));         // fractional L (A-3)
}

void tc_u06_N_range() {
    Problem p;
    CHECK(!parseOk("100\n0\n", p));                  // N = 0 (FR-06)
    CHECK(!parseOk("100\n101\n", p));                // N = 101
    CHECK(!parseOk("100\nabc\n", p));                // non-numeric
    std::string hundred = "100\n100\n";
    for (int i = 0; i < 100; ++i) hundred += "0 0 1 1\n";
    CHECK(parseOk(hundred, p));                      // N = 100 accepted
    CHECK(p.flights.size() == 100);
}

void tc_u07_coincident_points() {
    Problem p;
    CHECK(!parseOk("100\n1\n5 5 5 5\n", p));            // exactly coincident
    CHECK(parseOk("100\n1\n5 5 5 5.000000001\n", p));   // distinct (tiny)
}

// ---- TC-U08..U10: geometry primitives --------------------------------------

void tc_u08_makeFlightLine() {
    VecLine l;
    CHECK(makeFlightLine(0, 0, 10, 0, l));          // horizontal
    CHECK_NEAR(l.a, 0.0, 1e-15);
    CHECK_NEAR(std::abs(l.b), 1.0, 1e-15);
    CHECK_NEAR(l.c, 0.0, 1e-15);
    CHECK_NEAR(std::abs(l.a * 5 + l.b * 3 + l.c), 3.0, 1e-12);  // dist (5,3)

    CHECK(makeFlightLine(0, 0, 1, 1, l));           // diagonal
    CHECK_NEAR(l.a * l.a + l.b * l.b, 1.0, 1e-15);  // normalized (DR-01)
    CHECK_NEAR(std::abs(l.a * 1 + l.b * 0 + l.c), std::sqrt(0.5), 1e-12);

    CHECK(!makeFlightLine(3, 7, 3, 7, l));          // coincident -> error
    VecLine dummy;
    CHECK(!makeFlightLine(std::numeric_limits<double>::quiet_NaN(), 0, 1, 1,
                          dummy));
}

void tc_u09_clipLineToSquare() {
    // Horizontal line through the middle: full width crossing.
    VecLine l{0.0, 1.0, -50.0};  // y = 50
    auto s = clipLineToSquare(l, 100.0);
    CHECK(s.has_value());
    CHECK_NEAR(s->t1 - s->t0, 100.0, 1e-9);

    // Vertical line to the right of the square: never enters.
    VecLine out{1.0, 0.0, -150.0};  // x = 150
    CHECK(!clipLineToSquare(out, 100.0).has_value());

    // Line touching only one corner: degenerate segment kept.
    VecLine diag{std::sqrt(0.5), std::sqrt(0.5), -200.0 / std::sqrt(2.0)};
    auto corner = clipLineToSquare(diag, 100.0);
    CHECK(corner.has_value());
    CHECK(corner->t1 - corner->t0 < 1e-9);

    // Square-edge line: lies exactly on the border.
    VecLine edge{0.0, 1.0, 0.0};  // y = 0
    auto e = clipLineToSquare(edge, 100.0);
    CHECK(e.has_value());
    CHECK_NEAR(e->t1 - e->t0, 100.0, 1e-9);

    // Corner touch buried in FP rounding noise: with a/b/c a few ULPs off
    // the analytic values, the slab intersection ends with hi < lo but
    // inside the 1e-12 tolerance, and the guard must keep the degenerate
    // segment. Search ULPs around the analytic corner-touch line so the
    // test adapts to the platform's rounding (pinned toolchain, §8.2).
    auto rawHilo = [](const VecLine& l, double L) {
        const double qx = -l.c * l.a, qy = -l.c * l.b;
        const double ddx = -l.b, ddy = l.a;
        double lo = 0.0, hi = 0.0;
        bool have = false;
        if (std::abs(ddx) >= 1e-15) {
            double ta = (0 - qx) / ddx, tb = (L - qx) / ddx;
            if (ta > tb) std::swap(ta, tb);
            lo = ta; hi = tb; have = true;
        }
        if (std::abs(ddy) >= 1e-15) {
            double ta = (0 - qy) / ddy, tb = (L - qy) / ddy;
            if (ta > tb) std::swap(ta, tb);
            if (!have) { lo = ta; hi = tb; }
            else { lo = std::max(lo, ta); hi = std::min(hi, tb); }
        }
        return hi - lo;
    };
    const double s2 = std::sqrt(0.5);
    VecLine base{s2, s2, -200.0 / std::sqrt(2.0)};  // touches corner (100, 100)
    bool guardHit = false;
    for (int kb = -200; kb <= 200 && !guardHit; ++kb) {
        VecLine l = base;
        for (int i = 0; i < (kb < 0 ? -kb : kb); ++i)
            l.b = std::nextafter(l.b, kb < 0 ? 0.0 : 1.0);
        for (int kc = -200; kc <= 200 && !guardHit; ++kc) {
            VecLine m = l;
            for (int i = 0; i < (kc < 0 ? -kc : kc); ++i)
                m.c = std::nextafter(m.c, kc < 0 ? 1e300 : -1e300);
            const double d = rawHilo(m, 100.0);
            if (d < 0.0 && d > -1e-12) {
                // Raw interval is an FP-noise-thin negative sliver: only the
                // corner-touch guard can turn this into a segment.
                auto g = clipLineToSquare(m, 100.0);
                CHECK(g.has_value());
                CHECK(g->t1 - g->t0 <= 1e-12);
                guardHit = true;
            }
        }
    }
    CHECK(guardHit);
}

void tc_u10_intersectLines() {
    VecLine x0{1.0, 0.0, 0.0};    // x = 0
    VecLine y0{0.0, 1.0, 0.0};    // y = 0
    auto p = intersectLines(x0, y0);
    CHECK(p.has_value());
    CHECK_NEAR(p->x, 0.0, 1e-15);
    CHECK_NEAR(p->y, 0.0, 1e-15);

    VecLine x50{1.0, 0.0, -50.0};
    auto p2 = intersectLines(x50, y0);
    CHECK(p2.has_value());
    CHECK_NEAR(p2->x, 50.0, 1e-15);

    VecLine y7{0.0, 1.0, -7.0};
    CHECK(!intersectLines(y0, y7).has_value());     // parallel -> nullopt
}

// ---- TC-U11..U14, U21, U22: scanner behaviour ------------------------------

void tc_u11_reports_uncovered_point() {
    // L = 1000, one horizontal band |y - 500| <= 50: corners unviewed.
    Problem p = makeProblem(1000.0, {{0.0, 500.0, 1000.0, 500.0}});
    const ScanResult r = scanSquare(p);
    CHECK(!r.covered);
    CHECK(pointInsideSquare(r, 1000.0));
    CHECK(r.margin > 1e-6);
    // The point really is unviewed (independent recomputation).
    CHECK(minDistanceToFlights(p, r.x, r.y) > 50.0);
}

void tc_u12_fully_covered_ok() {
    // Two crossing bands that each span the whole square.
    Problem cross = makeProblem(
        100.0, {{50.0, -50.0, 50.0, 150.0}, {150.0, 50.0, -50.0, 50.0}});
    CHECK(scanSquare(cross).covered);

    // Diagonal flight in L = 70 square: farthest corner at 70/sqrt(2) < 50.
    Problem diag = makeProblem(70.0, {{0.0, 0.0, 70.0, 70.0}});
    CHECK(scanSquare(diag).covered);
}

void tc_u13_points_stay_inside_square() {
    // Tiny square, flight whose infinite line truly misses it: every poke
    // beside the square edges that leaves the square must be discarded
    // (MC/DC condition A). (1000,1000)->(2000,2000) would NOT qualify: the
    // line y = x passes through the corner (0, 0) of the tiny square.
    Problem p = makeProblem(0.001, {{1000.0, 1000.0, 2000.0, 1000.0}});
    const ScanResult r = scanSquare(p);
    CHECK(!r.covered);
    CHECK(pointInsideSquare(r, 0.001));

    // Flight along the bottom edge: pokes below y = 0 are outside.
    Problem edge = makeProblem(100.0, {{0.0, 0.0, 100.0, 0.0}});
    const ScanResult r2 = scanSquare(edge);
    CHECK(!r2.covered);
    CHECK(pointInsideSquare(r2, 100.0));
}

void tc_u14_best_margin_wins() {
    // L = 1000, flight at y = 100: uncovered regions below y < 50 and above
    // y > 150. Largest margin is at the top border (~849.9999 km), so the
    // max-margin rule (DR-06) must pick the top, not the bottom sliver.
    Problem p = makeProblem(1000.0, {{0.0, 100.0, 1000.0, 100.0}});
    const ScanResult r = scanSquare(p);
    CHECK(!r.covered);
    CHECK(r.y > 999.0);
    CHECK_NEAR(r.margin, 849.9999, 1e-3);
    CHECK_NEAR(minDistanceToFlights(p, r.x, r.y), r.margin + 50.0, 1e-6);
}

void tc_u21_sliver_wedge_regression() {
    // TC-14: two flights at angle 1e-6 rad; the uncovered wedge between their
    // bands is ~0.1 m thick near x = 0 — invisible to any 0.5 km grid sample.
    Problem p = makeProblem(
        1000.0, {{0.0, 500.0, 1000.0, 500.0},
                 {0.0, 450.0001, 1000.0, 450.0001 + 0.001}});
    const ScanResult r = scanSquare(p);
    CHECK(!r.covered);
    CHECK(pointInsideSquare(r, 1000.0));
    CHECK(minDistanceToFlights(p, r.x, r.y) > 50.0);
}

void tc_u22_vertex_counterexample_regression() {
    // TC-15: three flights form a triangle of inradius 80 in L = 1000. The
    // inner hole's vertices all lie exactly 50 km from a flight line (hence
    // "covered"), yet the hole exists — vertex-only checks would print OK.
    Problem p = makeProblem(1000.0, {{0.0, 180.0, 1000.0, 180.0},
                                     {-180.0, 0.0, 1180.0, 1000.0},
                                     {1000.0, 0.0, 0.0, 1000.0}});
    const ScanResult r = scanSquare(p);
    CHECK(!r.covered);
    CHECK(pointInsideSquare(r, 1000.0));
    CHECK(minDistanceToFlights(p, r.x, r.y) > 50.0);
}

// ---- TC-U15..U20: misc units -----------------------------------------------

void tc_u15_minDistanceToFlights() {
    Problem p = makeProblem(100.0, {{0.0, 0.0, 10.0, 0.0},   // y = 0
                                    {0.0, 30.0, 10.0, 30.0}});  // y = 30
    CHECK_NEAR(minDistanceToFlights(p, 5.0, 10.0), 10.0, 1e-12);
    CHECK_NEAR(minDistanceToFlights(p, 5.0, 16.0), 14.0, 1e-12);
}

void tc_u16_output_formatting() {
    std::ostringstream os;
    writeOk(os);
    CHECK(os.str() == "OK\n");

    std::ostringstream es;
    writeError(es);
    CHECK(es.str() == "ERROR\n");

    std::ostringstream ps;
    writePoint(ps, 12.34, 56.78);
    CHECK(ps.str() == "12.340000 56.780000\n");  // FR-11: 6 fixed decimals
}

void tc_u17_runProgram_dispatch() {
    // L = 70 diagonal: farthest corner at 70/sqrt(2) ~= 49.5 km < 50 -> OK.
    std::istringstream in_ok("70\n1\n0 0 70 70\n");
    std::ostringstream out_ok;
    CHECK(runProgram(in_ok, out_ok) == 0);
    CHECK(out_ok.str() == "OK\n");

    std::istringstream in_bad("100\n1\n5 5 5 5\n");
    std::ostringstream out_bad;
    CHECK(runProgram(in_bad, out_bad) == 0);       // ERROR is exit code 0
    CHECK(out_bad.str() == "ERROR\n");

    std::istringstream in_gap("100\n2\n0 40 100 40\n40 0 40 100\n");
    std::ostringstream out_gap;
    CHECK(runProgram(in_gap, out_gap) == 0);
    // One line, two fixed-point coordinates inside the square.
    double x = -1, y = -1;
    std::istringstream ps(out_gap.str());
    CHECK(static_cast<bool>(ps >> x >> y));
    CHECK(x >= 0 && x <= 100 && y >= 0 && y <= 100);
    CHECK(minDistanceToFlights(readProblemOrDie("100\n2\n0 40 100 40\n40 0 40 100\n"),
                               x, y) > 50.0);
}

void tc_u18_boundary_exact_visibility() {
    // TC-03 shape: every square corner exactly 50 km from the flight line.
    // Boundary points are visible (A-4) -> the square is fully viewed.
    Problem p = makeProblem(100.0, {{0.0, 50.0, 100.0, 50.0}});
    CHECK(scanSquare(p).covered);
}

void tc_u19_near_degenerate_flight() {
    // 1e-9 km between entry and exit: valid per FR-07. The resulting line is
    // y = 50, whose band edges land exactly on the square borders y = 0 and
    // y = 100, so the square is exactly covered (boundary visible, A-4).
    Problem p;
    CHECK(parseOk("100\n1\n5 50 5.000000001 50\n", p));
    CHECK(scanSquare(p).covered);
}

void tc_u20_determinism() {
    Problem p = makeProblem(1000.0, {{0.0, 180.0, 1000.0, 180.0},
                                     {-180.0, 0.0, 1180.0, 1000.0},
                                     {1000.0, 0.0, 0.0, 1000.0}});
    const ScanResult a = scanSquare(p);
    const ScanResult b = scanSquare(p);
    CHECK(a.covered == b.covered);
    CHECK(a.x == b.x && a.y == b.y);          // bitwise identical (DR-10)
    CHECK(a.margin == b.margin);
}

// ---- registration -----------------------------------------------------------

#define TEST(name)                                   \
    void name();                                     \
    Registrar reg_##name(#name, &name);              \
    void name()

TEST(tc_u01_valid_input);
TEST(tc_u02_non_numeric_token);
TEST(tc_u03_missing_token);
TEST(tc_u04_extra_trailing_token);
TEST(tc_u05_L_range);
TEST(tc_u06_N_range);
TEST(tc_u07_coincident_points);
TEST(tc_u08_makeFlightLine);
TEST(tc_u09_clipLineToSquare);
TEST(tc_u10_intersectLines);
TEST(tc_u11_reports_uncovered_point);
TEST(tc_u12_fully_covered_ok);
TEST(tc_u13_points_stay_inside_square);
TEST(tc_u14_best_margin_wins);
TEST(tc_u15_minDistanceToFlights);
TEST(tc_u16_output_formatting);
TEST(tc_u17_runProgram_dispatch);
TEST(tc_u18_boundary_exact_visibility);
TEST(tc_u19_near_degenerate_flight);
TEST(tc_u20_determinism);
TEST(tc_u21_sliver_wedge_regression);
TEST(tc_u22_vertex_counterexample_regression);

}  // namespace

int main() {
    for (const TestCase& t : registry()) {
        std::cout << "[ RUN  ] " << t.name << std::endl;
        const int before = g_failures;
        t.fn();
        std::cout << (g_failures == before ? "[  OK  ] " : "[ FAIL ] ")
                  << t.name << std::endl;
    }
    std::cout << (g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED")
              << " (" << registry().size() << " tests, " << g_failures
              << " failed checks)" << std::endl;
    return g_failures == 0 ? 0 : 1;
}
