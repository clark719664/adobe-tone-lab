"""Materialize paired DNG/XMP inputs. Does not run or install Adobe software."""
from pathlib import Path
import hashlib,json,shutil
import benchmark as b
ROOT=Path(__file__).resolve().parent
SETTINGS={'default':{}, 'S+100':{'Shadows2012':'100'}, 'H-100':{'Highlights2012':'-100'},
 'S+50':{'Shadows2012':'50'}, 'H-50':{'Highlights2012':'-50'},
 'S+100_H-100':{'Shadows2012':'100','Highlights2012':'-100'},
 'S+50_H-50':{'Shadows2012':'50','Highlights2012':'-50'}}
BASE={'ProcessVersion':'15.4','WhiteBalance':'As Shot','LensProfileEnable':'0','AutoLateralCA':'0',
 'Sharpness':'0','LuminanceSmoothing':'0','ColorNoiseReduction':'0','Exposure2012':'0','Contrast2012':'0',
 'Highlights2012':'0','Shadows2012':'0','Whites2012':'0','Blacks2012':'0','Texture':'0','Clarity2012':'0',
 'Dehaze':'0','Vibrance':'0','Saturation':'0','PostCropVignetteAmount':'0','GrainAmount':'0'}


def main():
    bad=b.verify_sources()
    if bad: raise ValueError('source integrity failure: '+str(bad))
    dest=ROOT/'acquisition'
    (dest/'inputs').mkdir(parents=True,exist_ok=True)
    jobs=[]
    for scene in sum(b.SPLIT.values(),[]):
        source=ROOT/'vendor'/f'{scene}.dng'
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        for name,settings in SETTINGS.items():
            ident=f'{scene}__{name}'
            target=dest/'inputs'/f'{ident}.dng'
            shutil.copyfile(source,target)
            all_settings=BASE|settings
            attributes=' '.join(f'crs:{k}="{v}"' for k,v in all_settings.items())
            text=f'''<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" {attributes}/>
</rdf:RDF></x:xmpmeta>
'''
            target.with_suffix('.xmp').write_text(text,encoding='utf-8')
            jobs.append({'id':ident,'input':'inputs/'+target.name,'input_sha256':digest,
              'xmp':'inputs/'+target.with_suffix('.xmp').name,'xmp_sha256':hashlib.sha256(target.with_suffix('.xmp').read_bytes()).hexdigest(),
              'output':ident+'.tif','dimensions':[384,256],'settings':all_settings,
              'split':'holdout' if scene in b.SPLIT['holdout'] else 'train'})
    b.write(dest/'manifest.json',{'schema':1,'source_pins':'../sources.json','jobs':jobs,
      'export_contract':{'bits_per_channel':16,'color_space':'ProPhoto RGB','embedded_icc':True,
        'resize':False,'linear_profile':'Embedded in DNG','process_version':'15.4'},
      'note':'These exact reduced DNG inputs require fresh paired exports. Existing public scene block measurements were captured at a different resolution; never combine them into these joint capture sets.'})
    b.write(dest/'capture-template.json',{'adobe_version':'FILL ACTUAL CAMERA RAW VERSION',
      'process_version':'15.4','color_space':'ProPhoto RGB','bits_per_channel':16,
      'files':{j['id']:{'sha256':'FILL SHA256 OF REAL TIFF','input_sha256':j['input_sha256'],'settings':j['settings']} for j in jobs}})
    print(f'Wrote {len(jobs)} paired DNG/XMP jobs; no Adobe exports were produced.')

if __name__=='__main__':main()
