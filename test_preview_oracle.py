import hashlib
import unittest
from pathlib import Path
import benchmark as b
import reference_import

class PreviewOracleTests(unittest.TestCase):
    def test_real_preview_files_match_pinned_source_manifest(self):
        root=b.ROOT/'preview_reference'
        manifest=b.read(root/'manifest.json');families=b.read(root/'families.json')
        entries={e['case']:e for e in manifest['entries']}
        self.assertEqual(len(entries),126)
        self.assertEqual(families['train_families'],['ramp','stripes','checker','spots'])
        self.assertEqual(families['holdout_families'],['rings','random_regions'])
        for case in families['cases']:
            e=entries[case['id']]
            self.assertEqual(e['source_sha256'],case['input_sha256'])
            self.assertEqual(e['PreviewColorSpace'],2)
            self.assertEqual(e['PreviewApplicationVersion'],'18.7')
            self.assertEqual(hashlib.sha256((root/'previews'/(case['id']+'.jpg')).read_bytes()).hexdigest(),e['jpeg_sha256'])

    def test_real_jpeg_cannot_enter_prophoto_tiff_import(self):
        jpeg=next((b.ROOT/'preview_reference/previews').glob('*.jpg'))
        with self.assertRaisesRegex(ValueError,'TIFF header required'):
            reference_import.read_linear_tiff(jpeg,[256,192])

if __name__=='__main__':unittest.main(verbosity=2)
