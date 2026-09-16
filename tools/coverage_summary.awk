# coverage_summary.awk — reads `gcov -t` annotated output on stdin and prints
# per-source-file line coverage for files under src/. When the same source
# appears in several binaries (e.g. app + test harness), the union is
# reported: a line counts as covered if any binary executed it.
# Line format: "count:line:source-text" with colon as separator.
BEGIN { FS = ":" }
/^ *-: *0:Source:/ { cur = $4; next }   # field 4 = source path
cur !~ /\/src\//    { next }
{
    line = $2 + 0; if (line < 1) next;
    c = $1; gsub(/ /, "", c); if (c == "-") next;   # "-" = non-executable
    total[cur]++;
    if (c + 0 > 0) covered[cur]++;
}
END {
    for (f in total)
        if (total[f] > 0)
            printf "%s: %.2f%% (%d/%d executable lines)\n", f,
                   100 * covered[f] / total[f], covered[f], total[f];
}
