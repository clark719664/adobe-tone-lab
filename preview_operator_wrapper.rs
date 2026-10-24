// Pinned upstream operator + numeric helpers. Only row scheduling is serial.
#![allow(dead_code)]
mod photo_util {
 pub(crate) fn par_map<T: Send>(n: usize, f: impl Fn(usize) -> T + Sync + Send) -> Vec<T> { (0..n).map(f).collect() }
pub fn srgb_to_linear(v: f32) -> f32 {
    if v <= 0.04045 { v / 12.92 } else { ((v + 0.055) / 1.055).powf(2.4) }
}
pub fn linear_to_srgb(v: f32) -> f32 {
    if v <= 0.003_130_8 { v * 12.92 } else { 1.055 * v.powf(1.0 / 2.4) - 0.055 }
}
pub(crate) fn bilinear(buf: &[f32], w: usize, h: usize, ch: usize, c: usize, x: f32, y: f32) -> f32 {
    let x = x.clamp(0.0, (w - 1) as f32);
    let y = y.clamp(0.0, (h - 1) as f32);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let (x1, y1) = ((x0 + 1).min(w - 1), (y0 + 1).min(h - 1));
    let (tx, ty) = (x - x0 as f32, y - y0 as f32);
    let p = |xx: usize, yy: usize| buf[(yy * w + xx) * ch + c];
    let top = p(x0, y0) + (p(x1, y0) - p(x0, y0)) * tx;
    let bot = p(x0, y1) + (p(x1, y1) - p(x0, y1)) * tx;
    top + (bot - top) * ty
}
 pub(crate) fn par_rows<T: Send + Sync>(buf: &mut [T], w: usize, ch: usize, f: impl Fn(usize, &mut [T]) + Sync + Send) {
   for (y,row) in buf.chunks_mut(w.max(1) * ch).enumerate() { f(y,row); }
 }
}
use photo_util::{linear_to_srgb, srgb_to_linear, par_rows};
#[derive(Clone, Copy)]
pub(crate) struct Encoding(f32);

impl Encoding {
    pub(crate) fn of(gamma: f32) -> Self {
        Encoding(if gamma.is_finite() && gamma > 0.0 { gamma.clamp(0.5, 4.0) } else { 0.0 })
    }
    /// A value in this encoding as linear light.
    pub(crate) fn decode(self, v: f32) -> f32 {
        if self.0 > 0.0 { v.max(0.0).powf(self.0) } else { srgb_to_linear(v) }
    }
    /// Linear light back into this encoding, the inverse of [`Encoding::decode`].
    pub(crate) fn encode(self, v: f32) -> f32 {
        if self.0 > 0.0 { v.max(0.0).powf(1.0 / self.0) } else { linear_to_srgb(v) }
    }
}
fn luma(c: [f32; 3]) -> f32 {
    0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}fn box_mean(v: &[f32], w: usize, h: usize, r: usize) -> Vec<f32> {
    if r == 0 || w == 0 || h == 0 {
        return v.to_vec();
    }
    let n = (2 * r + 1) as f64;
    let mut tmp = vec![0.0f32; w * h];
    par_rows(&mut tmp, w, 1, |y, row| {
        let src = &v[y * w..(y + 1) * w];
        let at = |k: i64| src[k.clamp(0, w as i64 - 1) as usize] as f64;
        let mut acc: f64 = (-(r as i64)..=r as i64).map(at).sum();
        for (x, o) in row.iter_mut().enumerate() {
            *o = (acc / n) as f32;
            acc += at(x as i64 + r as i64 + 1) - at(x as i64 - r as i64);
        }
    });
    const BAND: usize = 256;
    let bands = crate::photo_util::par_map(w.div_ceil(BAND), |b| {
        let (x0, x1) = (b * BAND, ((b + 1) * BAND).min(w));
        let bw = x1 - x0;
        let row = |y: i64| &tmp[y.clamp(0, h as i64 - 1) as usize * w + x0..y.clamp(0, h as i64 - 1) as usize * w + x1];
        let mut acc = vec![0.0f64; bw];
        for y in -(r as i64)..=r as i64 {
            for (a, v) in acc.iter_mut().zip(row(y)) {
                *a += *v as f64;
            }
        }
        let mut out = vec![0.0f32; bw * h];
        for y in 0..h {
            for (o, a) in out[y * bw..(y + 1) * bw].iter_mut().zip(&acc) {
                *o = (*a / n) as f32;
            }
            let (add, sub) = (row(y as i64 + r as i64 + 1), row(y as i64 - r as i64));
            for ((a, p), m) in acc.iter_mut().zip(add).zip(sub) {
                *a += (*p - *m) as f64;
            }
        }
        out
    });
    let mut out = vec![0.0f32; w * h];
    for (b, band) in bands.iter().enumerate() {
        let (x0, x1) = (b * BAND, ((b + 1) * BAND).min(w));
        let bw = x1 - x0;
        for y in 0..h {
            out[y * w + x0..y * w + x1].copy_from_slice(&band[y * bw..(y + 1) * bw]);
        }
    }
    out
}
#[path = "vendor/local_tone.rs"] mod local_tone;

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
