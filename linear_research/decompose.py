"""Exact seven-setting RGB error decomposition; oracle diagnostics, not predictions.

Consumes an existing source-linear native cache and frozen JPEG references. Fits no
parameters, generates no Adobe outputs, and never labels old holdouts as fresh.
"""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from measure import validate_case,verify_hash

METRICS=('joint_mae','singles_residual_mae_if_interaction_perfect',
         'interaction_defect_mae_if_singles_perfect','target_interaction_mae','pred_interaction_mae')
def mae(x):return float(np.abs(x).mean()*255)
def evaluate(manifest,previews,cache,transfer_path):
    cases=json.loads(Path(manifest).read_text())['cases']
    provenance=json.loads((Path(previews).parent/'manifest.json').read_text())
    entries={r['case']:r for r in provenance['entries']}
    integrity=json.loads((Path(cache)/'cache-manifest.json').read_text())
    verify_hash(transfer_path,integrity['transfer_sha256'])
    for name,digest in integrity['files'].items():verify_hash(Path(cache)/name,digest)
    data=np.load(transfer_path)
    tx,ty=data['x'],data['y']
    if tx.ndim!=1 or ty.shape!=tx.shape or np.any(np.diff(tx)<=0):
        raise ValueError('invalid frozen monotone transfer')
    groups={}
    for r in cases:
        validate_case(r)
        entry=entries[r['id']]
        if entry['source_sha256']!=r['input_sha256']:raise ValueError('source provenance mismatch')
        verify_hash(Path(previews)/(r['id']+'.jpg'),entry['jpeg_sha256'])
        for key in ('Shadows2012','Highlights2012','Exposure2012','ProcessVersion'):
            if float(entry['actual_crs_settings'][key])!=float(r['settings'][key]):raise ValueError('embedded setting mismatch')
        w,h=r['dimensions'];n=w*h
        s=float(r['settings']['Shadows2012'])/100
        hl=float(r['settings']['Highlights2012'])/100
        raw=np.fromfile(Path(cache)/(r['scene']+'.f32'),dtype='<f4')
        sg=np.fromfile(Path(cache)/f"{r['scene']}_{s}_{0.0}.f32",dtype='<f4')
        hg=np.fromfile(Path(cache)/f"{r['scene']}_{0.0}_{hl}.f32",dtype='<f4')
        if raw.size!=n or sg.size!=n+1025 or hg.size!=n+1025:
            raise ValueError('cache dimensions or native LUT contract mismatch')
        scene=np.interp(raw*sg[:n]*hg[:n],np.exp2(np.linspace(-16,4,1025)),sg[n:])
        pred=np.repeat(np.interp(scene,tx,ty).reshape(h,w,1),3,axis=2)
        target=np.asarray(Image.open(Path(previews)/(r['id']+'.jpg')).convert('RGB'),dtype=float)/255
        if target.shape!=pred.shape or not np.isfinite(pred).all():raise ValueError('invalid image')
        g=groups.setdefault(r['scene'],{})
        if r['setting'] in g:raise ValueError('duplicate setting')
        g[r['setting']]=r|{'pred':pred,'target':target}
    out=[]
    for scene,g in groups.items():
        expected={'default','S+50','H-50','S+100','H-100','S+50_H-50','S+100_H-100'}
        if set(g)!=expected:raise ValueError('exact seven-setting boundary required')
        for amount in (50,100):
            n,s,h,j=[g[k] for k in ('default',f'S+{amount}',f'H-{amount}',f'S+{amount}_H-{amount}')]
            # E_joint = E_S + E_H - E_0 + (I_pred - I_target), exact RGB identity.
            singles=s['pred']-s['target']+h['pred']-h['target']-n['pred']+n['target']
            pi=j['pred']-s['pred']-h['pred']+n['pred']
            ti=j['target']-s['target']-h['target']+n['target']
            defect=pi-ti;total=j['pred']-j['target']
            if np.max(np.abs(total-singles-defect))>=1e-12:raise AssertionError('identity failed')
            out.append({'scene':scene,'family':j['family'],'split':j['split'],'amount':amount,
              'joint_mae':mae(total),'singles_residual_mae_if_interaction_perfect':mae(singles),
              'interaction_defect_mae_if_singles_perfect':mae(defect),
              'target_interaction_mae':mae(ti),'pred_interaction_mae':mae(pi),
              'target_signed_interaction':float(ti.mean()*255),
              'pred_signed_interaction':float(pi.mean()*255)})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--previews',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--transfer',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    out=evaluate(args.manifest,args.previews,args.cache,args.transfer)
    args.output.write_text(json.dumps({'contract':'oracle counterfactual diagnostics only; no deployable corrections',
      'units':'full-image RGB mean absolute error in 0..255 JPEG levels',
      'formula':'E_joint=E_S+E_H-E_0+(I_pred-I_target)','cases':out},indent=2))
    for split in sorted({r['split'] for r in out}):
        rr=[r for r in out if r['split']==split]
        print(split,len(rr),{k:round(float(np.mean([r[k] for r in rr])),6) for k in METRICS})
    print('Seven-setting boundaries and exact RGB identity verified for',len(out),'joint cases.')
if __name__=='__main__':main()
