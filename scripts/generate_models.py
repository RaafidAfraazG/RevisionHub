"""Procedural binary STL catalogue. Standard library only; dimensions in millimetres.

Run: python scripts/generate_models.py [--output backend/uploads/models]
Faces use outward winding and unit normals. No external CAD files are required.
"""
import argparse
import math
import struct
from pathlib import Path

TAU = math.tau

def triangle(a, b, c):
    u = [b[i]-a[i] for i in range(3)]; v = [c[i]-a[i] for i in range(3)]
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    length = math.sqrt(sum(x*x for x in n))
    if length < 1e-10:
        return []
    return [(tuple(x/length for x in n), a, b, c)]

def quad(a,b,c,d):
    return triangle(a,b,c)+triangle(a,c,d)

def ring(outer, inner, height, n=192, z=0, center=(0,0)):
    # Annular prism; polygonal outer radii allow gear teeth and hex heads.
    radii = outer if isinstance(outer,list) else [outer]*n
    n = len(radii); mesh=[]
    for i in range(n):
        j=(i+1)%n; a=i*TAU/n; b=(i+1)*TAU/n
        def p(r,t,h): return (center[0]+r*math.cos(t),center[1]+r*math.sin(t),h+z)
        ob,oc=p(radii[i],a,0),p(radii[j],b,0)
        ot,od=p(radii[i],a,height),p(radii[j],b,height)
        ib,ic=p(inner,a,0),p(inner,b,0)
        it,idd=p(inner,a,height),p(inner,b,height)
        mesh += quad(ob,oc,od,ot)+quad(ib,it,idd,ic)+quad(ot,od,idd,it)+quad(ob,ib,ic,oc)
    return mesh

def torus(major=150, minor=9, n=256,m=32):
    mesh=[]
    def p(i,j):
        a=i*TAU/n; b=j*TAU/m; r=major+minor*math.cos(b)
        return (r*math.cos(a),r*math.sin(a),minor*math.sin(b))
    for i in range(n):
        for j in range(m): mesh+=quad(p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1))
    return mesh

def rod(start,end,radius,n=24):
    axis=[end[i]-start[i] for i in range(3)]; length=math.sqrt(sum(v*v for v in axis)); w=[v/length for v in axis]
    ref=(0,0,1) if abs(w[2])<.9 else (1,0,0)
    u=(w[1]*ref[2]-w[2]*ref[1],w[2]*ref[0]-w[0]*ref[2],w[0]*ref[1]-w[1]*ref[0]); l=math.sqrt(sum(v*v for v in u)); u=[v/l for v in u]
    v=(w[1]*u[2]-w[2]*u[1],w[2]*u[0]-w[0]*u[2],w[0]*u[1]-w[1]*u[0])
    def p(c,i): return tuple(c[j]+radius*(math.cos(i*TAU/n)*u[j]+math.sin(i*TAU/n)*v[j]) for j in range(3))
    mesh=[]
    for i in range(n): mesh+=quad(p(start,i),p(start,i+1),p(end,i+1),p(end,i))+triangle(start,p(start,i+1),p(start,i))+triangle(end,p(end,i),p(end,i+1))
    return mesh

def perforated(outer,inner,height,count,pitch,hole_radius,slot=False):
    """Tile annular sectors around real through holes. Radial seams share vertices.

    Each sector is star shaped from its hole center; bridge its perimeter to the
    circular/elliptical cutout, leaving holes open through both planar faces.
    """
    mesh=[]; steps=32
    for k in range(count):
        a0=(k-.5)*TAU/count; a1=(k+.5)*TAU/count; mid=k*TAU/count
        cx,cy=pitch*math.cos(mid),pitch*math.sin(mid)
        perimeter=[]; types=[]
        def polar(r,a): return (r*math.cos(a),r*math.sin(a))
        for i in range(steps): perimeter.append(polar(inner+(outer-inner)*i/steps,a0)); types.append('seam')
        for i in range(steps): perimeter.append(polar(outer,a0+(a1-a0)*i/steps)); types.append('wall')
        for i in range(steps): perimeter.append(polar(outer-(outer-inner)*i/steps,a1)); types.append('seam')
        for i in range(steps): perimeter.append(polar(inner,a1-(a1-a0)*i/steps)); types.append('wall')
        holes=[]
        for x,y in perimeter:
            dx,dy=x-cx,y-cy
            # Elliptical slots aligned radially for the brake rotor.
            dr=dx*math.cos(mid)+dy*math.sin(mid); dt=-dx*math.sin(mid)+dy*math.cos(mid)
            ar=hole_radius*(2.8 if slot else 1); at=hole_radius
            f=1/math.sqrt((dr/ar)**2+(dt/at)**2)
            holes.append((cx+dx*f,cy+dy*f))
        for i in range(len(perimeter)):
            j=(i+1)%len(perimeter)
            a,b=perimeter[i],perimeter[j]; c,d=holes[j],holes[i]
            def p(x,z): return (x[0],x[1],z)
            mesh+=quad(p(a,height),p(b,height),p(c,height),p(d,height))
            mesh+=quad(p(a,0),p(d,0),p(c,0),p(b,0))
            mesh+=quad(p(d,0),p(d,height),p(c,height),p(c,0))
            if types[i]=='wall': mesh+=quad(p(a,0),p(b,0),p(b,height),p(a,height))
    return mesh

def bracket():
    # Chamfered L profile, extruded along Y; small clipped corners mimic edge breaks.
    profile=[(0,2),(2,0),(58,0),(60,2),(60,8),(58,10),(14,10),(10,14),(10,48),(8,50),(2,50),(0,48)]
    mesh=[]
    # Profile is CCW in X/Z. Triangulate its concave polygon by ear clipping.
    ids=list(range(len(profile)))
    def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def inside(p,a,b,c): return all(x>=-1e-8 for x in (cross(a,b,p),cross(b,c,p),cross(c,a,p)))
    while len(ids)>2:
        for i in range(len(ids)):
            ia,ib,ic=ids[i-1],ids[i],ids[(i+1)%len(ids)]; a,b,c=[profile[t] for t in (ia,ib,ic)]
            if cross(a,b,c)>0 and not any(inside(profile[t],a,b,c) for t in ids if t not in (ia,ib,ic)):
                for y,order in [(0,(a,b,c)),(28,(c,b,a))]: mesh+=triangle(*[(x,y,z) for x,z in order])
                ids.pop(i); break
        else: raise ValueError('Invalid bracket profile')
    for i,a in enumerate(profile):
        b=profile[(i+1)%len(profile)]; mesh+=quad((a[0],0,a[1]),(a[0],28,a[1]),(b[0],28,b[1]),(b[0],0,b[1]))
    return mesh

def catalogue():
    gear_r=[]
    for _ in range(28): gear_r.extend([36,36,40,40,40,36])
    gear=ring(gear_r,10,12)+ring(18,10,5,z=12)
    hub=ring(16,6,42,z=-21)+ring(30,6,4,z=-19)+ring(30,6,4,z=15)
    for i in range(24):
        a=i*TAU/24; b=a+.14
        hub+=rod((27*math.cos(a),27*math.sin(a),15 if i%2 else -15),(142*math.cos(b),142*math.sin(b),0),1.2)
    hub+=torus(145,3,n=192,m=16)
    return {'spur-gear':gear,'flange':perforated(50,15,9,6,34,4.5)+ring(24,15,10,z=9),
            'bike-rim':torus(),'hub-spokes':hub,'bracket':bracket(),
            'bearing':ring(26,20,13)+ring(14,10,13),
            'brake-disc':perforated(80,23,3,12,57,3.7,slot=True)+ring(31,16,3),
            'hex-bolt':ring(5,0,34,n=64)+ring([9]*6,0,7,z=34)+ring(5.5,0,1.5,n=64,z=-1.5)}

def write_stl(path,mesh):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as f:
        f.write(b'RevisionHub | procedural engineering showcase | millimetres'.ljust(80,b'\0'))
        f.write(struct.pack('<I',len(mesh)))
        for normal,a,b,c in mesh: f.write(struct.pack('<12fH',*normal,*a,*b,*c,0))

def generate(output):
    models=catalogue()
    for name,mesh in models.items(): write_stl(Path(output)/f'{name}.stl',mesh)
    return models

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',default='backend/uploads/models'); args=parser.parse_args()
    for name,mesh in generate(args.output).items(): print(f'{name}: {len(mesh):,} triangles')
