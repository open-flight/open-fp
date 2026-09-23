import cadquery as cq, os
OUT="/mnt/user-data/outputs"; os.makedirs(OUT,exist_ok=True)

# ---------- shared dims ----------
CELL=34.0; CELL_T=7.8              # 50 kg half-bridge cell body (34x34x7.8)
CLR=0.3
M4_INS=5.6; M4_INS_D=6.5           # heat-set insert holes (Bambu-friendly)
M25_INS=3.5; M25_INS_D=5.0
M2_INS=3.2; M2_INS_D=4.0

def export(shape,name):
    cq.exporters.export(shape,f"{OUT}/{name}.stl",tolerance=0.02,angularTolerance=0.1)
    cq.exporters.export(shape,f"{OUT}/{name}.step")

# ---------- 1. Corner cradle (4 per plate) ----------
# Bolts to underside of the aluminum top plate. Pocket holds the cell by its
# outer frame; a centre relief keeps the flexing hub free. Open bottom lets the
# cell's rubber foot touch the floor.
W=54; H=14; POCKET=CELL+2*CLR; PD=CELL_T+0.4; RELIEF_D=24; RELIEF_DEPTH=2.0
cradle=(cq.Workplane("XY").box(W,W,H,centered=(True,True,False))
        .edges("|Z").fillet(4))
cradle=cradle.cut(cq.Workplane("XY").box(POCKET,POCKET,PD,centered=(True,True,False)))
cradle=cradle.cut(cq.Workplane("XY").workplane(offset=PD).circle(RELIEF_D/2).extrude(RELIEF_DEPTH))
# cable notch (-Y side)
cradle=cradle.cut(cq.Workplane("XY").center(0,-W/2+4).box(7,10,PD-1,centered=(True,True,False)))
# M4 inserts (top face) for plate screws
cradle=cradle.cut(cq.Workplane("XY").workplane(offset=H-M4_INS_D)
                  .pushPoints([(22.5,0),(-22.5,0)]).circle(M4_INS/2).extrude(M4_INS_D))
# M2 inserts (bottom face) for retainer frame
cradle=cradle.cut(cq.Workplane("XY").pushPoints([(22.5,22.5),(-22.5,22.5),(22.5,-22.5),(-22.5,-22.5)])
                  .circle(M2_INS/2).extrude(M2_INS_D))
export(cradle,"01_corner_cradle")

# ---------- 2. Retainer frame (4 per plate) ----------
# 2 mm frame under the cell edge; 28 mm window clears the centre foot.
ret=(cq.Workplane("XY").box(W,W,2,centered=(True,True,False)).edges("|Z").fillet(4)
     .cut(cq.Workplane("XY").rect(28,28).extrude(2))
     .cut(cq.Workplane("XY").center(0,-W/2+4).rect(7,10).extrude(2))
     .faces(">Z").workplane().pushPoints([(22.5,22.5),(-22.5,22.5),(22.5,-22.5),(-22.5,-22.5)])
     .cskHole(2.4,4.6,90))
export(ret,"02_cradle_retainer")

# ---------- 3. Electronics enclosure base ----------
# Uno Q (68.6x53.3) + 4x ADS1220 breakouts side by side.
IL,IW,IH,T=150,70,28,2.4
base=(cq.Workplane("XY").box(IL+2*T,IW+2*T,IH+T,centered=(True,True,False)).edges("|Z").fillet(5)
      .cut(cq.Workplane("XY").workplane(offset=T).box(IL,IW,IH,centered=(True,True,False)).edges("|Z").fillet(3)))
def bosses(pts,h,hole,hole_d):
    b=cq.Workplane("XY").workplane(offset=T).pushPoints(pts).circle(3.6).extrude(h)
    return b.cut(cq.Workplane("XY").workplane(offset=T+h-hole_d).pushPoints(pts).circle(hole/2).extrude(hole_d))
# Uno Q at left: board origin at (-IL/2+4, -IW/2+8); Arduino Uno hole pattern
ox,oy=-IL/2+4,-IW/2+8
uno=[(ox+14.0,oy+2.5),(ox+15.3,oy+50.7),(ox+66.1,oy+7.6),(ox+66.1,oy+35.5)]
# ADC bay at right: raised 4 mm pad with a 7.5 mm-pitch grid of blind M2.5
# insert holes. Install inserts only where your 4 ADS1220 breakout holes land
# (ProtoCentral / CJMCU-1220 footprints differ), then mount on 6 mm standoffs.
PAD_L,PAD_W,PAD_H=68,64,4
px0=IL/2-4-PAD_L/2
pad=cq.Workplane("XY").workplane(offset=T).center(px0,0).rect(PAD_L,PAD_W).extrude(PAD_H)
grid=[(px0+i*7.5,j*7.5) for i in range(-4,5) for j in range(-4,5)]
pad=pad.cut(cq.Workplane("XY").workplane(offset=T+PAD_H-3.5).pushPoints(grid).circle(M25_INS/2).extrude(3.5))
base=base.union(bosses(uno,5,M25_INS,M25_INS_D)).union(pad)
# lid posts in corners (M2.5 inserts)
posts=[(IL/2-5,IW/2-5),(-IL/2+5,IW/2-5),(IL/2-5,-IW/2+5),(-IL/2+5,-IW/2+5)]
base=base.union(bosses(posts,IH,M25_INS,M25_INS_D))
# USB-C / power slot on Uno Q end wall, generous 14x8
base=base.cut(cq.Workplane("YZ").workplane(offset=-IL/2-T-1).center(oy+26,T+9).rect(14,8).extrude(T+2))
# 4 load-cell cable slots on ADC end wall
for i in range(4):
    base=base.cut(cq.Workplane("YZ").workplane(offset=IL/2-1).center(-IW/2+12+i*15,T+8).rect(6,8).extrude(T+2))
# side mounting ears (M4) to strap box to plate edge
ears=(cq.Workplane("XY").pushPoints([(0,IW/2+T+6),(0,-IW/2-T-6)]).rect(30,12).extrude(3)
      .faces(">Z").workplane().pushPoints([(-10,IW/2+T+6),(10,IW/2+T+6),(-10,-IW/2-T-6),(10,-IW/2-T-6)]).hole(4.5))
base=base.union(ears)
export(base,"03_enclosure_base")

# ---------- 4. Enclosure lid ----------
lid=(cq.Workplane("XY").box(IL+2*T,IW+2*T,T,centered=(True,True,False)).edges("|Z").fillet(5))
lip=(cq.Workplane("XY").workplane(offset=T).box(IL-0.6,IW-0.6,2,centered=(True,True,False)).edges("|Z").fillet(3)
     .cut(cq.Workplane("XY").workplane(offset=T).box(IL-0.6-2*T,IW-0.6-2*T,2,centered=(True,True,False))))
lid=lid.union(lip)
lid=lid.faces("<Z").workplane().pushPoints([(x,-y) for x,y in posts]).cskHole(2.8,5.5,90)
# vent slots
for i in range(8):
    lid=lid.cut(cq.Workplane("XY").center(-40+i*8,0).box(2,40,T+3,centered=(True,True,False)))
lid=lid.cut(cq.Workplane("XY").pushPoints([(x,-y) for x,y in posts]).circle(3.6).extrude(T+2.5).translate((0,0,T)))  # clear posts in lip
export(lid,"04_enclosure_lid")
print("done")
