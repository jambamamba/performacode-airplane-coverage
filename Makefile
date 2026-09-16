# Makefile — Forest Fire (Task 1) build and verification targets.
# Toolchain is pinned in BUILD_RECORD.md; a compiler bump is a
# re-verification event (project-plan.md §8.2).

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

# Both coverage builds use the program name `forest` (in separate dirs) so
# gcov-tool merge can overlay their counters.
COV_FIX   := build/cov/fixture
COV_UNIT  := build/cov/unit
COV_MERGED := build/cov/merged

.PHONY: all test fixtures coverage report sanitize timing oracle cucumber clean

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

clean:
	rm -rf build *.gcda *.gcno *.gcov
