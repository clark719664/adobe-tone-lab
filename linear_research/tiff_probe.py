import struct,json,hashlib
from pathlib import Path
TYPES={1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8,11:4,12:8}
def read_ifds(path):
 b=Path(path).read_bytes(); e='<' if b[:2]==b'II' else '>'; seen=set(); rows=[]
 def walk(o):
  if not o or o in seen:return
  seen.add(o); n=struct.unpack_from(e+'H',b,o)[0]; tags={}
  for j in range(n):
   q=o+2+12*j; t,k,c=struct.unpack_from(e+'HHI',b,q); z=TYPES.get(k,1)*c; v=b[q+8:q+12] if z<=4 else b[struct.unpack_from(e+'I',b,q+8)[0]:][:z]
   if k in [3,4]: vals=struct.unpack(e+({3:'H',4:'I'}[k])*c,v[:z]); val=vals[0] if len(vals)==1 else vals
   elif k==2:val=v.rstrip(b'\0').decode('utf8','replace')
   else:val=v.hex() if z<40 else f'{z} bytes'
   tags[t]=val
  rows.append({'offset':o,'tags':tags})
  if 330 in tags:
   sub=tags[330]; sub=[sub] if isinstance(sub,int) else sub
   for so in sub:walk(so)
  walk(struct.unpack_from(e+'I',b,o+2+12*n)[0])
 walk(struct.unpack_from(e+'I',b,4)[0]); return b,e,rows
if __name__=='__main__':
 import sys
 for p in sys.argv[1:]:
  b,e,r=read_ifds(p); print(p,json.dumps(r,indent=2))
