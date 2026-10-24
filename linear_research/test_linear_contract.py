import unittest
import numpy as np
import linear_contract as lc

class ContractTests(unittest.TestCase):
    def test_transfer_follows_neutral_and_is_monotone(self):
        raw=np.repeat(np.linspace(.001,1,64)[None,:,None],3,2)
        neutral=np.sqrt(raw)
        t=lc.NeutralTransfer.fit(raw,neutral)
        self.assertLess(np.abs(t(raw)-neutral).max(),.00001)
        self.assertTrue(np.all(np.diff(t(np.linspace(0,2,200)))>=0))

    def test_color_and_nonfinite_input_rejected(self):
        raw=np.ones((4,4,3))*.2
        bad=raw.copy();bad[0,0,0]=.7
        with self.assertRaises(ValueError):lc.NeutralTransfer.fit(bad,raw)
        bad=raw.copy();bad[0,0,0]=np.nan
        with self.assertRaises(ValueError):lc.NeutralTransfer.fit(bad,raw)

    def test_rounding_sized_improvement_is_rejected(self):
        self.assertFalse(lc.gate([5,5],[4.5,4.5],[0],[0])['accepted'])

    def test_worst_case_regression_rejects_mean_win(self):
        self.assertFalse(lc.gate([10,10],[1,11.1],[0],[0])['accepted'])

    def test_single_regression_rejects_joint_win(self):
        self.assertFalse(lc.gate([10],[5],[2],[2.3])['accepted'])

    def test_meaningful_win_passes(self):
        self.assertTrue(lc.gate([8,9],[6,7],[2,3],[2,3])['accepted'])

    def test_mismatched_and_empty_scores_rejected(self):
        for args in [([],[],[1],[1]),([1],[1,2],[1],[1]),([1],[0],[float('nan')],[0])]:
            with self.assertRaises(ValueError):lc.gate(*args)

    def test_fit_never_uses_validation(self):
        rows=[{'split':'train','scores':[4,2,3]}, {'split':'validation','scores':[0,100,0]}]
        self.assertEqual(lc.select_index(rows),1)
        with self.assertRaises(ValueError):lc.select_index(rows[1:])

if __name__=='__main__':unittest.main()
