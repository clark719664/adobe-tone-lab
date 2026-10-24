"""Deterministic known-linear inputs for the separate Adobe preview contract."""
from pathlib import Path
import hashlib,json,sys,shutil
import numpy as np
import benchmark as b
import prepare_acquisition as acq
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
import probe_dng
TRAIN=('ramp','stripes','checker','spots')
HOLDOUT=('rings','random_regions')


def generate(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    h,w=192,256;yy,xx=np.mgrid[:h,:w];u=xx/(w-1);v=yy/(h-1)
    cases=[]
    for family in TRAIN+HOLDOUT:
        for variant,(lo,hi) in enumerate(((-8.,-1.),(-6.,0.),(-3.,0.))):
            if family=='ramp':field=u
            elif family=='stripes':field=(xx//16%4)/3
            elif family=='checker':field=((xx//16+yy//16)%4)/3
            elif family=='spots':
                field=np.full((h,w),.2)
                for cx,cy,rad,value in ((.3,.4,.16,.8),(.7,.3,.1,1),(.65,.7,.18,.05)):
                    field=np.where((u-cx)**2+(v-cy)**2<rad**2,value,field)
            elif family=='rings':field=np.floor(np.hypot((u-.5)*1.3,v-.5)*10)%5/4
            else:
                rng=np.random.default_rng(20261023+variant)
                coarse=rng.uniform(0,1,(12,16))
                field=np.repeat(np.repeat(coarse,16,axis=0),16,axis=1)
                field=np.clip(.85*field+.15*u,0,1)
            image=np.repeat((2**(lo+(hi-lo)*field))[...,None],3,axis=2)
            ident=f'{family}-{variant}';source=folder/(ident+'.dng')
            probe_dng.write(source,image,baseline_exposure=0.)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            for name,settings in acq.SETTINGS.items():
                stem=ident+'__'+name;dest=folder/(stem+'.dng');shutil.copyfile(source,dest)
                full=acq.BASE|settings
                attrs=' '.join(f'crs:{k}="{val}"' for k,val in full.items())
                xmp=f'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" {attrs}/></rdf:RDF></x:xmpmeta>\n'
                dest.with_suffix('.xmp').write_text(xmp,encoding='utf-8',newline='\n')
                cases.append({'id':stem,'scene':ident,'family':family,'variant':variant,'setting':name,'settings':full,
                  'split':'train' if family in TRAIN else 'holdout','input_sha256':digest,
                  'xmp_sha256':hashlib.sha256(dest.with_suffix('.xmp').read_bytes()).hexdigest(),'dimensions':[w,h]})
            source.unlink() # Only our just-created redundant source; seven identical source copies remain.
    manifest={'contract':'Adobe DNG Converter18.7 fullsize8bitJPEG conditional-preview experiment','train_families':TRAIN,'holdout_families':HOLDOUT,
      'generation':'known scene-linear neutral ProPhoto values; embedded linear profile; no fabricated Adobe outputs',
      'settings_application':'must validate converted output embedded XMP and counterfactual controls','cases':cases}
    b.write(folder/'manifest.json',manifest)
    return manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);args=p.parse_args();m=generate(args.folder);print('Generated',len(m['cases']),'input DNG/XMP pairs; zero oracle outputs.')
