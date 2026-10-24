"""Execute the pinned native operator on encoded preview pixels (separate contract)."""
from pathlib import Path
import subprocess
import numpy as np
import run_photocraft
ROOT=Path(__file__).resolve().parent


def build(build_dir):
    build_dir=Path(build_dir).resolve();build_dir.mkdir(parents=True,exist_ok=True)
    src=run_photocraft.source();src=src[:src.index('fn main()')]
    src+='''
fn main() {
 let a:Vec<String>=std::env::args().collect();
 assert_eq!(a.len(),8,"input output width height shadows highlights mode");
 let bytes=std::fs::read(&a[1]).unwrap();
 assert_eq!(bytes.len()%16,0);
 let mut px:Vec<[f32;4]>=bytes.chunks_exact(16).map(|b|std::array::from_fn(|c|f32::from_le_bytes(b[c*4..c*4+4].try_into().unwrap()))).collect();
 let w:usize=a[3].parse().unwrap();let h:usize=a[4].parse().unwrap();
 assert_eq!(px.len(),w*h);assert!(px.iter().flatten().all(|v|v.is_finite()));
 let s:f32=a[5].parse().unwrap();let hl:f32=a[6].parse().unwrap();
 if a[7]=="baseline" {local_tone::apply(&mut px,w,h,s,hl,Encoding(0.0));}
 else if a[7]=="reverse" {
  local_tone::apply(&mut px,w,h,s,0.0,Encoding(0.0));
  local_tone::apply(&mut px,w,h,0.0,hl,Encoding(0.0));
 } else {panic!("unknown mode");}
 let bytes:Vec<u8>=px.iter().flatten().flat_map(|v|v.to_le_bytes()).collect();
 std::fs::write(&a[2],bytes).unwrap();
}
'''
    wrapper=ROOT/'preview_operator_wrapper.rs';wrapper.write_text(src,encoding='utf-8',newline='\n')
    binary=build_dir/'preview_operator.exe'
    subprocess.run(['rustc','--edition=2024','-O',str(wrapper),'-o',str(binary)],check=True)
    return binary


def predict(binary,image,shadows,highlights,mode,work):
    image=np.asarray(image,dtype=np.float32)
    h,w,c=image.shape
    if c!=3:raise ValueError('RGB required')
    rgba=np.concatenate((image,np.ones((h,w,1),dtype=np.float32)),axis=2).astype('<f4')
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    source=work/'native-input.f32';dest=work/'native-output.f32';rgba.tofile(source)
    subprocess.run([str(binary),str(source),str(dest),str(w),str(h),str(shadows),str(highlights),mode],check=True)
    out=np.fromfile(dest,dtype='<f4').reshape(h,w,4)[...,:3].copy()
    if not np.isfinite(out).all():raise ValueError('nonfinite native output')
    return np.clip(out,0,1)
