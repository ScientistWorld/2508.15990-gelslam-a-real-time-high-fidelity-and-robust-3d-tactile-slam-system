"""Report the final cohort, correct normalized ranks, and paired uncertainty.

This is audit tooling only. The gym ranks exclusively the metric dictionaries
written by the two official evaluation entry points.
"""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT/'eval/test/hardening_results'
REF = 'gelslam_online'


def load(p):
    return json.loads(p.read_text())


def methods(scores):
    names = set()
    for exp in scores['experiments'].values():
        names.update(exp['results'])
    return sorted(names)


def rank(scores, spec, cohort=None):
    names = methods(scores)
    cohort = names if cohort is None else cohort
    stds = {}
    gains = dict.fromkeys(names, 0.0)
    for exp, ex in spec.items():
        for metric, ms in ex['metrics'].items():
            vals = [scores['experiments'][exp]['results'][n][metric] for n in cohort]
            std = float(np.std(vals)); stds[(exp,metric)] = std
            if std == 0:
                continue
            anchor = scores['experiments'][exp]['results'][REF][metric]
            for n in names:
                value = scores['experiments'][exp]['results'][n][metric]
                gains[n] += ex['weight']*abs(ms['coefficient'])*(1 if ms['higher_is_better'] else -1)*(value-anchor)/std
    return gains, stds


def paired_ci(scores, spec, stds):
    """Resample whole episodes, with identical draws for every method and ref."""
    eps=scores['_metadata']['episodes']
    groups={exp:[e['name'] for e in eps if e['contact_loss']==flag]
            for exp,flag in [('long_horizon_tracking',False),('relocalization_after_contact_loss',True)]}
    raw={}
    for n in methods(scores):
        if scores['_diagnostics'][n]['status'] != 'scored':
            continue
        raw[n]={}
        for exp, ids in groups.items():
            rows=[]
            for e in ids:
                with np.load(ROOT/'eval/test/audit_raw/cohort'/n/f'{e}.npz') as z:
                    rows.append({k:z[k].copy() for k in z.files})
            raw[n][exp]=rows
    names=sorted(raw)
    boot={n:[] for n in names}
    paired={}
    for n in names:
        paired[n]={}
        for exp, ids in groups.items():
            for src, metric in [('rot_axis_mae','rotation_mae_deg'),('trans_axis_mae','translation_mae_mm')]:
                d=np.array([raw[n][exp][i][src]-raw[REF][exp][i][src] for i in range(len(ids))],float)
                paired[n][f'{exp}:{metric}']={'mean_diff':float(d.mean()), 'se':float(d.std(ddof=1)/np.sqrt(len(d))),
                    'better':int((d < -1e-12).sum()), 'worse':int((d > 1e-12).sum()), 'n':len(d)}
    rng=np.random.default_rng(1717)  # Bootstrap RNG is public and independent of hidden instance RNGs.
    for _ in range(512):
        aggregates={n:{} for n in names}
        for exp, ids in groups.items():
            ix=rng.integers(0,len(ids),size=len(ids))
            for n in names:
                rr=[raw[n][exp][i] for i in ix]
                unique=sum(int(r['loops_unique']) for r in rr); false=sum(int(r['loops_false']) for r in rr)
                aggregates[n][exp]={
                    'rotation_mae_deg':float(np.mean([r['rot_axis_mae'] for r in rr])),
                    'translation_mae_mm':float(np.mean([r['trans_axis_mae'] for r in rr])),
                    'rotation_p95_deg':float(np.percentile(np.concatenate([r['geodesic'] for r in rr]),95)),
                    'translation_p95_mm':float(np.percentile(np.concatenate([r['trans_norm'] for r in rr]),95)),
                    'false_loop_excess':max(0.,false/unique-0.02) if unique else 0.}
        for n in names:
            gain=0.
            for exp, ex in spec.items():
                for m, ms in ex['metrics'].items():
                    sd=stds[exp,m]
                    if sd:
                        gain+=ex['weight']*abs(ms['coefficient'])*(1 if ms['higher_is_better'] else -1)*(aggregates[n][exp][m]-aggregates[REF][exp][m])/sd
            boot[n].append(gain)
    return {n:{'gain_ci95':np.percentile(boot[n],[2.5,97.5]).tolist(), 'paired':paired[n]} for n in names}


def main():
    final=load(ROOT/'scoring/scores_test.json')
    train=load(ROOT/'scoring/scores_train.json')
    cohort=load(RES/'after_cohort_test.json')
    train_cohort=load(ROOT/'eval/train/hardening_results/after_cohort_train.json')
    ref_path=ROOT/'scoring/reference.json'; ref=load(ref_path)
    # Paper context is never modified. Only scaled gym reference values are refreshed.
    for exp, ex in ref['experiments'].items():
        for n in [REF,'normalflow']:
            ex['results'][n].update(final['experiments'][exp]['results'][n])
    ref_path.write_text(json.dumps(ref,indent=2)+'\n')
    spec=ref['experiments']
    gains,stds=rank(cohort,spec)
    genuine=[n for n in methods(cohort) if not n.startswith('sc_')]
    genuine_gains,_=rank(cohort,spec,genuine)
    train_gains,_=rank(train_cohort,spec)
    paired=paired_ci(cohort,spec,stds)
    reproducibility={}
    for n in [REF,'normalflow']:
        delta=max(abs(final['experiments'][e]['results'][n][m]-cohort['experiments'][e]['results'][n][m])
                  for e in spec for m in spec[e]['metrics'])
        reproducibility[n]=delta
        if delta > 1e-9:
            raise RuntimeError(f'{n}: independent final run changed metrics by {delta}')
    failure_ranks=[gains[n] for n in gains if cohort['_diagnostics'][n]['status']=='failed']
    success_ranks=[gains[n] for n in gains if cohort['_diagnostics'][n]['status']=='scored']
    if failure_ranks and max(failure_ranks) > min(success_ranks)+1e-12:
        raise RuntimeError('failed method outranks a successful one')
    summary={'rank_formula':'sum weight * abs(coefficient) * direction * (value-reference) / population_std(all ranked attempts)',
        'reference_rerun_max_abs_metric_difference':reproducibility,
        'cohort':methods(cohort),'rank_gain':gains,'genuine_rank_gain':genuine_gains,'train_rank_gain':train_gains,
        'paired':paired,'stds':{e+':'+m:v for (e,m),v in stds.items()},
        'status':{n:cohort['_diagnostics'][n]['status'] for n in methods(cohort)}}
    (RES/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    exps=list(spec)
    lines=['# Final hardening audit measurements','',
        'Rank gains use all ranked entries, including failures, for each metric standard deviation. The genuine-only column uses the honest cohort. Confidence intervals resample whole paired episodes (512 draws), holding the cohort normalization fixed. These are audit summaries; only official experiment results are ranked.','',
        '| Method | Status | E1 rot / trans MAE | E2 rot / trans MAE | Gain (all) | Gain (honest) | Paired gain 95% CI | Train gain |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for n in sorted(gains,key=gains.get,reverse=True):
        aa=[cohort['experiments'][e]['results'][n] for e in exps]
        pair='; '.join(f"{a['rotation_mae_deg']:.4f} / {a['translation_mae_mm']:.4f}" for a in aa)
        ci=paired.get(n,{}).get('gain_ci95')
        cis=f'[{ci[0]:+.5f}, {ci[1]:+.5f}]' if ci else 'failed'
        tg=f'{train_gains[n]:+.5f}' if n in train_gains else '—'
        lines.append(f"| {n} | {cohort['_diagnostics'][n]['status']} | {pair.replace('; ',' | ')} | {gains[n]:+.5f} | {genuine_gains[n]:+.5f} | {cis} | {tg} |")
    lines+=['','Independent, serialized reference rerun: '+repr(reproducibility),'', 'Paired per-episode changes (variant minus reference; negative improves):','']
    for n,p in paired.items():
        if n==REF or n.startswith('sc_'):
            continue
        lines.append(f'- **{n}**: '+ '; '.join(f"{k}: {v['mean_diff']:+.5f} ± {v['se']:.5f} SE ({v['better']}/{v['worse']} better/worse, n={v['n']})" for k,v in p['paired'].items()))
    (RES/'measurements.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines),flush=True)


if __name__ == '__main__':
    main()
