"""Input/calibration and acceptance contracts for the synthetic linear experiment."""
import numpy as np

class NeutralTransfer:
    def __init__(self,x,y):self.x,self.y=x,y
    @classmethod
    def fit(cls,raw,neutral):
        raw=np.asarray(raw,dtype=float);neutral=np.asarray(neutral,dtype=float)
        if raw.shape!=neutral.shape or raw.ndim!=3 or raw.shape[-1]!=3:raise ValueError('matching RGB images required')
        if not np.isfinite(raw).all() or not np.isfinite(neutral).all():raise ValueError('finite images required')
        if np.max(np.ptp(raw,axis=2))>1e-6 or np.min(raw)<0:raise ValueError('nonnegative neutral source required')
        x=raw[...,0].ravel();y=neutral.mean(axis=2).ravel()
        u,idx=np.unique(x,return_inverse=True)
        means=np.bincount(idx,weights=y)/np.bincount(idx)
        # Neutral pixels at identical input level are averaged; monotonic regression
        # uses adjacent-violator pooling, avoiding a one-sided cumulative-max bias.
        blocks=[]
        for value,count in zip(means,np.bincount(idx)):
            blocks.append([value*count,float(count),1])
            while len(blocks)>1 and blocks[-2][0]/blocks[-2][1]>blocks[-1][0]/blocks[-1][1]:
                b=blocks.pop();a=blocks.pop();blocks.append([a[i]+b[i] for i in range(3)])
        means=np.concatenate([np.repeat(a/b,int(n)) for a,b,n in blocks])
        if u[0]>0:u=np.r_[0,u];means=np.r_[0,means]
        if u[-1]<1:u=np.r_[u,1];means=np.r_[means,1]
        return cls(u,np.clip(means,0,1))
    def __call__(self,x):return np.interp(x,self.x,self.y)

def gate(base,candidate,guard_base,guard_candidate):
    arrays=[np.asarray(x,dtype=float) for x in (base,candidate,guard_base,guard_candidate)]
    b,c,gb,gc=arrays
    if any(x.ndim!=1 or not x.size or not np.isfinite(x).all() for x in arrays) or b.shape!=c.shape or gb.shape!=gc.shape:raise ValueError('matching nonempty finite score vectors required')
    improvement=float(np.mean(b-c));worst=float(np.max(c-b));guard=float(np.max(gc-gb))
    return {'accepted':improvement>=1 and worst<=1 and guard<=.25,'joint_improvement_255':improvement,'worst_joint_regression_255':worst,'worst_guard_regression_255':guard}

def select_index(rows):
    scores=[r['scores'] for r in rows if r['split']=='train']
    if not scores:raise ValueError('training cases required')
    a=np.asarray(scores,dtype=float)
    if a.ndim!=2 or not np.isfinite(a).all():raise ValueError('finite candidate matrix required')
    return int(np.argmin(a.mean(axis=0)))
