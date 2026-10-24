import unittest
import numpy as np
import preview_candidate as c

class JointCandidateTests(unittest.TestCase):
    def test_singles_and_defaults_are_unchanged(self):
        baseline=np.array([[[.1,.3,.7]]],dtype=np.float32)
        neutral=baseline/2;shadow=baseline*.8
        for s,h in ((0,0),(100,0),(0,-100)):
            np.testing.assert_array_equal(c.correct(baseline,neutral,shadow,s,h,.6),baseline)

    def test_holdout_values_cannot_select_parameters(self):
        z=np.full((2,2,3),.3)
        rows=[{'split':'train','baseline':z,'default':z*.5,'shadow':z,'shadows':100,'highlights':-100,'oracle':z*.7},
          {'split':'holdout','baseline':z,'default':z*.5,'shadow':z,'shadows':100,'highlights':-100,'oracle':z*0}]
        before=c.fit(rows)
        rows[1]['oracle']=z*1000
        self.assertEqual(c.fit(rows),before)

    def test_quantization_uncertainty_bound(self):
        baseline=np.array([.2,.4,.6]);candidate=baseline+.01;oracle=baseline+.1
        improvement=np.abs(baseline-oracle).mean()-np.abs(candidate-oracle).mean()
        perturbed=oracle+np.array([-.5,.5,-.5])/255
        changed=np.abs(baseline-perturbed).mean()-np.abs(candidate-perturbed).mean()
        self.assertLessEqual(abs(changed-improvement),1/255+1e-12)

if __name__=='__main__':unittest.main(verbosity=2)
