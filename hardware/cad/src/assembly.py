import cadquery as cq, cairosvg
OUT="/mnt/user-data/outputs"
P=304.8; PT=6.35; PAD=1.6; RUN=60; GAP=2
L=lambda n: cq.importers.importStep(f"{OUT}/{n}.step")
cradle,ret,eb,el,rr,rl=[L(n) for n in ["01_corner_cradle","02_cradle_retainer","03_centre_enclosure_base","04_centre_enclosure_lid","07_edge_ramp_right","07_edge_ramp_left"]]
plate=cq.Workplane("XY").rect(P,P).extrude(PT).edges("|Z").fillet(8)
mat=cq.Workplane("XY").rect(P,P).extrude(PAD).edges("|Z").fillet(8)
cell=cq.Workplane("XY").rect(34,34).extrude(7.8).edges("|Z").fillet(4)
nub=cq.Workplane("XY").circle(9).extrude(3)
ins=30; corners=[(P/2-ins,P/2-ins),(-P/2+ins,P/2-ins),(P/2-ins,-P/2+ins),(-P/2+ins,-P/2+ins)]
asm=cq.Assembly()
def add_plate(cx,tag):
    asm.add(plate,name=f"plate{tag}",loc=cq.Location(cq.Vector(cx,0,14.2)))
    asm.add(mat,name=f"mat{tag}",loc=cq.Location(cq.Vector(cx,0,14.2+PT)))
    for i,(x,y) in enumerate(corners):
        asm.add(cradle,name=f"cr{tag}{i}",loc=cq.Location(cq.Vector(cx+x,y,3.0)))
        asm.add(ret,name=f"rt{tag}{i}",loc=cq.Location(cq.Vector(cx+x,y,1.4)))
        asm.add(cell,name=f"ce{tag}{i}",loc=cq.Location(cq.Vector(cx+x,y,3.0)))
        asm.add(nub,name=f"nb{tag}{i}",loc=cq.Location(cq.Vector(cx+x,y,0)))
    off=P/2+GAP
    for k,ang in enumerate([a for a in (0,90,180,270) if a!=(90 if cx<0 else 270)]):
        asm.add(rr,name=f"rr{tag}{k}",loc=cq.Location(cq.Vector(cx,0,0),cq.Vector(0,0,1),ang)*cq.Location(cq.Vector(0,-off,0)))
        asm.add(rl,name=f"rl{tag}{k}",loc=cq.Location(cq.Vector(cx,0,0),cq.Vector(0,0,1),ang)*cq.Location(cq.Vector(0,-off,0)))
SP=P+60.8+2*GAP
add_plate(-SP/2,"A"); add_plate(SP/2,"B")
asm.add(eb,name="enclosure",loc=cq.Location(cq.Vector(0,0,0),cq.Vector(0,0,1),90))
asm.add(el,name="lid",loc=cq.Location(cq.Vector(0,0,19.9),cq.Vector(0,0,1),90))
asm.save(f"{OUT}/08_assembly_two_plates.step")
comp=cq.Workplane().add(asm.toCompound())
def render(shape,name,dirn,w=1600,h=800):
    cq.exporters.export(shape,f"/home/claude/{name}.svg",opt={"projectionDir":dirn,"width":w,"height":h,"strokeWidth":0.5,"showHidden":False,"strokeColor":(40,40,40)})
    cairosvg.svg2png(url=f"/home/claude/{name}.svg",write_to=f"{OUT}/mockup_{name}.png",output_width=w,background_color="white")
render(comp,"two_plates_iso",(1,-1,0.7))
#sec=comp.intersect(cq.Workplane("XY").box(120,500,60).translate((-SP/2+P/2+40,0,20)))
#render(sec,"edge_section",(1,0,0.15),1200,400)
