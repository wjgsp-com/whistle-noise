"""

Extract the points coordinates from the FreeCAD model

Call it: python freecad-extract-points.py [model name]

"""

import sys
sys.path.append('/usr/lib64/freecad/lib64')
import FreeCAD as fcd

if len(sys.argv) < 2:
    raise ValueError('Missing model name: python freecad-extract-points.py [model name]')
model_name = sys.argv[1]

filename = f'./{model_name:}.FCStd'

doc = fcd.open(filename)
sketch = doc.getObjectsByLabel('Sketch_open')[0]

# one can extract the vertexes easily if ignoring construction nodes with
# `sketch.Shape.Vertexes`

vertexes = []

for i, obj in enumerate(sketch.Geometry):
    if obj.TypeId == 'Part::GeomCircle':
        vertexes.append(obj.Center)
    if obj.TypeId == 'Part::GeomArcOfCircle':
        vertexes.append(obj.Center)
        vertexes.append(obj.StartPoint)
        vertexes.append(obj.EndPoint)
    if obj.TypeId == 'Part::GeomLineSegment':
        vertexes.append(obj.StartPoint)
        vertexes.append(obj.EndPoint)
    if obj.TypeId == 'Part::GeomPoint':
        vertexes.append(fcd.Vector(obj.X,obj.Y,obj.Z))

print('n/List of points:')
for i,v in enumerate(vertexes): print(i,i+1,v)

# get the vertex of interest
# list defined manuqlly because it is not possible to explicitly name elements
# in FreeCAD skecth
points = {}
# consider vertex - 1 because the numbering in the GUI is one-based
points['center'] = vertexes[0]


points['channel-start-top'] = vertexes[24]
points['channel-start-center'] = vertexes[5]
points['channel-start-bottom'] = vertexes[27]
points['channel-end-bottom'] = vertexes[28]
points['channel-end-center'] = vertexes[66]
points['channel-end-top'] = vertexes[19]

points['cavity-start-bottom'] = vertexes[30]
points['cavity-start-top'] = vertexes[20]

points['wedge-bottom'] = vertexes[48]
points['wedge-tip'] = vertexes[15]
points['wedge-top'] = vertexes[35]

points['cavity-left'] = vertexes[50]
points['cavity-bottom'] = vertexes[45]
points['cavity-right'] = vertexes[46]
points['cavity-top'] = vertexes[48]


points['outlet-left-wall'] = vertexes[61]
points['outlet-left-boundary'] = vertexes[60]

points['channel-end-center'] = vertexes[64]
points['outlet-center-boundary'] = vertexes[57]

points['outlet-right-wall'] = vertexes[68]
points['outlet-right-boundary'] = vertexes[69]
points['outlet-bottom-wall'] = vertexes[54]
points['outlet-bottom-boundary'] = vertexes[59]


digits = 12
with open(f'./output/vertex-{model_name}.csv','w') as f:
    f.writelines('name,x,y,z\n')
    for v in points:
        p = points[v]
        f.writelines(
            f'{v},{round(p.x,digits)},{round(p.y,digits)},{round(p.z,digits)}\n'
            )