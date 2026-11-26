# Single-column figure polish

[Figure on paper page 7](after_in_paper.png) ·
[submission proof](after/submission/main.pdf) ·
[arXiv proof](after/arxiv/main.pdf)

All six scene views are retained in the single-column figure. Native
3.4-inch composition increases the smallest type from about 3.7 pt to
7.14 pt. The four methods share one legible legend row. The real-world
framing is tighter, the orange GEAR-Nav route is emphasized, and stars and
failure crosses have line weights appropriate for the paper column.

The figure is 3.4 × 2.36 inches before its caption. The shorter caption
avoids repeating the legend and retains the scientific interpretation of
the schematic baseline paths and separate oracle-goal simulation recordings.

All source path control points and goal positions are preserved. The figure
contains six photographs, six panel goal stars, twelve real-world paths, and
nine reference failure markers. Before-edit paper sources and figure are
saved here; source hashes, marker counts, and preservation checks are in
`verification.json`.

Both variants compiled twice with pdfLaTeX. The submission remains eight
pages; the version including the supplement remains nine. The unresolved
citation warnings and the small last-page balancing warning are unchanged.
No evaluation table entries changed.

Local masters and their builder are in
`figs/realworld_isaacsim/single_column/`. These source assets and proof
artifacts remain under ignored `/figs/`. Only the paper PDF, its caption,
and the paper README are committed to the paper repository.
