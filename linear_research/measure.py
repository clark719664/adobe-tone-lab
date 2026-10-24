"""Portable native scene-tone measurement, with training-only neutral calibration."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
import numpy as np
from PIL import Image
from tiff_probe import read_ifds
from linear_contract import NeutralTransfer
HERE=Path(__file__).resolve().parent
GRID=np.exp2(np.linspace(-16,4,1025))
TRAIN={'ramp','stripes','checker','spots'}
SETTINGS={'default':(0,0),'S+50':(50,0),'S+100':(100,0),'H-50':(0,-50),'H-100':(0,-100),'S+50_H-50':(50,-50),'S+100_H-100':(100,-100)}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_hash(path,digest):
    if sha(path)!=digest:raise ValueError('file hash mismatch: '+str(path))

def validate_case(case):
    settings=case['settings'];expected=SETTINGS.get(case['setting'])
    if expected is None or (float(settings['Shadows2012']),float(settings['Highlights2012']))!=expected:raise ValueError('setting name/value mismatch')
    if float(settings['Exposure2012'])!=0 or float(settings['ProcessVersion'])!=15.4:raise ValueError('unsupported exposure/process version')
    if case['id']!=case['scene']+'__'+case['setting'] or Path(case['id']).name!=case['id']:raise ValueError('invalid case ID')

def verify_sources(root=HERE):
    pins=json.loads((root/'source-pins.json').read_text())
    for path,digest in pins['files'].items():
        if sha(root/path)!=digest:raise ValueError('native source hash mismatch: '+path)
    return pins

def build(root=HERE):
    verify_sources(root)
    subprocess.run(['cargo','build','--locked','--release','--jobs','1','--manifest-path',str(root/'Cargo.toml')],check=True)
    return root/'target/release'/('linear-tone-probe.exe' if os.name=='nt' else 'linear-tone-probe')

def raw_scene(path):
    data,endian,ifds=read_ifds(path)
    t=next(i['tags'] for i in ifds if i['tags'].get(262)==32803)
    if t[259]!=1 or t[258]!=16 or t[50717]!=65535:raise ValueError('known uncompressed16bit neutral probe required')
    raw=np.frombuffer(data[t[273]:t[273]+t[279]],dtype=endian+'u2').reshape(t[257],t[256]).astype(float)/65535
    return np.repeat(raw[...,None],3,axis=2)

def native_gain(binary,cache,raw,s,h,scene):
    cache.mkdir(parents=True,exist_ok=True)
    src=cache/(scene+'.f32');dest=cache/f'{scene}_{s}_{h}.f32'
    # Re-execute each distinct case per run; never trust an unpinned old cache.
    raw[...,0].astype('<f4').tofile(src)
    env=os.environ.copy();env['RAYON_NUM_THREADS']='2'
    subprocess.run([str(binary),str(src),str(dest),str(raw.shape[1]),str(raw.shape[0]),str(s),str(h)],env=env,check=True)
    values=np.fromfile(dest,dtype='<f4');n=raw.shape[0]*raw.shape[1]
    if values.size!=n+1025 or not np.isfinite(values).all():raise ValueError('invalid native output')
    return values[:n].reshape(raw.shape[:2]),values[n:]

def load(inputs,reference,binary,cache):
    manifest=json.loads((reference/'families.json').read_text())
    provenance=json.loads((reference/'manifest.json').read_text())
    entries={r['case']:r for r in provenance['entries']}
    rows=[];scenes={}
    for case in manifest['cases']:
        validate_case(case)
        entry=entries[case['id']];path=inputs/(case['id']+'.dng');jpeg=reference/'previews'/(case['id']+'.jpg')
        verify_hash(path,case['input_sha256']);verify_hash(jpeg,entry['jpeg_sha256'])
        if entry['source_sha256']!=case['input_sha256']:raise ValueError('source provenance mismatch')
        for key in ('Shadows2012','Highlights2012','Exposure2012','ProcessVersion'):
            if float(entry['actual_crs_settings'][key])!=float(case['settings'][key]):raise ValueError('embedded setting mismatch')
        scene=case['scene']
        if scene not in scenes:scenes[scene]={'raw':raw_scene(path),'gains':{}}
        stored=scenes[scene];raw=stored['raw']
        target=np.asarray(Image.open(jpeg),dtype=float)/255
        if target.shape!=raw.shape or list(raw.shape[1::-1])!=case['dimensions']:raise ValueError('shape mismatch')
        s=float(case['settings']['Shadows2012'])/100;h=float(case['settings']['Highlights2012'])/100
        for key in ((s,0.),(0.,h)):
            if key not in stored['gains']:stored['gains'][key]=native_gain(binary,cache,raw,*key,scene)
        sg,curve=stored['gains'][(s,0.)];hg,_=stored['gains'][(0.,h)]
        rows.append(case|{'raw':raw,'target':target,'s':s,'h':h,'sg':sg,'hg':hg,'curve':curve})
    return rows

def calibrate(rows):
    selected=[r for r in rows if r['split']=='train' and r['family'] in TRAIN and r['setting']=='default']
    expected={(f,v) for f in TRAIN for v in range(3)}
    if {(r['family'],r['variant']) for r in selected}!=expected or len(selected)!=12:raise ValueError('exact12training neutral calibration cases required')
    x=[np.interp(r['raw'],GRID,r['curve']) for r in selected]
    return NeutralTransfer.fit(np.concatenate(x),np.concatenate([r['target'] for r in selected]))

def measure(rows,transfer):
    results=[]
    for r in rows:
        pred=transfer(np.interp(r['raw']*(r['sg']*r['hg'])[...,None],GRID,r['curve']))
        results.append({k:r[k] for k in ('id','family','setting','split')}|{'baseline':float(np.abs(pred-r['target']).mean()*255)})
    return results

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build',action='store_true');p.add_argument('--refit-transfer',type=Path)
    p.add_argument('--transfer',type=Path,default=HERE/'neutral-transfer-global.npz');args=p.parse_args()
    verify_sources();binary=build() if args.build else HERE/'target/release'/('linear-tone-probe.exe' if os.name=='nt' else 'linear-tone-probe')
    rows=load(args.inputs,args.reference,binary,args.cache)
    if args.refit_transfer:
        transfer=calibrate(rows);np.savez(args.refit_transfer,x=transfer.x,y=transfer.y)
        expected=np.load(args.transfer)
        if not np.array_equal(transfer.x,expected['x']) or not np.array_equal(transfer.y,expected['y']):raise ValueError('training-only calibration differs from frozen transfer')
    else:
        saved=np.load(args.transfer);transfer=NeutralTransfer(saved['x'],saved['y'])
    result=measure(rows,transfer);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    integrity={'files':{p.name:sha(p) for p in args.cache.glob('*.f32')},'transfer_sha256':sha(args.refit_transfer or args.transfer)}
    (args.cache/'cache-manifest.json').write_text(json.dumps(integrity,indent=2)+'\n')
    print('Measured',len(result),'cases with native source-linear baseline; no fitted correction accepted.')

if __name__=='__main__':main()
