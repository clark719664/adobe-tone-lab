import math
import tempfile
import unittest
from pathlib import Path
import benchmark as b

class MetricsTests(unittest.TestCase):
    def test_exact_values_and_effect(self):
        got = b.metrics([.1, .2], [.1, .2], ([.05, .1], [.05, .1]))
        self.assertEqual(got['mae'], 0)
        self.assertEqual(got['max'], 0)
        self.assertEqual(got['effect_ev'], 0)
        self.assertEqual(got['effect_blocks'], 2)

    def test_one_stop_effect_error(self):
        got = b.metrics([.2, .4], [.1, .2], ([.1, .2], [.1, .2]))
        self.assertAlmostEqual(got['effect_ev'], 1)

    def test_rejects_malformed_predictions(self):
        for x in ([.2], [.1, float('nan')], [.1, -.2], []):
            with self.assertRaises(ValueError):
                b.metrics(x, [.1, .2])

    def test_empty_effect_support_is_not_a_pass(self):
        with self.assertRaises(ValueError):
            b.metrics([0], [0], ([0], [0]))

    def test_train_and_holdout_do_not_overlap(self):
        self.assertEqual(b.SPLIT, {'train': ['scene1', 'scene3'], 'holdout': ['scene4']})

    def test_noop_baseline_has_twelve_edited_cases(self):
        report = b.public_baseline()
        self.assertEqual(len(report['cases']), 12)
        self.assertEqual(len(report['holdout_cases']), 4)
        self.assertTrue(all(v['effect_ev'] > 0 for v in report['cases'].values()))
        self.assertEqual(report['fidelity_status'], 'joint_references_missing')

    def test_fixtures_match_source_pins(self):
        self.assertEqual(b.verify_sources(), [])

    def test_joint_gate_fails_when_oracle_absent(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'missing joint Adobe references'):
                b.joint_gate(Path(d))

    def test_oracle_self_comparison_is_only_a_scorer_sanity_check(self):
        refs = b.read(b.ROOT / 'vendor/scene-probes.json')['cases']
        p = {k: v['camera_raw'] for k, v in refs.items()}
        report = b.score_predictions(p)
        self.assertTrue(report['anti_regression_pass'])
        self.assertEqual(len(report['default_cases']), 3)
        self.assertEqual(report['fidelity_status'], 'joint_references_missing')

    def test_candidate_default_is_in_anti_regression_gate(self):
        refs = b.read(b.ROOT / 'vendor/scene-probes.json')['cases']
        p = {k: v['camera_raw'] for k, v in refs.items()}
        p['scene4/default'] = [v * 2 for v in p['scene4/default']]
        report = b.score_predictions(p)
        self.assertFalse(report['default_cases']['scene4/default']['within_upstream_accepted_distance'])
        self.assertFalse(report['anti_regression_pass'])

    def test_acquisition_has_paired_cases_and_hashes(self):
        import hashlib
        jobs = b.read(b.ROOT / 'acquisition/manifest.json')['jobs']
        self.assertEqual(len(jobs), 21)
        for j in jobs:
            for key in ('input', 'xmp'):
                self.assertEqual(hashlib.sha256((b.ROOT / 'acquisition' / j[key]).read_bytes()).hexdigest(), j[key + '_sha256'])
        self.assertEqual(sum(j['split'] == 'holdout' for j in jobs), 7)

    def test_xmp_attributes_match_every_capture_job(self):
        import xml.etree.ElementTree as ET
        ns = '{http://ns.adobe.com/camera-raw-settings/1.0/}'
        for j in b.read(b.ROOT / 'acquisition/manifest.json')['jobs']:
            root = ET.parse(b.ROOT / 'acquisition' / j['xmp']).getroot()
            description = next(x for x in root.iter() if x.tag.endswith('Description'))
            actual = {k.removeprefix(ns): v for k, v in description.attrib.items() if k.startswith(ns)}
            self.assertEqual(actual, j['settings'])

    def test_candidate_missing_default_fails(self):
        with self.assertRaises(ValueError):
            b.score_predictions({})

if __name__ == '__main__':
    unittest.main(verbosity=2)
