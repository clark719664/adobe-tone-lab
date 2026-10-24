"""Build/run the pinned PhotoCraft operator without building its native app.
Only the row scheduler is replaced by a serial loop; numeric helpers are verbatim.
"""
from pathlib import Path
import argparse, json, subprocess, sys, time
import benchmark as b
ROOT = Path(__file__).resolve().parent


def function(text, name):
    import re
    m = re.search(r'(?m)^(?:pub(?:\([^)]*\))?\s+)?fn\s+' + name + r'(?:<[^\n]*>)?\(', text)
    if not m:
        raise ValueError('function not found: ' + name)
    start = text.index('{', m.start()); level = 1; end = start + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[m.start():end]


def source():
    v = ROOT / 'vendor'
    camera = (v / 'photocraft-camera_raw.rs').read_text()
    util = (v / 'photocraft-photo_util.rs').read_text()
    convert = (v / 'photocraft-convert.rs').read_text()
    # Use the source Encoding implementation verbatim, with no serde dependency.
    enc_start = camera.index('pub(crate) struct Encoding(')
    enc_end = camera.index('\nfn luma_linear', enc_start)
    encoding = '#[derive(Clone, Copy)]\n' + camera[enc_start:enc_end]
    return '''// Pinned upstream operator + numeric helpers. Only row scheduling is serial.
#![allow(dead_code)]
mod photo_util {
 pub(crate) fn par_map<T: Send>(n: usize, f: impl Fn(usize) -> T + Sync + Send) -> Vec<T> { (0..n).map(f).collect() }
''' + function(convert, 'srgb_to_linear') + '\n' + function(convert, 'linear_to_srgb') + '\n' + function(util, 'bilinear') + '''
 pub(crate) fn par_rows<T: Send + Sync>(buf: &mut [T], w: usize, ch: usize, f: impl Fn(usize, &mut [T]) + Sync + Send) {
   for (y,row) in buf.chunks_mut(w.max(1) * ch).enumerate() { f(y,row); }
 }
}
use photo_util::{linear_to_srgb, srgb_to_linear, par_rows};
''' + encoding + function(camera, 'luma') + function(camera, 'box_mean') + '''
#[path = "vendor/local_tone.rs"] mod local_tone;
fn main() {
 let n=256;
 println!("shadows,highlights,measured_255,adobe_255,absolute_error_255");
 for (s,h,want) in [(100.0,0.0,165.3),(0.0,-100.0,89.6)] {
  let mut px: Vec<[f32;4]>=(0..n*n).map(|i| {
   let (x,y)=(i%n,i/n);
   let v=if x>=n-26 && y>=n-26 {0.97} else if x>=n-26 && y<26 {0.015} else {0.5};
   [v,v,v,1.0]
  }).collect();
  local_tone::apply(&mut px,n,n,s,h,Encoding(0.0));
  let got=px[175*n+100][0]*255.0;
  println!("{s},{h},{got},{want},{}",(got-want).abs());
 }
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-dir',type=Path,required=True)
    args=p.parse_args()
    bad=b.verify_sources()
    if bad: raise ValueError('source integrity failure: '+str(bad))
    args.build_dir.mkdir(parents=True,exist_ok=True)
    # Rust path attributes are relative to wrapper file, so write to bundle root.
    wrapper=ROOT/'photocraft_wrapper.rs'
    wrapper.write_text(source(),encoding='utf-8')
    test=args.build_dir/'photocraft_tests.exe'
    binary=args.build_dir/'photocraft_probe.exe'
    subprocess.run(['rustc','--edition=2024','-O','--test',str(wrapper),'-o',str(test)],check=True)
    test_run=subprocess.run([str(test),'--test-threads=1'],text=True,capture_output=True,check=True)
    subprocess.run(['rustc','--edition=2024','-O',str(wrapper),'-o',str(binary)],check=True)
    start=time.monotonic()
    run=subprocess.run([str(binary)],text=True,capture_output=True,check=True)
    elapsed=time.monotonic()-start
    import csv,io
    rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(io.StringIO(run.stdout))]
    result={'operator':'actual pinned PhotoCraft local_tone.rs, serial scheduler; upstream Encoding/luma/helpers',
      'oracle':'Photoshop25.4 Camera Raw Filter; upstream grey_moves_as_in_photoshop saved measurements',
      'rows':rows,'elapsed_seconds':elapsed,'within_upstream_5_level_tolerance':all(r['absolute_error_255']<5 for r in rows),
      'joint_fidelity':'unmeasured: no saved joint grey oracle',
      'limits':'Two neutral-grey single-slider spots only. Not the full app, RAWmakase pipeline, color-space interoperability, Adobe18.7 or photo holdout parity.'}
    b.write(ROOT/'photocraft-results.json',result)
    (ROOT/'photocraft-tests.txt').write_text(test_run.stdout+test_run.stderr,encoding='utf-8')
    print(test_run.stdout)
    print(json.dumps(result,indent=2))
    return 0 if result['within_upstream_5_level_tolerance'] else 1

if __name__=='__main__': sys.exit(main())
