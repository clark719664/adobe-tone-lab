"""Synthetic validation fixtures only. No Adobe outputs or oracle expectations."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import benchmark as b
import reference_import as r


def synthetic_icc(gamma=1.8, wrong_primaries=False, curve_form='single'):
    xyz = ((.7976749,.2880402,0),(.1351917,.7118741,0),(.0313534,.0000857,.8252100))
    if wrong_primaries: xyz = ((.4,.2,.01),)+xyz[1:]
    tags = []
    for c, p in zip('rgb', xyz):
        tags.append(((c+'XYZ').encode(), b'XYZ '+bytes(4)+struct.pack('>iii',*(round(v*65536) for v in p))))
        if curve_form=='single': curve=b'curv'+bytes(4)+struct.pack('>IH',1,round(gamma*256))
        elif curve_form=='spiky':
            table=[round((i/65535)**gamma*65535) for i in range(65536)];table[256]=65535
            curve=b'curv'+bytes(4)+struct.pack('>I',65536)+struct.pack('>65536H',*table)
        elif curve_form=='sampled':
            curve=b'curv'+bytes(4)+struct.pack('>I',257)+struct.pack('>257H',*(round((i/256)**gamma*65535) for i in range(257)))
        else:
            form=3 if curve_form=='hidden-branch' else int(curve_form)
            params={0:[gamma],1:[gamma,1,0],2:[gamma,1,0,0],3:[gamma,1,0,1,0],4:[gamma,1,0,1,0,0,0]}[form]
            if curve_form=='hidden-branch':params=[gamma,1,0,1000,.003]
            curve=b'para'+bytes(4)+struct.pack('>HH',form,0)+struct.pack('>'+str(len(params))+'i',*(round(v*65536) for v in params))
        tags.append(((c+'TRC').encode(),curve))
    name=b'SYNTHETIC TEST ProPhoto RGB\0'
    tags.append((b'desc',b'desc'+bytes(4)+struct.pack('>I',len(name))+name))
    header=bytearray(128);header[16:20]=b'RGB ';header[20:24]=b'XYZ ';header[36:40]=b'acsp'
    offset=132+len(tags)*12;directory=b'';payload=b''
    for sig,data in tags:
        directory+=sig+struct.pack('>II',offset,len(data));payload+=data
        pad=(-len(data))%4;payload+=bytes(pad);offset+=len(data)+pad
    profile=header+struct.pack('>I',len(tags))+directory+payload
    struct.pack_into('>I',profile,0,len(profile))
    return bytes(profile)


def synthetic_tiff(path, *, width=384, height=256, gamma=1.8, wrong_primaries=False, bits=16,
                   orientation=1, compression=1, endian='<', rows=None, pattern=False, curve_form='single'):
    """Artificial pixels exercise parsing only. Never an Adobe expected output."""
    rows=height if rows is None else rows
    strips=(height+rows-1)//rows
    entries=[(256,4,[width]),(257,4,[height]),(258,3,[bits]*3),(259,3,[compression]),
      (262,3,[2]),(273,4,[0]*strips),(274,3,[orientation]),(277,3,[3]),(278,4,[rows]),
      (279,4,[min(rows,height-i*rows)*width*6 for i in range(strips)]),(284,3,[1]),(339,3,[1]*3),
      (34675,7,synthetic_icc(gamma,wrong_primaries,curve_form))]
    entries.sort()
    def raw(kind,value):return value if kind==7 else struct.pack(endian+{3:'H',4:'I'}[kind]*len(value),*value)
    offset=8+2+len(entries)*12+4
    pixel_start=offset+sum(len(raw(k,v)) for _,k,v in entries if len(raw(k,v))>4)
    table=bytearray();extra=bytearray()
    for tag,kind,value in entries:
        if tag==273:value=[pixel_start+i*rows*width*6 for i in range(strips)]
        data=raw(kind,value)
        if len(data)>4:slot=struct.pack(endian+'I',offset+len(extra));extra+=data
        else:slot=data.ljust(4,b'\0')
        table+=struct.pack(endian+'HHI',tag,kind,len(value))+slot
    pixels=bytearray()
    for y in range(height):
        for x in range(width):
            values=((x*101)%65536,(y*179)%65536,((x+y)*61)%65536) if pattern else (16384,32768,49152)
            pixels+=struct.pack(endian+'HHH',*values)
    order=b'II' if endian=='<' else b'MM'
    path.write_bytes(order+struct.pack(endian+'HIH',42,8,len(entries))+table+bytes(4)+extra+pixels)


class ReferenceImportTests(unittest.TestCase):
    def test_lossless_synthetic_16bit_reduction(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.tif';synthetic_tiff(p)
            image=r.read_linear_tiff(p,[384,256])
            expected=sum((v/65535)**1.8*w for v,w in zip((16384,32768,49152),r.YW))
            blocks=r.block_luminance(image,384,256)
            self.assertEqual(len(blocks),384)
            self.assertAlmostEqual(blocks[0],expected,places=12)
            self.assertAlmostEqual(blocks[-1],expected,places=12)

    def test_synthetic_invalid_contracts_rejected(self):
        for kwargs in ({'gamma':2.2},{'wrong_primaries':True},{'bits':8},{'orientation':3},{'compression':5},{'width':386}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as d:
                p=Path(d)/'synthetic.tif';synthetic_tiff(p,**kwargs)
                with self.assertRaises(ValueError):r.read_linear_tiff(p,[384,256])

    def test_truncated_synthetic_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.tif';synthetic_tiff(p);p.write_bytes(p.read_bytes()[:-2])
            with self.assertRaises(ValueError):r.read_linear_tiff(p,[384,256])

    def test_all_21_synthetic_imports_are_marked_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);jobs=b.read(b.ROOT/'acquisition/manifest.json')['jobs']
            first=folder/jobs[0]['output'];synthetic_tiff(first)
            data=first.read_bytes()
            for j in jobs[1:]:(folder/j['output']).write_bytes(data)
            r.record_capture(folder,'SYNTHETIC TEST ONLY')
            report=r.import_references(folder)
            self.assertEqual(len(report['cases']),21)
            self.assertEqual(report['adobe_settings_application'],'unverified; capture metadata records requested settings only')
            self.assertEqual(report['fidelity_status'],'not_measured')
            capture=b.read(folder/'capture.json');capture['files'][jobs[0]['id']]['settings']['Shadows2012']='999'
            b.write(folder/'capture.json',capture)
            with self.assertRaisesRegex(ValueError,'metadata/hash mismatch'):r.import_references(folder)

    def test_big_endian_multiple_strips_and_nonuniform_block_order(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic-be.tif';synthetic_tiff(p,endian='>',rows=31,pattern=True)
            blocks=r.block_luminance(r.read_linear_tiff(p,[384,256]),384,256)
            for bx,by in ((0,0),(7,4),(23,15)):
                expected=0
                for y in range(by*16,(by+1)*16):
                    for x in range(bx*16,(bx+1)*16):
                        values=((x*101)%65536,(y*179)%65536,((x+y)*61)%65536)
                        expected+=sum((v/65535)**1.8*w for v,w in zip(values,r.YW))
                self.assertAlmostEqual(blocks[by*24+bx],expected/256,places=12)

    def test_sampled_and_all_parametric_icc_forms(self):
        for curve in ('sampled','0','1','2','3','4'):
            with self.subTest(curve=curve):
                self.assertEqual(r._icc(synthetic_icc(curve_form=curve))['primaries'],'ProPhoto D50')
                with self.assertRaises(ValueError):r._icc(synthetic_icc(gamma=2.2,curve_form=curve))

    def test_icc_spikes_and_hidden_parametric_branches_rejected(self):
        for form in ('spiky','hidden-branch'):
            with self.subTest(form=form):
                with self.assertRaises(ValueError):r._icc(synthetic_icc(curve_form=form))

    def test_malformed_strip_offsets_counts_and_zero_rows(self):
        for tag,newvalue in ((273,0x7fffffff),(279,2),(278,0)):
            with self.subTest(tag=tag),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'synthetic-bad.tif';synthetic_tiff(p)
                data=bytearray(p.read_bytes());count=struct.unpack_from('<H',data,8)[0]
                for i in range(count):
                    pos=10+i*12
                    if struct.unpack_from('<H',data,pos)[0]==tag:struct.pack_into('<I',data,pos+8,newvalue)
                p.write_bytes(data)
                with self.assertRaises(ValueError):r.read_linear_tiff(p,[384,256])

    def test_capture_metadata_and_stale_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);jobs=b.read(b.ROOT/'acquisition/manifest.json')['jobs']
            first=folder/jobs[0]['output'];synthetic_tiff(first);data=first.read_bytes()
            for j in jobs[1:]:(folder/j['output']).write_bytes(data)
            r.record_capture(folder,'SYNTHETIC TEST ONLY');original=b.read(folder/'capture.json')
            variants=[]
            for key,value in (('adobe_version','FILL'),('process_version','6'),('bits_per_channel',8),('color_space','sRGB')):
                candidate=copy.deepcopy(original);candidate[key]=value;variants.append(candidate)
            candidate=copy.deepcopy(original);candidate['files'][jobs[0]['id']]['sha256']='0'*64;variants.append(candidate)
            candidate=copy.deepcopy(original);candidate['files'].pop(jobs[0]['id']);variants.append(candidate)
            for candidate in variants:
                b.write(folder/'capture.json',candidate)
                with self.assertRaises(ValueError):r.import_references(folder)
            b.write(folder/'capture.json',original)
            first.unlink()
            with self.assertRaisesRegex(ValueError,'missing joint Adobe references'):r.import_references(folder)

    def test_missing_real_exports_fail(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'missing joint Adobe references'):r.import_references(Path(d))

if __name__=='__main__':unittest.main(verbosity=2)
