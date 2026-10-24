"""Frozen Adobe probe evaluation. Harness correctness is separate from joint fidelity."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SPLIT = {'train': ['scene1', 'scene3'], 'holdout': ['scene4']}
SLIDERS = ('S+100', 'S-50', 'H-100', 'H+50')
DARK, BRIGHT = 1 / 4096, .9


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def verify_sources():
    bad = []
    for item in read(ROOT / 'sources.json')['files']:
        p = ROOT / item['file']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            bad.append(item['file'])
    return bad


def values(v, n=None):
    if not isinstance(v, list) or not v or (n is not None and len(v) != n):
        raise ValueError('nonempty, matching block arrays required')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in v):
        raise ValueError('block values must be finite, nonnegative numbers')
    return v


def metrics(predicted, oracle, defaults=None):
    values(oracle)
    values(predicted, len(oracle))
    encode = lambda x: min(1., max(0., x)) ** (1 / 1.8)
    errors = [abs(encode(a) - encode(b)) for a, b in zip(predicted, oracle)]
    result = {'mae': sum(errors) / len(errors), 'max': max(errors)}
    if defaults is not None:
        p0, o0 = defaults
        values(p0, len(oracle)); values(o0, len(oracle))
        effect = [abs(math.log2(p / pz) - math.log2(o / oz))
                  for p, o, pz, oz in zip(predicted, oracle, p0, o0)
                  if min(p, o, pz, oz) > DARK and max(o, oz) < BRIGHT]
        if not effect:
            raise ValueError('no supported nonclipped blocks for effect comparison')
        result.update(effect_ev=sum(effect) / len(effect), effect_blocks=len(effect))
    return result


def score_predictions(predictions):
    refs = read(ROOT / 'vendor/scene-probes.json')['cases']
    required = [f'{s}/{setting}' for s in sum(SPLIT.values(), []) for setting in ('default',) + SLIDERS]
    missing = [k for k in required if k not in predictions]
    if missing:
        raise ValueError('missing candidate cases: ' + ', '.join(missing))
    report, default_report = {}, {}
    accepted = read(ROOT / 'vendor/engine-accepted-distances.json')
    for key in required:
        values(predictions[key], len(refs[key]['camera_raw']))
        if key.endswith('/default'):
            m = metrics(predictions[key], refs[key]['camera_raw'])
            base = accepted[key]
            m['within_upstream_accepted_distance'] = (m['mae'] <= base['mae'] * 1.05 + .0005 and m['max'] <= base['max'] * 1.05 + .003)
            m['upstream_accepted_distance'] = base
            default_report[key] = m
            continue
        scene = key.split('/')[0]
        defaults = (predictions[scene + '/default'], refs[scene + '/default']['camera_raw'])
        m = metrics(predictions[key], refs[key]['camera_raw'], defaults)
        base = accepted[key]
        m['within_upstream_accepted_distance'] = (
            m['mae'] <= base['mae'] * 1.05 + .0005
            and m['max'] <= base['max'] * 1.05 + .003
            and m['effect_ev'] <= base['effect'] * 1.05 + .005)
        m['upstream_accepted_distance'] = base
        report[key] = m
    return {'fidelity_status': 'joint_references_missing', 'split': SPLIT,
            'cases': report, 'default_cases': default_report, 'holdout_cases': [k for k in report if k.startswith('scene4/')],
            'anti_regression_pass': all(m['within_upstream_accepted_distance'] for m in list(report.values()) + list(default_report.values())),
            'limits': ['Single-slider block means only; no joint or private-photo validation.',
                       'Upstream accepted distances are historical thresholds, not a fresh local engine run.',
                       'No parameters were fitted here; scene4 is reserved for future candidate evaluation.']}


def public_baseline():
    refs = read(ROOT / 'vendor/scene-probes.json')['cases']
    p = {f'{s}/{setting}': refs[f'{s}/default']['camera_raw']
         for s in sum(SPLIT.values(), []) for setting in ('default',) + SLIDERS}
    r = score_predictions(p)
    r['operator'] = 'no-op: frozen Adobe default used unchanged for each edited case'
    return r


def joint_gate(folder):
    """Validate the complete paired capture set; never claim measured fidelity."""
    import reference_import
    result = reference_import.import_references(folder)
    return {k: v for k, v in result.items() if k != 'cases'} | {'exports': len(result['cases'])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('audit')
    base = sub.add_parser('baseline'); base.add_argument('--out', type=Path)
    score = sub.add_parser('score'); score.add_argument('predictions', type=Path); score.add_argument('--out', type=Path)
    gate = sub.add_parser('joint-gate'); gate.add_argument('references', type=Path)
    args = p.parse_args()
    try:
        bad = verify_sources()
        if bad:
            raise ValueError('source integrity failure: ' + ', '.join(bad))
        if args.command == 'audit':
            refs = read(ROOT / 'vendor/scene-probes.json')
            joints = [k for k, v in refs['cases'].items() if float(v['settings'].get('Shadows2012', 0)) and float(v['settings'].get('Highlights2012', 0))]
            result = {'source_integrity': 'pass', 'public_cases': len(refs['cases']), 'scene_cases': sum(k.startswith('scene') for k in refs['cases']), 'joint_cases': joints, 'joint_fidelity': 'blocked_missing_oracle'}
            print(json.dumps(result, indent=2)); return 2 if not joints else 0
        if args.command == 'baseline':
            result = public_baseline()
        elif args.command == 'score':
            result = score_predictions(read(args.predictions)['cases'])
        else:
            result = joint_gate(args.references)
        if getattr(args, 'out', None):
            write(args.out, result)
            print(json.dumps({'saved': str(args.out), 'cases': len(result.get('cases', {})), 'anti_regression_pass': result.get('anti_regression_pass'), 'fidelity_status': result.get('fidelity_status')}))
        else:
            print(json.dumps(result, indent=2))
        return 1 if args.command == 'score' and not result['anti_regression_pass'] else 0
    except (ValueError, OSError, KeyError) as e:
        print('FAIL: ' + str(e), file=sys.stderr); return 2

if __name__ == '__main__':
    sys.exit(main())
