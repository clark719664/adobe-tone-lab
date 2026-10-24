import unittest,tempfile,subprocess,os,json,hashlib
from pathlib import Path
import numpy as np
import measure

class NativeTests(unittest.TestCase):
    def run_gain(self,s,h):
        with tempfile.TemporaryDirectory() as tmp:
            raw=np.repeat(np.exp2(np.linspace(-8,0,64).reshape(8,8))[...,None],3,axis=2)
            binary=measure.HERE/'target/release'/('linear-tone-probe.exe' if os.name=='nt' else 'linear-tone-probe')
            return measure.native_gain(binary,Path(tmp),raw,s,h,'test')
    def test_default_and_determinism(self):
        a,c=self.run_gain(0.,0.);b,d=self.run_gain(0.,0.)
        np.testing.assert_array_equal(a,np.ones((8,8)));np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(c,d)
        self.assertTrue(np.all(np.diff(c)>=-1e-6))
    def test_native_joint_equals_product(self):
        a,_=self.run_gain(1.,0.);b,_=self.run_gain(0.,-1.);c,_=self.run_gain(1.,-1.)
        np.testing.assert_allclose(c,a*b,rtol=3e-6,atol=1e-6)
    def test_actual_source_hashes(self):
        self.assertEqual(measure.verify_sources()['commit'],'6c60222a927ec54cea9bb11624615b3d2baa6aa9')
    def test_source_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'x').write_bytes(b'changed')
            (root/'source-pins.json').write_text(json.dumps({'files':{'x':hashlib.sha256(b'original').hexdigest()}}))
            with self.assertRaises(ValueError):measure.verify_sources(root)
    def test_calibration_rejects_missing_training_cases(self):
        with self.assertRaises(ValueError):measure.calibrate([])
    def test_setting_name_value_mismatch_rejected(self):
        case={'id':'x__S+50','scene':'x','setting':'S+50','settings':{'Shadows2012':'100','Highlights2012':'0','Exposure2012':'0','ProcessVersion':'15.4'}}
        with self.assertRaises(ValueError):measure.validate_case(case)
    def test_input_or_reference_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'reference';path.write_bytes(b'reference')
            digest=measure.sha(path);path.write_bytes(b'mutation')
            with self.assertRaises(ValueError):measure.verify_hash(path,digest)

if __name__=='__main__':unittest.main()
