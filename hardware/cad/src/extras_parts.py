import cadquery as cq
OUT="/home/claude/extras"; import os; os.makedirs(OUT,exist_ok=True)
def export(s,n):
    cq.exporters.export(s,f"{OUT}/{n}.stl"); cq.exporters.export(s,f"{OUT}/{n}.step")
# 09 drill template: sits on a plate corner, lips hook over two edges.
# Guides for the two M4 holes of one cradle: 30 mm from edge E1, 7.5 / 52.5 mm from edge E2.
TT,LIP,LW,S=4.0,5.0,3.0,75.0
t=cq.Workplane("XY").box(S,S,TT,centered=False)
t=t.union(cq.Workplane("XY").box(LW,S,LIP+TT,centered=False).translate((-LW,0,-LIP)))   # lip on E1 (x=0 edge)
t=t.union(cq.Workplane("XY").box(S+LW,LW,LIP+TT,centered=False).translate((-LW,-LW,-LIP)))  # lip on E2 (y=0 edge)
t=t.cut(cq.Workplane("XY").pushPoints([(30,7.5),(30,52.5)]).circle(4.6/2).extrude(TT+1).translate((0,0,-0.5)))
t=t.cut(cq.Workplane("XY").pushPoints([(30,30)]).circle(3).extrude(TT+1).translate((0,0,-0.5)))  # sight hole = cradle centre
export(t,"09_drill_template_a"); export(t.mirror("YZ"),"09_drill_template_b")
# 10 hub foot (TPU 95A): glued to the load cell's centre boss, only floor contact.
f=cq.Workplane("XY").circle(8).extrude(3.5).faces(">Z").chamfer(0.6)
export(f,"10_hub_foot_tpu")
print("ok")
