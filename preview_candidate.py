"""Experimental joint-only preview coupling, not an Adobe RAW-stage implementation."""
import numpy as np


def decode(x):
    x=np.asarray(x,dtype=np.float64)
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)


def encode(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,12.92*x,1.055*x**(1/2.4)-.055)


def features(baseline,neutral,shadow,highlights):
    weights=np.array([.2126,.7152,.0722])
    n=decode(neutral)@weights;s=decode(shadow)@weights
    gain=np.log2((s+1/65536)/(n+1/65536))
    return decode(baseline),gain*np.clip(-highlights/100,0,1)


def apply_features(data,coefficient):
    linear,gain=data
    return encode(linear*np.exp2(-coefficient*gain)[...,None])


def correct(baseline,neutral,shadow,shadows,highlights,coefficient):
    if not 0<=coefficient<=1:raise ValueError('coefficient must be in0..1')
    if shadows<=0 or highlights>=0 or coefficient==0:return np.asarray(baseline).copy()
    return apply_features(features(baseline,neutral,shadow,highlights),coefficient)


def fit(rows):
    train=[r for r in rows if r['split']=='train' and r['shadows']>0 and r['highlights']<0]
    if not train:raise ValueError('joint train cases required')
    prepared=[(features(r['baseline'],r['default'],r['shadow'],r['highlights']),r['oracle']) for r in train]
    scores=[]
    for a in np.linspace(0,1,21):
        errors=[float(np.abs(apply_features(f,a)-oracle).mean()*255) for f,oracle in prepared]
        scores.append((float(np.mean(errors)),float(a)))
    error,coefficient=min(scores)
    return {'coefficient':coefficient,'train_mean_mae_255':error,'selection':'train families only; one bounded coefficient; fixed0.05grid'}
