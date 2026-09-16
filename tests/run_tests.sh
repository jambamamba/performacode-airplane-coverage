#!/usr/bin/env bash
# run_tests.sh — acceptance fixture harness (plan §9.1).
# Runs every tests/fixtures/INPUT_* in a sandbox with a 10 s timeout and
# diffs OUTPUT against tests/expected/OUTPUT_*. Exit code 0 is asserted
# for every case (ERROR is a correct outcome, not a failure — FR-03/FR-12).
#
# TC-10 (missing INPUT) is synthesized here: run in an empty directory.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${BIN:-$HERE/../build/forest}"
TIMEOUT="${TIMEOUT:-10}"   # seconds, per the task limit
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail=0
run_case() {  # $1 = fixture id, $2 = fixture path ("" for TC-10)
    local id="$1" fixture="$2"
    rm -rf "$WORK/case" && mkdir -p "$WORK/case"
    if [ -n "$fixture" ]; then
        cp "$fixture" "$WORK/case/INPUT"
    fi
    local rc=0
    ( cd "$WORK/case" && timeout "$TIMEOUT" "$BIN" ) >/dev/null 2>&1 || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL $id: exit code $rc (expected 0, FR-12)"
        return 1
    fi
    local got expect_line
    got="$(cat "$WORK/case/OUTPUT" 2>/dev/null)"
    if [ "$id" = "TC-10" ]; then
        expect_line="ERROR"
    else
        expect_line="$(cat "$HERE/expected/OUTPUT_$id" 2>/dev/null)"
        if [ -z "$expect_line" ]; then
            echo "FAIL $id: missing tests/expected/OUTPUT_$id"
            return 1
        fi
    fi
    if [ "$got" != "$expect_line" ]; then
        echo "FAIL $id: OUTPUT mismatch"
        echo "  expected: $expect_line"
        echo "  got:      $got"
        return 1
    fi
    echo "PASS $id: $got"
    return 0
}

for fixture in "$HERE"/fixtures/INPUT_*; do
    id="$(basename "$fixture")"
    id="${id#INPUT_}"
    run_case "$id" "$fixture" || fail=1
done

# TC-10: INPUT missing entirely -> ERROR (if OUTPUT openable), exit 0 (FR-03).
run_case "TC-10" "" || fail=1

echo
if [ "$fail" -eq 0 ]; then
    echo "ALL FIXTURE TESTS PASSED"
else
    echo "FIXTURE TESTS FAILED"
fi
exit "$fail"
