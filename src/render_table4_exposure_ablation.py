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
    for index, row in enumerate(rows):
        if index == 3:
            lines.append(r"\addlinespace[4pt]")
        model = row["model"].split()[-1] if index % 3 == 0 else ""
        fields = [model, row["exposure"]]
        fields.extend(f"{row[k]:.1f}" for k in ("original_epoch_10", "perturbed_epoch_10"))
        fields.extend(
            f"${row[f'gap_growth_epoch_{e}']:+.1f}$" for e in (1, 3, 10)
        )
        lines.append(" & ".join(fields) + r" \\")
    return "\n".join(lines)


def document(summary):
    # Capture the complete table in a box, then size the PDF to its actual height.
    # This avoids blank page margins and preserves vector text and rules.
    template = r"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage{mathptmx,booktabs,array,xcolor}
\pagestyle{empty}
\definecolor{panelblue}{RGB}{37,66,92}
\setlength{\parindent}{0pt}
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.19}
\newsavebox{\tablebox}
\begin{document}
\setbox\tablebox=\vbox{%
\hsize=180mm
\begin{minipage}{180mm}
\fontsize{10}{12}\selectfont
\textbf{Table 4. Effect of exposure modality on original and perturbed performance.}
\par\vspace{6pt}
\fontsize{9}{11}\selectfont
\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}llrrrrr@{}}
\toprule
\shortstack[l]{Qwen3.5\\model} & Exposure during training &
\multicolumn{2}{c}{Epoch 10 (\%)} &
\multicolumn{3}{c}{Gap growth $\Delta G_e$ (pp)} \\
\cmidrule(lr){3-4}\cmidrule(l){5-7}
& & Original & Perturbed & $e=1$ & $e=3$ & $e=10$ \\
\midrule
\multicolumn{7}{@{}l}{\color{panelblue}\textbf{(a) Answer-changing QA: macro accuracy over seven task/dataset pairs}} \\
\addlinespace[3pt]
@@QA_ROWS@@
\addlinespace[5pt]
\midrule
\multicolumn{7}{@{}l}{\color{panelblue}\textbf{(b) Temporal grounding: R@1 at IoU $\geq 0.7$ ($N=5{,}553$)}} \\
\addlinespace[3pt]
@@GROUNDING_ROWS@@
\bottomrule
\end{tabular*}
\par\vspace{7pt}
\fontsize{8.2}{10.3}\selectfont
\textbf{Gap growth.}
$\Delta G_e=(O_e-E_e)-(O_0-E_0)$, where $O_e$ and $E_e$ are original and
perturbed scores at epoch $e$. Positive values indicate a widening gap relative
to the starting checkpoint; they are descriptive effects, not calibrated
detection performance. Values are rounded after calculation.
\par\vspace{4pt}
\textbf{Exposure and evaluation.}
All conditions receive video and question at evaluation. QA-only exposure
includes evaluation questions and answer targets. Same-video exposure uses
different QA. Panel (a) weights each task/dataset pair equally and excludes
grounding and both shuffling controls. Panel (b) uses 10\% appended black
padding for perturbed videos. No independent-run uncertainty is reported.
\par\vspace{4pt}
\textbf{Starting scores ($O_0/E_0$).}
QA: 73.3/66.8\% (9B), 75.9/70.4\% (27B).
Grounding: 18.5/18.5\% (9B), 18.4/18.4\% (27B).
\par\vspace{4pt}
\textbf{Task-level exception.}
For 27B material changes under video+QA exposure, edited accuracy improves
from 72\% to 86\%, while original accuracy rises from 78\% to 98\%.
Gap growth is only $+6$ pp: exposure does not uniformly reduce perturbed
performance.
\end{minipage}%
}
\pdfpagewidth=196mm
\pdfpageheight=\dimexpr\ht\tablebox+\dp\tablebox+16mm\relax
\pdfhorigin=0pt
\pdfvorigin=0pt
\shipout\vbox{\offinterlineskip\kern8mm\hbox{\kern8mm\box\tablebox}}
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
