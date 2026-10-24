"""Reference guards only: these tests do not add or bless Adobe expectations."""
import copy
import unittest
import benchmark as b
import preview_benchmark as p

class PreviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=b.ROOT/'preview_reference'
        cls.families=b.read(cls.folder/'families.json')
        cls.oracle=b.read(cls.folder/'manifest.json')

    def manifests(self):return copy.deepcopy(self.families),copy.deepcopy(self.oracle)

    def test_existing_real_capture_contract_passes(self):
        self.assertEqual(len(p.validate_oracle(self.folder,self.families,self.oracle)),126)

    def test_duplicate_and_missing_oracle_cases_rejected(self):
        for change in ('duplicate','missing'):
            with self.subTest(change=change):
                f,o=self.manifests()
                if change=='duplicate':o['entries'].append(o['entries'][0])
                else:o['entries'].pop()
                with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_family_duplicate_missing_or_split_mixup_rejected(self):
        for change in ('duplicate','missing','split','family_declaration','settings'):
            with self.subTest(change=change):
                f,o=self.manifests()
                if change=='duplicate':f['cases'].append(f['cases'][0])
                elif change=='missing':f['cases'].pop()
                elif change=='split':f['cases'][0]['split']='holdout'
                elif change=='family_declaration':f['train_families'].append('rings')
                else:f['cases'][0]['settings']['Shadows2012']='99'
                with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_wrong_reference_metadata_rejected(self):
        for field,value in [('requested_xmp_sha256','0'*64),('decoded_rgb8_sha256','0'*64),('PreviewColorSpace',3),
          ('PreviewApplicationName','other'),('PreviewApplicationVersion','18.6'),('dimensions',[1,1]),
          ('bits_per_sample',[16,16,16]),('YCbCrSubSampling',[2,2]),('jpeg_embedded_icc_present',True)]:
            with self.subTest(field=field):
                f,o=self.manifests();entry=next(e for e in o['entries'] if e['case']==f['cases'][0]['id']);entry[field]=value
                with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_wrong_actual_slider_or_camera_profile_rejected(self):
        for field,value in [('Shadows2012','100'),('ProcessVersion','6'),('CameraProfile','Adobe Standard')]:
            with self.subTest(field=field):
                f,o=self.manifests();entry=next(e for e in o['entries'] if e['case']==f['cases'][0]['id'])
                entry['actual_crs_settings'][field]=value
                with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_missing_paired_provenance_hashes_rejected(self):
        f,o=self.manifests()
        for case in f['cases']:
            case.pop('input_sha256');case.pop('xmp_sha256')
        for entry in o['entries']:
            entry.pop('source_sha256');entry.pop('requested_xmp_sha256')
        with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_all_provenance_hash_fields_require_hex_strings(self):
        for field in ('source_sha256','requested_xmp_sha256','converted_dng_sha256','jpeg_sha256','decoded_rgb8_sha256'):
            with self.subTest(field=field):
                f,o=self.manifests();o['entries'][0][field]='not-a-sha256'
                with self.assertRaises(ValueError):p.validate_oracle(self.folder,f,o)

    def test_semantically_equal_numeric_crs_values_accepted(self):
        f,o=self.manifests()
        entry=next(e for e in o['entries'] if e['case']==f['cases'][0]['id'])
        entry['actual_crs_settings']['Exposure2012']='0.0000'
        self.assertEqual(len(p.validate_oracle(self.folder,f,o)),126)

if __name__=='__main__':unittest.main(verbosity=2)
