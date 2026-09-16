# Makefile — Forest Fire (Task 1) build and verification targets.
# Toolchain is pinned in BUILD_RECORD.md; a compiler bump is a
# re-verification event (PROJECT_PLAN.md §8.2).

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Wpedantic
SANFLAGS  = -std=c++17 -O1 -g -fsanitize=address,undefined \
            -fno-omit-frame-pointer -Wall -Wextra -Wpedantic
COVFLAGS  = -std=c++17 -O0 -g --coverage -Wall -Wextra -Wpedantic

SRC := src/main.cpp src/input.cpp src/geometry.cpp src/scanner.cpp \
       src/output.cpp src/run.cpp
HDR := src/input.h src/geometry.h src/scanner.h src/output.h src/run.h

BIN     := build/forest
BIN_SAN := build/forest.san
REPORTS := build/reports

# Static-analysis toolchain (see BUILD_RECORD.md §4). Versions are pinned in
# the report headers; a tool bump is a re-review event, not a re-verification
# event (they are development tools, not part of the graded artifact).
CLANG_FORMAT ?= $(HOME)/.local/bin/clang-format
CLANG_TIDY   ?= $(HOME)/.local/bin/clang-tidy
CLANG_QUERY  ?= clang-query-20
VALGRIND     ?= valgrind
# Optional overrides for a non-installed valgrind, e.g. a local extraction:
#   make valgrind VALGRIND_BIN=/tmp/vg/root/usr/bin/valgrind \
#                VALGRIND_LIB=/tmp/vg/root/usr/libexec/valgrind

# Both coverage builds use the program name `forest` (in separate dirs) so
# gcov-tool merge can overlay their counters.
COV_FIX   := build/cov/fixture
COV_UNIT  := build/cov/unit
COV_MERGED := build/cov/merged

.PHONY: all test fixtures coverage report sanitize timing oracle cucumber \
        cucumber-smoke gherkin-report format format-check static query \
        valgrind analysis clean

all: $(BIN)

$(BIN): $(SRC) $(HDR)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $(SRC)

build/test_unit: tests/test_unit.cpp $(filter-out src/main.cpp,$(SRC)) $(HDR)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -Isrc -o $@ tests/test_unit.cpp \
	    $(filter-out src/main.cpp,$(SRC))

# Unit tests (TC-U01..U22) + acceptance fixtures (TC-01..TC-17, TC-10).
test: $(BIN) build/test_unit
	./build/test_unit
	./tests/run_tests.sh

# Regenerate tests/expected/* from the current binary, then validate each
# with the independent oracle. Only for reviewing a deliberate change.
fixtures: $(BIN)
	@set -e; BIN="$(CURDIR)/$(BIN)"; \
	 tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	 for f in tests/fixtures/INPUT_*; do \
	   id=$$(basename "$$f" | sed 's/INPUT_//'); \
	   cp "$$f" "$$tmp/INPUT"; \
	   (cd "$$tmp" && timeout 10 "$$BIN"); \
	   cp "$$tmp/OUTPUT" "tests/expected/OUTPUT_$$id"; \
	 done; \
	 for f in tests/fixtures/INPUT_*; do \
	   id=$$(basename "$$f" | sed 's/INPUT_//'); \
	   python3 tools/verify_random.py verify "$$f" \
	       "tests/expected/OUTPUT_$$id" || exit 1; \
	 done

$(COV_FIX)/forest: $(SRC) $(HDR)
	@mkdir -p $(COV_FIX)
	$(CXX) $(COVFLAGS) -o $(CURDIR)/$(COV_FIX)/forest \
	    $(addprefix $(CURDIR)/,$(SRC))

$(COV_UNIT)/forest: $(CURDIR)/tests/test_unit.cpp $(SRC) $(HDR)
	@mkdir -p $(COV_UNIT)
	$(CXX) $(COVFLAGS) -I$(CURDIR)/src -o $(CURDIR)/$(COV_UNIT)/forest \
	    $(CURDIR)/tests/test_unit.cpp \
	    $(addprefix $(CURDIR)/,$(filter-out src/main.cpp,$(SRC)))

# Structural coverage (§9.5): acceptance fixtures (incl. TC-10 missing INPUT
# and an unwritable-cwd run) + unit tests. Both binaries are named `forest`,
# so gcov-tool merge overlays their counters; the summary reports the union.
coverage: $(COV_FIX)/forest $(COV_UNIT)/forest
	@rm -rf $(COV_MERGED) build/coverage
	@BIN="$(CURDIR)/$(COV_FIX)/forest"; \
	 tmp=$$(mktemp -d); \
	 for f in tests/fixtures/INPUT_*; do \
	   cp "$$f" "$$tmp/INPUT"; (cd "$$tmp" && timeout 10 "$$BIN"); \
	 done; \
	 d=$$(mktemp -d); (cd "$$d" && timeout 10 "$$BIN"); \
	 d=$$(mktemp -d); cp tests/fixtures/INPUT_TC-01 "$$d/INPUT"; \
	 chmod 555 "$$d"; (cd "$$d" && timeout 10 "$$BIN") || true; \
	 chmod 755 "$$d"; rm -rf "$$tmp" "$$d"
	@$(COV_UNIT)/forest >/dev/null
	gcov-tool merge -o $(COV_MERGED) $(COV_FIX) $(COV_UNIT)
	@cp $(COV_MERGED)/forest-*.gcda $(COV_FIX)/
	@echo "--- src/ line coverage (fixtures + unit tests, merged) ---"
	@gcov -t $(COV_FIX)/forest-*.gcda 2>/dev/null \
	   | awk -f tools/coverage_summary.awk | sort

# Human-readable annotated .gcov files for review.
report: coverage
	@mkdir -p build/coverage
	@for g in $(COV_FIX)/forest-*.gcda; do \
	   gcov -t "$$g" \
	     > "build/coverage/$$(basename "$$g" .gcda).gcov" 2>/dev/null \
	     || true; \
	 done
	@echo "Annotated .gcov files in build/coverage/"

sanitize: $(BIN_SAN)
	@set -e; BIN="$(CURDIR)/$(BIN_SAN)"; tmp=$$(mktemp -d); \
	 trap 'rm -rf "$$tmp"' EXIT; \
	 for f in tests/fixtures/INPUT_*; do \
	   d=$$(mktemp -d "$$tmp/run.XXXX"); \
	   cp "$$f" "$$d/INPUT"; \
	   (cd "$$d" && ASAN_OPTIONS=detect_leaks=1 timeout 30 "$$BIN") \
	     || exit 1; \
	 done; \
	 echo "ASan+UBSan clean on all fixtures (TC-19)"

$(BIN_SAN): $(SRC) $(HDR)
	@mkdir -p build
	$(CXX) $(SANFLAGS) -o $@ $(SRC)

timing: $(BIN)
	@echo "TC-04/TC-17: N=100 stress runs (limit 10 s each)"
	@set -e; for tc in TC-04 TC-17; do \
	   tmp=$$(mktemp -d); \
	   cp tests/fixtures/INPUT_$$tc "$$tmp/INPUT"; \
	   ( cd "$$tmp" && /usr/bin/time -f "$$tc: %e s wall, %M KB peak RSS" \
	     timeout 10 "$(CURDIR)/$(BIN)" >/dev/null ) 2>&1; \
	   rm -rf "$$tmp"; \
	 done

oracle: $(BIN)
	python3 tools/verify_random.py random --bin $(BIN) --trials 50

# Gherkin/BDD suite: scenarios, PNG coverage diagrams, timing table
cucumber: $(BIN)
	python3 tools/cucumber.py --bin $(BIN)

cucumber-smoke: $(BIN)
	python3 tools/cucumber.py --bin $(BIN) --tags @timing --no-images

# Full Gherkin run + tracked images + BUILD_RECORD.md report regeneration.
gherkin-report: $(BIN)
	python3 tools/cucumber.py --bin $(BIN) --images-dir assets/cucumber
	python3 tools/gherkin_report.py

clean:
	rm -rf build *.gcda *.gcno *.gcov

# --------------------------------------------------------------------------
# Analysis & reports (docs/: DAL_ANALYSIS.md, COVERAGE_ANALYSIS.md,
# EDGE_CASES.md). Reports land in build/reports/.
# --------------------------------------------------------------------------

# clang-tidy and clang-query need a compile database; generated from the same
# flags as the graded build so the analysis sees exactly the graded code.
compile_commands.json: Makefile $(SRC)
	@echo '[' > $@.tmp
	@sep=""; \
	 for f in $(SRC); do \
	   printf '%s{ "directory": "%s", "command": "%s -std=c++17 -Wall -Wextra -Wpedantic -I%s/src -c %s/%s -o /dev/null", "file": "%s/%s" }\n' \
	     "$$sep" "$(CURDIR)" "$(CXX)" "$(CURDIR)" "$(CURDIR)" "$$f" "$(CURDIR)" "$$f" >> $@.tmp; \
	   sep=","; \
	 done
	@echo ']' >> $@.tmp && mv $@.tmp $@

# Report only (no in-place changes): fails when a file deviates from the style.
format-check: .clang-format $(SRC) $(HDR) | $(REPORTS)
	@rm -f $(REPORTS)/clang-format.log
	@status=0; for f in $(SRC) $(HDR); do \
	   $(CLANG_FORMAT) --dry-run --Werror "$$f" >>$(REPORTS)/clang-format.log 2>&1 \
	     || status=1; \
	 done; \
	 if [ $$status -eq 0 ]; then echo "clang-format: all files conform"; \
	 else echo "clang-format: deviations found -> $(REPORTS)/clang-format.log"; fi; \
	 exit $$status

# Apply the style in place (explicit action — review the diff afterwards).
format: .clang-format $(SRC) $(HDR)
	@$(CLANG_FORMAT) -i $(SRC) $(HDR)
	@echo "clang-format applied to src/ headers and sources"

# Full static analysis over the graded TUs. Findings are triaged in
# docs/COVERAGE_ANALYSIS.md §5; the report is a review artifact.
static: compile_commands.json .clang-tidy $(SRC) $(HDR) | $(REPORTS)
	@$(CLANG_TIDY) --config-file=.clang-tidy -p $(CURDIR) $(SRC) \
	   > $(REPORTS)/clang-tidy.log 2>&1 || true
	@n=$$(grep -c "warning:" $(REPORTS)/clang-tidy.log || true); \
	 echo "clang-tidy: $$n findings -> $(REPORTS)/clang-tidy.log"; \
	 grep "warning:" $(REPORTS)/clang-tidy.log | sed 's/^.*warning: /  /' | sort | uniq -c | sort -rn | head -12

# AST structural queries: FP equality in decisions, C-style casts, magic
# literals, branch structure, gotos. Output triaged in docs/COVERAGE_ANALYSIS.md §6.
query: compile_commands.json tools/queries/checks.query $(SRC) | $(REPORTS)
	@rm -f $(REPORTS)/clang-query.log
	@for f in $(SRC); do \
	   echo "=== $$f ===" >> $(REPORTS)/clang-query.log; \
	   $(CLANG_QUERY) -p $(CURDIR) -f tools/queries/checks.query "$$f" \
	     >> $(REPORTS)/clang-query.log 2>&1 || true; \
	 done
	@echo "clang-query report -> $(REPORTS)/clang-query.log"

# Valgrind memcheck (+leakcheck) over every acceptance fixture and the N=100
# stress inputs. Exit code 9 on any finding.
valgrind: $(BIN)
	@vg="$(VALGRIND_BIN)"; [ -n "$$vg" ] || vg="$(VALGRIND)"; \
	 command -v "$$vg" >/dev/null 2>&1 || { \
	   echo "valgrind not found. Install it, or run e.g.:"; \
	   echo "  make valgrind VALGRIND_BIN=/tmp/vg/root/usr/bin/valgrind VALGRIND_LIB=/tmp/vg/root/usr/libexec/valgrind"; \
	   exit 1; }; \
	 set -e; tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	 : > $(REPORTS)/valgrind.log 2>/dev/null || { mkdir -p $(REPORTS); : > $(REPORTS)/valgrind.log; }; \
	 for f in tests/fixtures/INPUT_*; do \
	   d=$$(mktemp -d "$$tmp/run.XXXX"); cp "$$f" "$$d/INPUT"; \
	   id=$$(basename "$$f"); \
	   ( cd "$$d" && "$$vg" -q --tool=memcheck --leak-check=full \ 
	     --error-exitcode=9 "$(CURDIR)/$(BIN)" >>"$(CURDIR)/$(REPORTS)/valgrind.log" 2>&1 ) \
	     || { echo "valgrind: FAILURES on $$id (see $(REPORTS)/valgrind.log)"; exit 1; }; \
	   echo "  $$id: clean"; \
	 done; \
	 echo "valgrind memcheck: clean on all fixtures ($(REPORTS)/valgrind.log)"

# Aggregate: everything the review needs, reports in build/reports/.
analysis: format-check static query valgrind
	@echo "--- analysis complete; reports in $(REPORTS)/ ---"

$(REPORTS):
	@mkdir -p $(REPORTS)
