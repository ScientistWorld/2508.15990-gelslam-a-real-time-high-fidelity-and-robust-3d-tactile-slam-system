"""Summarize actual test outputs using the user-specified standardized rank."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics

RT = Path('/home/user/redteam')
TRACKING = 'synthetic_long_horizon_tracking'
LOOPS = 'loop_closure_quality'


def read_candidate(path, name='gelslam_online'):
    scores = json.loads(path.read_text())
    return {exp: val.get('results', {}).get(name, {})
            for exp, val in scores['experiments'].items()}


def main():
    reference = read_candidate(RT / 'reference_original/scores_test.json')
    contract = json.loads((RT / 'reference_original/metric_contract.json').read_text())['experiments']
    candidates = {'original_reference': reference}
    outcomes = {}
    for path in sorted(RT.glob('*/outcome.json')):
        name = path.parent.name
        outcome = json.loads(path.read_text())
        outcomes[name] = outcome
        scores_path = path.parent / 'scores_test.json'
        if outcome.get('test', {}).get('exit_code') == 0 and scores_path.exists():
            candidates[name] = read_candidate(scores_path)
    baseline = read_candidate(RT / 'ref_seed_0/scores_test.json', 'normalflow')
    candidates['frame_to_frame_baseline'] = baseline
    finite = {name: vals for name, vals in candidates.items() if all(
        isinstance(vals.get(exp, {}).get(metric), (float, int)) and
        math.isfinite(vals[exp][metric])
        for exp, spec in contract.items() for metric in spec['metrics'])}
    scales = {}
    for exp, spec in contract.items():
        scales[exp] = {}
        for metric in spec['metrics']:
            values = [v[exp][metric] for v in finite.values()]
            scales[exp][metric] = statistics.pstdev(values) or 1.0
    ranking = {}
    for name, vals in finite.items():
        contributions = {}
        for exp, spec in contract.items():
            contributions[exp] = sum(
                spec['weight'] * abs(setting['coefficient']) *
                (1 if setting['higher_is_better'] else -1) *
                (vals[exp][metric] - reference[exp][metric]) / scales[exp][metric]
                for metric, setting in spec['metrics'].items())
        ranking[name] = {'rank_gain': sum(contributions.values()),
                         'contributions': contributions, 'metrics': vals}
    ordered = sorted(ranking, key=lambda n: ranking[n]['rank_gain'], reverse=True)
    report = {'normalization': 'population standard deviation over the finite cohort listed here',
              'cohort': sorted(finite), 'metric_scales': scales,
              'ranking': {n: ranking[n] for n in ordered},
              'excluded_nonfinite': sorted(set(candidates) - set(finite)),
              'outcomes': outcomes}
    (RT / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    seed_values = [candidates[f'ref_seed_{i}'] for i in range(3)]
    ranges = {exp: {metric: max(v[exp][metric] for v in seed_values) -
                           min(v[exp][metric] for v in seed_values)
                    for metric in spec['metrics']}
              for exp, spec in contract.items()}
    checks = {'seed_metric_ranges': ranges,
              'seed_rank_range': max(ranking[f'ref_seed_{i}']['rank_gain'] for i in range(3)) -
                                 min(ranking[f'ref_seed_{i}']['rank_gain'] for i in range(3)),
              'completed_trials': len(outcomes),
              'finite_rank_cohort_size': len(finite),
              'test_failure_trials': [name for name, val in outcomes.items()
                                     if val.get('test', {}).get('exit_code') != 0],
              'reference_reproduced_exactly': all(v == reference for v in seed_values),
              'all_evaluator_hashes_unchanged': all(
                  val.get('evaluator_sha256_before') == val.get('evaluator_sha256_after')
                  for val in outcomes.values())}
    (RT / 'quality_checks.json').write_text(json.dumps(checks, indent=2) + '\n')
    lines = ['| Run | Rank gain | Rot MAE deg | Trans MAE mm | Loops / valid | False rate |',
             '|---|---:|---:|---:|---:|---:|']
    for name in ordered:
        row = ranking[name]
        tr = row['metrics'][TRACKING]
        lp = row['metrics'][LOOPS]
        lines.append(f"| {name} | {row['rank_gain']:.6f} | {tr['rotation_mae_deg']:.6f} | "
                     f"{tr['translation_mae_mm']:.6f} | {lp['accepted_loops']} / "
                     f"{lp['valid_loops']} | {lp['false_loop_rate']:.6f} |")
    (RT / 'results.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
