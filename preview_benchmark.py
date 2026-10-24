"""Actual pinned PhotoCraft conditional preview baseline; not RAW-stage equivalence."""
from pathlib import Path
import argparse,hashlib,json,re
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET
import sys
import prepare_acquisition
import preview_families
import numpy as np
from PIL import Image
import benchmark as b
import preview_native


def equivalent(a,b):
    try:return Decimal(a)==Decimal(b)
    except (InvalidOperation,TypeError,ValueError):return a==b


def digest(obj,key):
    value=obj.get(key)
    if not isinstance(value,str) or re.fullmatch(r'[0-9a-fA-F]{64}',value) is None:
        raise ValueError('required SHA256 digest missing or malformed: '+key)
    return value.lower()


def validate_oracle(folder,families,oracle):
    """Validate the frozen six-family preview contract before any native prediction."""
    folder=Path(folder)
    expected_ids={f'{family}-{variant}__{setting}' for family in preview_families.TRAIN+preview_families.HOLDOUT
                  for variant in range(3) for setting in prepare_acquisition.SETTINGS}
    if families.get('train_families')!=list(preview_families.TRAIN) or families.get('holdout_families')!=list(preview_families.HOLDOUT):
        raise ValueError('family split declaration differs from frozen experiment')
    cases=families.get('cases',[]);entries_list=oracle.get('entries',[])
    if len(cases)!=126 or {c.get('id') for c in cases}!=expected_ids:
        raise ValueError('exact126unique family case IDs required')
    if len(entries_list)!=126 or {e.get('case') for e in entries_list}!=expected_ids:
        raise ValueError('exact126unique oracle case IDs required')
    if digest(oracle,'converter_sha256')!='6fd0af0d40e72ab634460fd00085a035ae7d5048bc69fbd19ae926c7e904e8a1':
        raise ValueError('wrong converter provenance')
    entries={e['case']:e for e in entries_list};source_by_scene={}
    crs='{http://ns.adobe.com/camera-raw-settings/1.0/}'
    rdf='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
    for case in cases:
        ident=case['id'];entry=entries[ident]
        source_hash=digest(case,'input_sha256');xmp_hash=digest(case,'xmp_sha256')
        for field in ('source_sha256','requested_xmp_sha256','converted_dng_sha256','jpeg_sha256','decoded_rgb8_sha256'):
            digest(entry,field)
        family,variant,setting=case.get('family'),case.get('variant'),case.get('setting')
        if family not in preview_families.TRAIN+preview_families.HOLDOUT or type(variant) is not int or variant not in range(3) or setting not in prepare_acquisition.SETTINGS:
            raise ValueError('invalid family case identity: '+ident)
        scene=f'{family}-{variant}'
        expected_settings=prepare_acquisition.BASE|prepare_acquisition.SETTINGS[setting]
        expected_split='train' if family in preview_families.TRAIN else 'holdout'
        if case.get('scene')!=scene or ident!=scene+'__'+setting or case.get('split')!=expected_split or case.get('settings')!=expected_settings:
            raise ValueError('family identity/settings/split mismatch: '+ident)
        if case.get('dimensions')!=[256,192]:raise ValueError('family dimensions mismatch: '+ident)
        if source_by_scene.setdefault(scene,source_hash)!=source_hash:
            raise ValueError('paired source DNG hashes differ: '+ident)
        if digest(entry,'source_sha256')!=source_hash or digest(entry,'requested_xmp_sha256')!=xmp_hash:
            raise ValueError('oracle source/XMP hash mismatch: '+ident)
        if entry.get('PreviewApplicationName')!='Adobe DNG Converter' or entry.get('PreviewApplicationVersion')!='18.7' or entry.get('PreviewColorSpace')!=2:
            raise ValueError('preview engine/version/colorspace mismatch: '+ident)
        if entry.get('dimensions')!=[256,192] or entry.get('bits_per_sample')!=[8,8,8] or entry.get('YCbCrSubSampling')!=[1,1] or entry.get('jpeg_embedded_icc_present') is not False:
            raise ValueError('preview pixel/profile contract mismatch: '+ident)
        actual=entry.get('actual_crs_settings',{})
        if any(not equivalent(value,actual.get(key)) for key,value in expected_settings.items()) or actual.get('CameraProfile')!='RAWmakase Probe':
            raise ValueError('actual output settings/profile mismatch: '+ident)
        # Verify saved output XMP as well as its copied metadata, allowing numeric spelling differences.
        try:
            xml=ET.parse(folder/'previews'/(ident+'.xmp')).getroot()
            desc=xml.find('.//'+rdf+'Description')
            parsed={k[len(crs):]:v for k,v in desc.attrib.items() if k.startswith(crs)} if desc is not None else {}
        except (OSError,ET.ParseError) as exc:raise ValueError('invalid saved output XMP: '+ident) from exc
        if set(parsed)!=set(actual) or any(not equivalent(value,parsed.get(key)) for key,value in actual.items()):
            raise ValueError('saved output XMP differs from recorded CRS: '+ident)
        path=folder/'previews'/(ident+'.jpg')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest(entry,'jpeg_sha256'):
            raise ValueError('oracle JPEG hash mismatch: '+ident)
        with Image.open(path) as image:
            if image.format!='JPEG' or image.mode!='RGB' or list(image.size)!=[256,192] or 'icc_profile' in image.info:
                raise ValueError('actual JPEG format/profile/dimensions mismatch: '+ident)
            pixels=np.asarray(image)
            if pixels.dtype!=np.uint8 or pixels.shape!=(192,256,3) or hashlib.sha256(pixels.tobytes()).hexdigest()!=digest(entry,'decoded_rgb8_sha256'):
                raise ValueError('decoded RGB8 hash mismatch: '+ident)
    return entries


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--oracle',type=Path,required=True)
    p.add_argument('--families',type=Path,required=True)
    p.add_argument('--build-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();families=b.read(args.families);oracle=b.read(args.oracle/'manifest.json')
    validate_oracle(args.oracle,families,oracle)
    bad=b.verify_sources()
    if bad:raise ValueError('source integrity failure: '+str(bad))
    binary=preview_native.build(args.build_dir);rows=[];defaults={}
    for case in families['cases']:
        if case['setting']=='default':continue
        scene=case['scene']
        if scene not in defaults:
            defaults[scene]=np.asarray(Image.open(args.oracle/'previews'/(scene+'__default.jpg')).convert('RGB'),dtype=np.float32)/255
        image=defaults[scene]
        target=np.asarray(Image.open(args.oracle/'previews'/(case['id']+'.jpg')).convert('RGB'),dtype=np.float32)/255
        s=float(case['settings']['Shadows2012']);h=float(case['settings']['Highlights2012'])
        predicted=preview_native.predict(binary,image,s,h,'baseline',args.build_dir)
        error=np.abs(predicted-target)*255
        clipped=(image.min(2)<=.5/255)|(image.max(2)>=254.5/255)
        pixel_error=error.mean(2)
        rows.append({k:case[k] for k in ('id','scene','family','variant','setting','split')}|{
          'baseline_mae_255':float(error.mean()),'baseline_p95_255':float(np.quantile(error,.95)),
          'noop_mae_255':float(np.abs(image-target).mean()*255),
          'neutral_clipped_fraction':float(clipped.mean()),
          'absolute_error_mass_on_clipped':float(pixel_error[clipped].sum()/max(pixel_error.sum(),1e-12))})
    summary={}
    for split in ('train','holdout'):
        joint=[r for r in rows if r['split']==split and '_H' in r['setting']]
        summary[split]={'joint_cases':len(joint),'baseline_joint_mean_mae_255':float(np.mean([r['baseline_mae_255'] for r in joint]))}
    result={'contract':'Adobe DNG Converter18.7 encoded8-bit fullsize sRGBJPEG; PhotoCraft applied postrender to Adobe neutral preview',
      'status':'native_baseline_measured; no candidate passed generalization',
      'limitations':['Not RAW-stage equivalence or16-bit TIFF/Lightroom fidelity.','Preview output quantization, JPEG and stage mismatch remain.','Family validation was excluded from coefficient fitting but reused across multiple hypotheses; not an independent final test set.'],
      'oracle_rounding_bound':'For fixed predictions, perturbing every target channel by at most0.5/255 changes a paired MAE improvement by at most1/255. This does not bound JPEG loss or neutral-input operator sensitivity.',
      'summary':summary,'rows':rows}
    args.out.parent.mkdir(parents=True,exist_ok=True);b.write(args.out,result)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);sys.exit(2)
