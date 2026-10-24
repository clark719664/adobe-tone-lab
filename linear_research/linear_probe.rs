#![allow(dead_code)]
// App-only interface types. No evaluated tone/filter code is stubbed.
mod model { pub mod recipe {
    pub struct Effects { pub clarity:f32 }
    pub struct Adjustment { pub clarity:f32 }
    pub struct Mask { pub adjust:Adjustment }
    impl Mask { pub fn is_active(&self)->bool { false } }
    pub struct Recipe { pub shadows:f32,pub highlights:f32,pub effects:Effects,pub masks:Vec<Mask> }
}}
mod camera_data { pub struct CameraImage { pub pixels:Vec<[f32;3]>,pub width:u32,pub height:u32 } }
#[path="vendor/local_tone_data.rs"] mod local_tone_data;
#[path="vendor/local_tone.rs"] mod local_tone;
#[path="vendor/clarity.rs"] mod clarity;
#[path="vendor/shadow_context.rs"] mod shadow_context;
#[path="vendor/shadow_context_data.rs"] mod shadow_context_data;
#[path="vendor/scene_tone/global.rs"] mod global;
fn main() {
    let args:Vec<String>=std::env::args().collect();
    assert_eq!(args.len(),7,"input output width height shadows highlights");
    let bytes=std::fs::read(&args[1]).unwrap();
    let w:u32=args[3].parse().unwrap();let h:u32=args[4].parse().unwrap();
    assert_eq!(bytes.len(),w as usize*h as usize*4);assert!(w>0 && h>0);
    let lum:Vec<f32>=bytes.chunks_exact(4).map(|v|f32::from_le_bytes(v.try_into().unwrap())).collect();
    assert!(lum.iter().all(|v|v.is_finite() && *v>=0.));
    let s:f32=args[5].parse().unwrap();let hl:f32=args[6].parse().unwrap();
    assert!(s.is_finite() && hl.is_finite() && s.abs()<=1. && hl.abs()<=1.);
    let base=std::sync::Arc::new(local_tone::MapBase::new(lum.clone(),[w,h]));
    let map=local_tone::LocalToneMap::from_base(&base,[w,h],local_tone::Sliders{shadows:s,highlights:hl,..Default::default()},false);
    let mut out:Vec<u8>=lum.iter().enumerate().flat_map(|(i,v)| {
        let gain=map.gain((i%w as usize) as f32,(i/w as usize) as f32,*v,*v);
        assert!(gain.is_finite());gain.to_le_bytes()
    }).collect();
    // Same scene-measure conventions as PhotoMeasures and CurveSet::for_image.
    let mut levels:Vec<f32>=lum.iter().map(|v|v.max(local_tone::FLOOR).log2()).collect();
    levels.sort_by(f32::total_cmp);
    let at=|q:f32|levels[((levels.len()-1) as f32*q) as usize];
    let shadow_map=local_tone::LocalToneMap::from_base(&base,[w,h],local_tone::Sliders{shadows:s,..Default::default()},false);
    let mut shadow_gains:Vec<f32>=lum.iter().enumerate().map(|(i,v)|shadow_map.gain((i%w as usize) as f32,(i/w as usize) as f32,*v,*v).log2()).collect();
    shadow_gains.sort_by(f32::total_cmp);
    let shift=if s>0. {shadow_gains[(shadow_gains.len()-1)/2]} else {0.};
    let tone=global::GlobalTone::new([0.,at(1.),(at(0.99)+1.).min(0.),0.],0.,0.,at(0.),at(0.001)+shift,true);
    for k in 0..1025 {
        let x=(-16.+20.*k as f32/1024.).exp2();
        out.extend_from_slice(&tone.apply([x;3])[0].to_le_bytes());
    }
    std::fs::write(&args[2],out).unwrap();
}
