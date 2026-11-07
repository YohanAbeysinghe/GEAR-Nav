#!/usr/bin/env python3
"""Rebuild Table 4 from the captured sheet values; requires pdflatex and pdftoppm.

Run from any directory:
    .venv/bin/python src/render_table4_exposure_ablation.py

Writes editable LaTeX, a vector PDF, a 300-dpi PNG, and unrounded summary CSV
beside this script. No remote access, training, or inference is performed.
"""

import csv
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent
STEM = "table4_exposure_ablation"
MODELS = ("Qwen3.5 9B", "Qwen3.5 27B")
SETTINGS = (
    ("Video only [SIMULATED]", "Same videos, different QA"),
    ("Question only [SIMULATED]", "Evaluation QA, no video"),
    ("Video+QA", "Video + evaluation QA"),
)
QA_TASKS = (
    ("Text replacement", "ViTeX-Bench"),
    ("Text replacement", "NewsVideoQA"),
    ("Object removal", "Our Dataset"),
    ("Object recoloring", "Our Dataset"),
    ("Object addition", "MVBench"),
    ("Material change", "FiVE (material)"),
    ("Video-segment reordering", "TempCompass"),
)


def summarize(source):
    rows = source["values"][1:]
    assert len(rows) == 120
    for row in rows:
        assert len(row) == 18
        for value in row[7:]:
            count = value * row[4] / 100
            assert math.isclose(count, round(count), abs_tol=1e-8)

    output = []
    for panel, tasks in (
        ("Answer-changing QA", QA_TASKS),
        ("Temporal grounding", (("Temporal grounding", "NExT-GQA"),)),
    ):
        for model in MODELS:
            for raw_setting, label in SETTINGS:
                selected = [r for r in rows if r[0] == model and r[1] == raw_setting]
                originals, edited = [], []
                for task, dataset in tasks:
                    pair = [r for r in selected if (r[2], r[3]) == (task, dataset)]
                    assert len(pair) == 2
                    originals.append(next(r for r in pair if r[6] == "Original"))
                    edited.append(next(r for r in pair if r[6] != "Original"))

                def mean_at(items, epoch):
                    return statistics.mean(r[7 + epoch] for r in items)

                original_0 = mean_at(originals, 0)
                edited_0 = mean_at(edited, 0)
                gap_0 = original_0 - edited_0
                result = {
                    "panel": panel,
                    "model": model,
                    "exposure": label,
                    "task_dataset_pairs": len(tasks),
                    "sample_count_sum": sum(r[4] for r in originals),
                    "original_epoch_0": original_0,
                    "perturbed_epoch_0": edited_0,
                    "original_epoch_10": mean_at(originals, 10),
                    "perturbed_epoch_10": mean_at(edited, 10),
                }
                for epoch in (1, 3, 10):
                    result[f"gap_growth_epoch_{epoch}"] = (
                        mean_at(originals, epoch) - mean_at(edited, epoch) - gap_0
                    )
                output.append(result)
    return output


def latex_rows(rows):
    lines = []
    for _, label in SETTINGS:
        fields = [label]
        for model in MODELS:
            row = next(r for r in rows if r["model"] == model and r["exposure"] == label)
            fields.append(f"${row['gap_growth_epoch_10']:+.1f}$")
        lines.append(" & ".join(fields) + r" \\")
    return "\n".join(lines)


def document(summary):
    # Capture the complete table in a box, then size the PDF to its actual height.
    # This avoids blank page margins and preserves vector text and rules.
    template = r"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage{mathptmx,booktabs,array}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.19}
\newsavebox{\tablebox}
\begin{document}
\setbox\tablebox=\vbox{%
\hsize=85mm
\begin{minipage}{85mm}
\fontsize{9}{11}\selectfont
\textbf{Table 4. Qwen3.5 exposure ablation.}
\par\vspace{6pt}
\fontsize{9}{11}\selectfont
\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrr@{}}
\toprule
Exposure during training & 9B & 27B \\
\midrule
\multicolumn{3}{@{}l}{\textit{Answer-changing QA}} \\
\addlinespace[3pt]
@@QA_ROWS@@
\addlinespace[5pt]
\midrule
\multicolumn{3}{@{}l}{\textit{Temporal grounding}} \\
\addlinespace[3pt]
@@GROUNDING_ROWS@@
\bottomrule
\end{tabular*}
\par\vspace{5pt}
\fontsize{8}{9.5}\selectfont
Values are gap growth at epoch 10 (pp):
$\Delta G_{10}=(O_{10}-E_{10})-(O_0-E_0)$,
where $O/E$ denote original/perturbed scores.
QA is the macro mean over seven task/dataset pairs;
grounding uses R@1 at IoU $\geq 0.7$ with 10\% black padding.
All conditions use video and question at evaluation.
\end{minipage}%
}
\pdfpagewidth=93mm
\pdfpageheight=\dimexpr\ht\tablebox+\dp\tablebox+8mm\relax
\pdfhorigin=0pt
\pdfvorigin=0pt
\shipout\vbox{\offinterlineskip\kern4mm\hbox{\kern4mm\box\tablebox}}
\end{document}
"""
    return template.replace("@@QA_ROWS@@", latex_rows(summary[:6])).replace(
        "@@GROUNDING_ROWS@@", latex_rows(summary[6:])
    )


def run_checked(command, cwd):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    source = json.loads((ROOT / f"{STEM}_source.json").read_text())
    summary = summarize(source)
    with (ROOT / f"{STEM}_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    tex_path = ROOT / f"{STEM}.tex"
    tex_path.write_text(document(summary))
    with tempfile.TemporaryDirectory(prefix="table4-render-") as temporary:
        output = run_checked(
            ["pdflatex", "-halt-on-error", "-interaction=nonstopmode",
             f"-output-directory={temporary}", str(tex_path)], ROOT
        )
        if "Overfull" in output:
            raise RuntimeError("LaTeX reports overflowing content:\n" + output)
        shutil.copyfile(Path(temporary) / f"{STEM}.pdf", ROOT / f"{STEM}.pdf")
    run_checked(
        ["pdftoppm", "-singlefile", "-png", "-r", "300",
         str(ROOT / f"{STEM}.pdf"), str(ROOT / STEM)], ROOT
    )
    print(f"Rendered {ROOT / (STEM + '.pdf')}")
    print(f"Rendered {ROOT / (STEM + '.png')}")


if __name__ == "__main__":
    main()
