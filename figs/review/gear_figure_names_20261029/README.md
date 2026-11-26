# GEAR figure filenames and combined paper figure

All seven PDFs in the paper's `fig/` folder now use the `gear_` prefix.
The six renamed files are byte-identical to their previous versions;
`renames.json` records the mapping and hashes. LaTeX and README references
use the new names. The previously untracked combined PDF already in the
paper folder matched the verified local master and was retained.

The combined real-world and navigation figure replaces the real-world-only
placement. It is Figure 4 on page 7, spanning the full text width with an
explicit caption and references to its two rows. The earlier real-world-only
PDF is retained as `gear_realworld.pdf`, and is not included separately.

- [Submission proof](after/submission/main.pdf): eight pages, unchanged.
- [arXiv proof](after/arxiv/main.pdf): nine pages including the supplement, unchanged.
- [Figure on the paper page](combined_in_paper.png): visually checked.
- [Verification](verification.json): unchanged table blocks, renamed file
  hashes, and no new citation warnings. Existing unresolved citations remain.

Both variants compiled twice with pdfLaTeX. Neither final proof has an
overfull box. Sources and build logs remain here, outside the paper repository.
All files in this review directory remain local under ignored `/figs/`.
