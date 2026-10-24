"""Lossless reference import. Synthetic validation is never Adobe fidelity evidence."""
from __future__ import annotations
import argparse
from array import array
import hashlib
from functools import lru_cache
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET
import benchmark as b
import prepare_acquisition as acquisition

YW = (.2880402, .7118741, .0000857)
APPLICATION = 'unverified; capture metadata records requested settings only'
GAMMA18 = tuple((i/65535)**1.8 for i in range(65536))


def _slice(data, start, size):
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError('truncated or out-of-bounds TIFF/ICC data')
    return data[start:start + size]


@lru_cache(maxsize=16)
def _icc(profile):
    if len(profile) < 132 or profile[36:40] != b'acsp' or profile[16:20] != b'RGB ' or profile[20:24] != b'XYZ ':
        raise ValueError('RGB matrix ICC profile required')
    length, = struct.unpack_from('>I',profile)
    if length != len(profile): raise ValueError('ICC length mismatch')
    count, = struct.unpack_from('>I',profile,128)
    if count > 256: raise ValueError('excessive ICC tag count')
    directory_end = 132 + count * 12
    _slice(profile,132,count*12)
    tags = {}
    for i in range(count):
        sig, offset, size = struct.unpack_from('>4sII',profile,132+i*12)
        if sig in tags or offset < directory_end: raise ValueError('invalid ICC tag directory')
        tags[sig] = _slice(profile,offset,size)
    def fixed(data,offset): return struct.unpack('>i',_slice(data,offset,4))[0] / 65536
    target = ((.7976749,.2880402,0),(.1351917,.7118741,0),(.0313534,.0000857,.8252100))
    for channel, expected in zip('rgb',target):
        tag=tags.get((channel+'XYZ').encode(),b'')
        if tag[:4]!=b'XYZ ': raise ValueError('missing ProPhoto ICC primaries')
        if any(abs(fixed(tag,8+4*i)-v)>.004 for i,v in enumerate(expected)):
            raise ValueError('ICC primaries differ from ProPhoto')
        curve=tags.get((channel+'TRC').encode(),b'')
        kind=curve[:4]
        if kind==b'curv':
            n,=struct.unpack('>I',_slice(curve,8,4))
            if n==1:
                gamma=struct.unpack('>H',_slice(curve,12,2))[0]/256
                if gamma<=0:raise ValueError('invalid ICC gamma')
                evaluate=lambda x,gamma=gamma:x**gamma
            elif 2 <= n <= 65536:
                table=struct.unpack('>'+str(n)+'H',_slice(curve,12,n*2))
                def evaluate(x):
                    q=x*(n-1);i=min(int(q),n-2);t=q-i
                    return ((1-t)*table[i]+t*table[i+1])/65535
            else: raise ValueError('unsupported or linear ICC transfer curve')
        elif kind==b'para':
            form,=struct.unpack('>H',_slice(curve,8,2))
            sizes={0:1,1:3,2:4,3:5,4:7}
            if form not in sizes: raise ValueError('unsupported ICC parametric curve')
            params=[fixed(curve,12+4*i) for i in range(sizes[form])]
            def evaluate(x):
                g=params[0]
                if g<=0:raise ValueError('invalid ICC gamma')
                if form==0:return x**g
                a,c0=params[1:3]
                if a<=0:raise ValueError('invalid ICC curve scale')
                if form==1:return max(0,a*x+c0)**g if x>=-c0/a else 0
                c=params[3]
                if form==2:return max(0,a*x+c0)**g+c if x>=-c0/a else c
                d=params[4]
                if form==3:return max(0,a*x+c0)**g if x>=d else c*x
                e,f=params[5:7]
                return max(0,a*x+c0)**g+e if x>=d else c*x+f
        else:raise ValueError('missing ICC transfer curve')
        previous=-math.inf
        # Every possible unsigned16-bit sample: sparse probes miss LUT spikes and narrow branches.
        for code,expected in enumerate(GAMMA18):
            try:actual=evaluate(code/65535)
            except (OverflowError,ZeroDivisionError):raise ValueError('invalid ICC transfer curve') from None
            if not math.isfinite(actual) or not -.00001<=actual<=1.00001 or actual<previous-1e-7 or abs(actual-expected)>.003:
                raise ValueError('ICC transfer curve is not monotone ProPhoto gamma1.8')
            previous=actual
    return {'primaries':'ProPhoto D50','transfer':'verified gamma1.8 within0.003 linear tolerance'}


def read_linear_tiff(path, dimensions):
    """Decode uncompressed, unsigned16-bit interleaved RGB without 8-bit conversion."""
    data=Path(path).read_bytes()
    if len(data)<8 or data[:2] not in (b'II',b'MM'):raise ValueError('TIFF header required')
    endian='<' if data[:2]==b'II' else '>'
    def unpack(fmt,offset):return struct.unpack(endian+fmt,_slice(data,offset,struct.calcsize(endian+fmt)))
    if unpack('H',2)[0]!=42:raise ValueError('classic TIFF required')
    offset=unpack('I',4)[0];count=unpack('H',offset)[0]
    if count>256:raise ValueError('excessive TIFF tag count')
    _slice(data,offset+2,count*12+4)
    if unpack('I',offset+2+count*12)[0]:raise ValueError('single-image TIFF required')
    tags={}
    required={256,257,258,259,262,273,274,277,278,279,284,317,338,339,34675}
    for i in range(count):
        pos=offset+2+i*12;tag,kind,n=unpack('HHI',pos)
        if tag not in required:continue
        if tag in tags:raise ValueError('duplicate TIFF tag')
        sizes={1:1,3:2,4:4,7:1}
        if kind not in sizes:raise ValueError('unsupported TIFF field type')
        size=sizes[kind]*n
        raw=_slice(data,pos+8,size) if size<=4 else _slice(data,unpack('I',pos+8)[0],size)
        tags[tag]=raw if tag==34675 else list(struct.unpack(endian+{1:'B',3:'H',4:'I',7:'B'}[kind]*n,raw))
    def one(tag,default=None):
        value=tags.get(tag,[default])
        if len(value)!=1 or value[0] is None:raise ValueError('missing or nonscalar TIFF tag: '+str(tag))
        return value[0]
    width,height=one(256),one(257)
    if [width,height]!=list(dimensions):raise ValueError('TIFF dimensions mismatch')
    if tags.get(258)!=[16,16,16] or one(277)!=3 or one(262)!=2 or 338 in tags:
        raise ValueError('16-bit RGB without alpha required')
    if one(259,1)!=1 or one(284,1)!=1 or one(317,1)!=1:
        raise ValueError('uncompressed interleaved TIFF without predictor required')
    if one(274,1)!=1 or tags.get(339,[1,1,1]) not in ([1],[1,1,1]):
        raise ValueError('top-left unsigned-integer TIFF required')
    _icc(tags.get(34675,b''))
    offsets,counts=tags.get(273,[]),tags.get(279,[])
    rows=one(278,height)
    if rows<=0 or len(offsets)!=(height+rows-1)//rows or len(counts)!=len(offsets):raise ValueError('TIFF strip count mismatch')
    channels=array('H')
    for i,(start,size) in enumerate(zip(offsets,counts)):
        if size!=min(rows,height-i*rows)*width*6:raise ValueError('TIFF strip byte count mismatch')
        part=array('H');part.frombytes(_slice(data,start,size))
        if (sys.byteorder=='little') != (endian=='<'):part.byteswap()
        channels.extend(part)
    return [(x/65535)**1.8 for x in channels]


def block_luminance(image,width,height):
    if len(image)!=width*height*3 or width%24 or height%16:raise ValueError('24x16 block geometry required')
    bw,bh=width//24,height//16;out=[]
    for by in range(16):
        for bx in range(24):
            total=0.
            for y in range(by*bh,(by+1)*bh):
                for x in range(bx*bw,(bx+1)*bw):
                    i=(y*width+x)*3
                    total+=sum(image[i+c]*YW[c] for c in range(3))
            out.append(total/(bw*bh))
    return out


def _jobs():
    bad=b.verify_sources()
    if bad:raise ValueError('source integrity failure: '+', '.join(bad))
    jobs=b.read(b.ROOT/'acquisition/manifest.json')['jobs']
    expected={scene+'__'+setting for scene in sum(b.SPLIT.values(),[]) for setting in acquisition.SETTINGS}
    if len(jobs)!=21 or {j['id'] for j in jobs}!=expected:raise ValueError('exact21paired jobs required')
    ns='{http://ns.adobe.com/camera-raw-settings/1.0/}'
    for j in jobs:
        scene,setting=j['id'].split('__',1)
        if j['settings']!=acquisition.BASE|acquisition.SETTINGS[setting] or j['dimensions']!=[384,256] or j['output']!=j['id']+'.tif':
            raise ValueError('capture job contract changed: '+j['id'])
        original=b.ROOT/'vendor'/(scene+'.dng')
        if hashlib.sha256(original.read_bytes()).hexdigest()!=j['input_sha256']:raise ValueError('capture source hash changed')
        for key in ('input','xmp'):
            p=(b.ROOT/'acquisition'/j[key]).resolve()
            if not p.is_relative_to((b.ROOT/'acquisition/inputs').resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=j[key+'_sha256']:
                raise ValueError('acquisition input integrity failure: '+j['id'])
        root=ET.parse(b.ROOT/'acquisition'/j['xmp']).getroot()
        descriptions=[x for x in root.iter() if x.tag.endswith('Description')]
        actual={k.removeprefix(ns):v for k,v in descriptions[0].attrib.items() if k.startswith(ns)} if len(descriptions)==1 else {}
        if actual!=j['settings']:raise ValueError('XMP settings differ from manifest')
    return jobs


def _present(folder,jobs):
    missing=[j['output'] for j in jobs if not(folder/j['output']).is_file()]
    if missing:raise ValueError(f'missing joint Adobe references: {len(missing)} paired exports absent; first: {missing[0]}')


def record_capture(folder,adobe_version):
    folder=Path(folder);jobs=_jobs();_present(folder,jobs)
    if not adobe_version.strip() or 'FILL' in adobe_version:raise ValueError('actual Adobe version required')
    if (folder/'capture.json').exists():raise ValueError('capture.json already exists; preserve/review it explicitly')
    result={'adobe_version':adobe_version,'process_version':'15.4','color_space':'ProPhoto RGB','bits_per_channel':16,
      'adobe_settings_application':APPLICATION,'files':{}}
    for j in jobs:
        read_linear_tiff(folder/j['output'],j['dimensions'])
        result['files'][j['id']]={'sha256':hashlib.sha256((folder/j['output']).read_bytes()).hexdigest(),
          'input_sha256':j['input_sha256'],'settings':j['settings']}
    b.write(folder/'capture.json',result)
    return result


def import_references(folder):
    folder=Path(folder);jobs=_jobs();_present(folder,jobs);capture=b.read(folder/'capture.json')
    if not capture.get('adobe_version') or 'FILL' in capture['adobe_version'] or capture.get('process_version')!='15.4':raise ValueError('capture must identify actual Adobe version and ProcessVersion15.4')
    if capture.get('color_space')!='ProPhoto RGB' or capture.get('bits_per_channel')!=16:raise ValueError('capture must use16-bit ProPhoto RGB')
    if set(capture.get('files',{}))!={j['id'] for j in jobs}:raise ValueError('capture requires exact21case records')
    cases={}
    for j in jobs:
        p=folder/j['output'];item=capture['files'][j['id']]
        if item.get('sha256')!=hashlib.sha256(p.read_bytes()).hexdigest() or item.get('input_sha256')!=j['input_sha256'] or item.get('settings')!=j['settings']:
            raise ValueError('capture metadata/hash mismatch: '+j['id'])
        image=read_linear_tiff(p,j['dimensions'])
        cases[j['id']]={'settings':j['settings'],'linear_prophoto_block_luminances':block_luminance(image,*j['dimensions']),
          'split':j['split'],'source_tiff_sha256':item['sha256'],'input_sha256':item['input_sha256']}
    return {'status':'paired_exports_validated','fidelity_status':'not_measured','adobe_version':capture['adobe_version'],
      'adobe_settings_application':APPLICATION,'icc_transfer_curve':'validated gamma1.8',
      'comparison_contract':'fresh384x256capture batch only; never mix with old full-resolution probe values',
      'cases':cases}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    cap=sub.add_parser('capture');cap.add_argument('folder',type=Path);cap.add_argument('--adobe-version',required=True)
    imp=sub.add_parser('import');imp.add_argument('folder',type=Path);imp.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command=='capture':
            result=record_capture(args.folder,args.adobe_version);print('Recorded21TIFF hashes; requested Adobe settings remain unverified.')
        else:
            result=import_references(args.folder);b.write(args.out,result);print('Imported21paired linear block references; fidelity not measured.')
        return 0
    except (ValueError,OSError,KeyError,struct.error,ET.ParseError) as e:print('FAIL: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
