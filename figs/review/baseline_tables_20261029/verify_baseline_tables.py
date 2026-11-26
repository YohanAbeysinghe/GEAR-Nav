"""Verify the copied table cells against the supplied VEGA manuscript."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PAPER = ROOT / 'GEAR-Nav Overleaf'
SOURCE = ROOT / 'Overleaf--VEGA/sec/5_results.tex'
METHODS = ('OmniVLA', 'TIC-VLA', 'NaVILA')


def table(text, label):
    for env in re.finditer(
        r'\\begin\{(table\*?|figure\*?)\}([\s\S]*?)\\end\{\1\}', text
    ):
        block = env.group(2)
        if '\\label{' + label + '}' in block:
            return re.search(
                r'\\begin\{tabular\}([\s\S]*?)\\end\{tabular\}', block
            ).group(1)
    raise ValueError(label)


def cells(row):
    return [re.sub(r'\\textbf\{([^{}]*)\}', r'\1', v).strip()
            for v in row.split('&')]


raw = SOURCE.read_text()
active = '\n'.join(line.split('%')[0] for line in raw.splitlines())
target = (PAPER / 'main.tex').read_text()
sim_source = table(active, 'tab:navigation')
real_source = table(active, 'tab:real_results')
parsed = {'navigation': {}, 'real_world': {}}
for row in sim_source.split('\\\\'):
    values = cells(row)
    if len(values) == 5 and values[1] in METHODS:
        parsed['navigation'].setdefault(values[1], []).extend(values[2:])
for method in METHODS:
    row = re.search(r'\b' + re.escape(method) + r'\s*&([\s\S]*?)\\\\',
                    real_source).group(1)
    parsed['real_world'][method] = cells(row)[:9]

comparisons = 0
for kind, label in [('navigation', 'tab:navigation'),
                    ('real_world', 'tab:real_world')]:
    block = table(target, label)
    for method in METHODS:
        row = re.search(r'\b' + re.escape(method) + r'\s*&([\s\S]*?)\\\\',
                        block).group(1)
        values = cells(row)
        expected = parsed[kind][method]
        assert len(values) == len(expected) == 9, (kind, method)
        for value, original in zip(values, expected):
            assert (value == original if original == 'N/A'
                    else Decimal(value) == Decimal(original)), (
                        kind, method, value, original)
            comparisons += 1
    pending = re.search(r'\\textbf\{GEAR-Nav\}\s*&([\s\S]*?)\\\\',
                        block).group(1)
    assert cells(pending) == ['--'] * 9
    assert not re.search(r'(?:\\textbf\{)?VEGA(?:\})?\s*&', block)
assert 'tab:benchmark' not in target
assert 'VEGA-Bench' not in target

receipt = {
    'source_path': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'paper_source_sha256': hashlib.sha256((PAPER / 'main.tex').read_bytes()).hexdigest(),
    'source_labels': {'navigation': 'tab:navigation', 'real_world': 'tab:real_results'},
    'copied_scenarios': [1, 2, 3],
    'baseline_values_verified': comparisons,
    'pending_GEAR_Nav_cells': 18,
    'trials_per_method_per_scenario': {'navigation': 50, 'real_world': 20},
    'rates_scale': [0, 1],
    'clearance_unit': 'm',
    'excluded_source_real_world_scenario': 4,
    'VEGA_result_rows_included': False,
    'VEGA_Bench_table_included': False,
    'results': parsed,
}
(HERE / 'baseline_values.json').write_text(json.dumps(receipt, indent=2) + '\n')
(HERE / 'source_results.tex').write_text(raw)
for build, revision in [('baseline_build', 'HEAD:main.tex'), ('paper_build', None)]:
    out = HERE / build
    out.mkdir(exist_ok=True)
    tex = (subprocess.check_output(['git', '-C', str(PAPER), 'show', revision],
                                   text=True) if revision else target)
    (out / 'main.tex').write_text(tex)
print(f'Verified {comparisons} copied baseline values and 18 pending GEAR-Nav cells.')
print('Source SHA-256:', receipt['source_sha256'])
