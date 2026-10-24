"""Acquire Adobe DNG Converter 18.7 full-size JPEG previews; no TIFF parity claim."""
import argparse,hashlib,io,json,os,re,shutil,subprocess,xml.etree.ElementTree as ET
from decimal import Decimal,InvalidOperation
from pathlib import Path
import numpy as np
from PIL import Image
from tiff_probe import read_ifds
PIN='6fd0af0d40e72ab634460fd00085a035ae7d5048bc69fbd19ae926c7e904e8a1'
CRS='{http://ns.adobe.com/camera-raw-settings/1.0/}'
def sha(b):return hashlib.sha256(b).hexdigest()
def settings(x):
 d=ET.fromstring(x).find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
 return {k[len(CRS):]:v for k,v in d.attrib.items() if k.startswith(CRS)}
def equivalent(a,b):
 try:return Decimal(a)==Decimal(b)
 except (InvalidOperation,TypeError):return a==b

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--converter',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
 exe=args.converter.resolve();src=args.inputs.resolve();out=args.out.resolve()
 if sha(exe.read_bytes())!=PIN:raise ValueError('Converter executable differs from pinned Adobe18.7 binary')
 if out.exists() and any(out.iterdir()):raise ValueError('Output directory must be empty; existing references are never overwritten')
 out.mkdir(parents=True,exist_ok=True);inp=out/'inputs';conv=out/'converted';jpg=out/'previews'
 for p in [inp,conv,jpg]:p.mkdir()
 files=sorted(src.glob('*.dng'))
 if not files:raise ValueError('No DNG inputs')
 requested={}
 for p in files:
  _,_,rows=read_ifds(p)
  if 700 in rows[0]['tags']:raise ValueError(f'{p.name}: embedded XMP would override the paired sidecar')
  x=p.with_suffix('.xmp')
  if not x.exists():raise ValueError(f'Missing sidecar: {x.name}')
  requested[p.stem]=settings(x.read_bytes());shutil.copy2(p,inp/p.name);shutil.copy2(x,inp/x.name)
 env=os.environ.copy()
 for key,folder in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata'),('PROGRAMDATA','programdata'),('TEMP','temp'),('TMP','temp')]:
  p=out/'isolated-user'/folder;p.mkdir(parents=True,exist_ok=True);env[key]=str(p)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW
 argv=[str(exe),'-c','-p2','-d',str(conv)]+[str(inp/p.name) for p in files]
 proc=subprocess.run(argv,env=env,startupinfo=si,capture_output=True,timeout=180)
 if proc.returncode:raise RuntimeError(f'Adobe converter exit {proc.returncode}: {proc.stderr!r}')
 entries=[]
 for f in files:
  converted=conv/f.name
  if not converted.exists():raise ValueError(f'Adobe did not create {f.name}')
  b,_,rows=read_ifds(converted);previews=[r['tags'] for r in rows if r['tags'].get(259)==7 and r['tags'].get(262)==6]
  t=max(previews,key=lambda v:v[256]*v[257]);raw=b[t[273]:t[273]+t[279]];image=Image.open(io.BytesIO(raw));pixels=np.array(image)
  if t[50970]!=2 or tuple(t[258])!=(8,8,8):raise ValueError('Preview is not tagged sRGB RGB8')
  if t[50966]!='Adobe DNG Converter' or t[50967]!='18.7':raise ValueError('Wrong preview engine/version')
  xml=re.search(rb'<x:xmpmeta.*?</x:xmpmeta>',b,re.S).group();actual=settings(xml)
  mismatch={k:[v,actual.get(k)] for k,v in requested[f.stem].items() if not equivalent(v,actual.get(k))}
  if mismatch:raise ValueError(f'{f.name}: requested settings mismatch {mismatch}')
  jpeg=jpg/(f.stem+'.jpg');jpeg.write_bytes(raw);(jpg/(f.stem+'.xmp')).write_bytes(xml)
  entries.append({'case':f.stem,'source_sha256':sha(f.read_bytes()),'requested_xmp_sha256':sha(f.with_suffix('.xmp').read_bytes()),'converted_dng_sha256':sha(b),'jpeg_sha256':sha(raw),'decoded_rgb8_sha256':sha(pixels.tobytes()),'dimensions':image.size,'bits_per_sample':t[258],'PreviewColorSpace':t[50970],'PreviewApplicationName':t[50966],'PreviewApplicationVersion':t[50967],'PreviewSettingsDigest':t.get(50969),'YCbCrSubSampling':t.get(530),'jpeg_embedded_icc_present':'icc_profile' in image.info,'actual_crs_settings':actual})
 report={'contract':'Adobe DNG Converter18.7 JPEG preview, sRGB RGB8; not Lightroom16-bit TIFF parity','converter_sha256':PIN,'argv':argv,'returncode':proc.returncode,'entries':entries}
 (out/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'returncode':proc.returncode,'verified_previews':len(entries),'manifest':str(out/'manifest.json')}))
if __name__=='__main__':main()
