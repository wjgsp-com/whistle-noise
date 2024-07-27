""" Generates mesh of sports whistle using gmsh

Extruded 2D unstructured mesh. Default parameters produces a refined for
running with LES (quality of result not checked!)
TODO: put defualt values here!

Call it with:

```
    python gmsh-sports-whistle.py {points file} {parameters file} [output folder]
```

Since the mesh commands are tailored to a given set of points, the only model
it considers is `sports-whistle-v06-half-circle-domain`.

For a true 3D version select a number of layers `n_extrude` bigger than 1

Note that the use of quad recombined mesh and 3D extrude is not possible
https://gitlab.onelab.info/gmsh/gmsh/-/issues/2623
https://gitlab.onelab.info/gmsh/gmsh/-/issues/2046
https://gitlab.onelab.info/gmsh/gmsh/-/issues/2467

"""

import sys
import yaml

import pandas as pd
import numpy as np

import gmsh


def buildMesh(points_file,parameters,name='test',output_folder='./output'):
    """
    
    Arguments
    ---------
    points_file :
        path to CSV file with points
    parameters : dict
        dictionary with all the mesh parameters
    
    """

    gmsh.initialize()
    factory = gmsh.model.geo
    gmsh.model.add(name)

    # 2D mesh algorithm (Default value: 6)
    # 1: MeshAdapt, 2: Automatic, 3: Initial mesh only, 5: Delaunay
    # 6: Frontal-Delaunay, 7: BAMG, 8: Frontal-Delaunay for Quads
    # 9: Packing of Parallelograms, 11: Quasi-structured Quad
    gmsh.option.setNumber('Mesh.Algorithm',8)
    # 3D mesh algorithm (Default value: 1)
    # 1: Delaunay, 3: Initial mesh only, 4: Frontal, 7: MMG3D, 9: R-tree, 10: HXT
    gmsh.option.setNumber('Mesh.Algorithm3D',1)
    gmsh.option.setNumber('Mesh.BoundaryLayerFanElements',parameters['bl_number_fan_elements'])


    # read points coordinates exported from CAD file using 
    # `freecade-extract-points.py'
    cad_points = pd.read_csv(points_file,index_col=0)
    points_coords = cad_points.to_numpy()

    points = {}
    for p, coords in zip(cad_points.index.tolist(),points_coords):
        points[p] = factory.addPoint(*coords.tolist(),parameters['lc'])
    factory.synchronize()

    lines = {}
    loops = {}
    surfaces = {}

    # list of predefined-surfaces (more than 4 cornes) in order to define the
    predefined_surfaces = []

    def define_connected_lines(connectivity):
        for i in range(len(connectivity)-1):
            name_start, name_end = connectivity[i], connectivity[i+1]
            start, end = points[name_start],points[name_end]
            lines[f'{name_start}_TO_{name_end}'] = factory.addLine(start,end)

    def define_connected_arcs(connectivity,center):
        for i in range(len(connectivity)-1):
            start_name, end_name = connectivity[i], connectivity[i+1]
            start, end = points[start_name], points[end_name]
            line_name = f'{start_name}_TO_{end_name}'
            lines[line_name] = factory.addCircleArc(start,points[center],end)

    ###############################################################################
    # cavity arcs
    define_connected_lines(['channel-start-bottom','channel-end-bottom','cavity-start-bottom'])
    define_connected_arcs(
        ['cavity-start-bottom','cavity-left','cavity-bottom','cavity-right','cavity-top',
        'wedge-tip'],
        'center')
    define_connected_lines(['wedge-tip','wedge-top'])
    define_connected_arcs(['wedge-top','outlet-right-wall',],'center')
    half_circle = True
    if not half_circle:
        define_connected_lines(['outlet-right-wall','outlet-right-boundary'])
        define_connected_arcs(['outlet-right-boundary','outlet-center-boundary',],'center')
    else:
        define_connected_arcs(['outlet-right-wall','outlet-bottom-wall',],'center')
        define_connected_lines(['outlet-bottom-wall','outlet-bottom-boundary'])
        define_connected_arcs(['outlet-bottom-boundary','outlet-right-boundary',],'center')
        define_connected_arcs(['outlet-right-boundary','outlet-center-boundary',],'center')
        

    left_with_arc = True
    if not left_with_arc:
        define_connected_lines(
            ['outlet-center-boundary','outlet-left-boundary','outlet-left-wall','cavity-start-top',
            'channel-end-top','channel-start-top','channel-start-bottom']
            )
    else:
        # left opening arc
        define_connected_arcs(['outlet-center-boundary','outlet-left-boundary',],'center')
        define_connected_lines(
            ['outlet-left-boundary','outlet-left-wall','cavity-start-top',
            'channel-end-top','channel-start-top','channel-start-bottom']
            )



    name_lines = list(lines.keys())
    list_lines = [lines[k] for k in name_lines]

    loops['front'] = factory.addCurveLoop(list_lines)
    surfaces['front'] = factory.addPlaneSurface([loops['front']])

    # index_end_bottom_wall = name_lines.index('wedge-top_TO_outlet-right-wall')
    index_end_bottom_wall = name_lines.index('outlet-right-wall_TO_outlet-bottom-wall')
    index_outer_left_wall = name_lines.index('outlet-left-wall_TO_cavity-start-top')


    curve_bl_list = list_lines[:index_end_bottom_wall+1]
    f_bl_bottom = gmsh.model.mesh.field.add('BoundaryLayer')
    gmsh.model.mesh.field.setNumbers(f_bl_bottom,'CurvesList',curve_bl_list)
    gmsh.model.mesh.field.setNumbers(
        f_bl_bottom,'PointsList',
        [points[p] for p in ['channel-start-bottom','outlet-bottom-wall']]
        )
    gmsh.model.mesh.field.setNumbers(
        f_bl_bottom,'FanPointsList',
        [points[p] for p in ['channel-end-bottom','cavity-start-bottom','wedge-tip','wedge-top']]
        )

    curve_bl_list = list_lines[index_outer_left_wall:-1]
    f_bl_top = gmsh.model.mesh.field.add('BoundaryLayer')
    gmsh.model.mesh.field.setNumbers(f_bl_top,'CurvesList',curve_bl_list)
    gmsh.model.mesh.field.setNumbers(
        f_bl_top,'PointsList',
        [points[p] for p in ['channel-start-top','outlet-left-wall']]
        )
    gmsh.model.mesh.field.setNumbers(
        f_bl_top,'FanPointsList',
        [points[p] for p in ['channel-end-top','cavity-start-top']]
        )

    for f in (f_bl_bottom,f_bl_top):
        gmsh.model.mesh.field.setNumber(f,'BetaLaw',0)
        gmsh.model.mesh.field.setNumber(f,'Ratio',parameters['bl_ratio'])
        gmsh.model.mesh.field.setNumber(f,'Size',parameters['bl_first_layer'])
        gmsh.model.mesh.field.setNumber(f,'Quads',parameters['bl_quads'])
        gmsh.model.mesh.field.setNumber(f,'Thickness',parameters['bl_thickness'])

        gmsh.model.mesh.field.setAsBoundaryLayer(f)
    factory.synchronize()


    f_distance = gmsh.model.mesh.field.add('Distance')
    gmsh.model.mesh.field.setNumber(f_distance,'Sampling',100)
    gmsh.model.mesh.field.setNumbers(f_distance,'PointsList',[points['wedge-tip']])

    f_threshold = gmsh.model.mesh.field.add('Threshold')
    gmsh.model.mesh.field.setNumber(f_threshold,'SizeMin',parameters['wedge_lc'])
    gmsh.model.mesh.field.setNumber(f_threshold,'SizeMax',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_threshold,'DistMin',parameters['wedge_refinement_zone_inner_radius'])
    gmsh.model.mesh.field.setNumber(f_threshold,'DistMax',parameters['wedge_refinement_zone_outer_radius'])
    gmsh.model.mesh.field.setNumber(f_threshold,'Sigmoid',False)
    gmsh.model.mesh.field.setNumber(f_threshold,'InField',f_distance)


    f_box_channel = gmsh.model.mesh.field.add('Box')
    gmsh.model.mesh.field.setNumber(f_box_channel,'VIn',parameters['channel_lc'])
    gmsh.model.mesh.field.setNumber(f_box_channel,'VOut',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_box_channel,'XMin',gmsh.model.getValue(0,points['channel-start-bottom'],[])[0])
    gmsh.model.mesh.field.setNumber(f_box_channel,'XMax',gmsh.model.getValue(0,points['channel-end-bottom'],[])[0])
    gmsh.model.mesh.field.setNumber(f_box_channel,'YMin',gmsh.model.getValue(0,points['channel-start-bottom'],[])[1])
    gmsh.model.mesh.field.setNumber(f_box_channel,'YMax',gmsh.model.getValue(0,points['channel-start-top'],[])[1])
    gmsh.model.mesh.field.setNumber(f_box_channel,'Thickness',5*parameters['lc'])


    # create line to define a refinement from channel end to the wedge tip
    define_connected_lines(['channel-end-center','wedge-tip'])
    f_distance_opening = gmsh.model.mesh.field.add('Distance')
    gmsh.model.mesh.field.setNumber(f_distance_opening,'Sampling',100)
    gmsh.model.mesh.field.setNumbers(f_distance_opening,'CurvesList',[lines['channel-end-center_TO_wedge-tip']])

    f_opening = gmsh.model.mesh.field.add('Threshold')
    gmsh.model.mesh.field.setNumber(f_opening,'SizeMin',parameters['jet_to_wedge_lc'])
    gmsh.model.mesh.field.setNumber(f_opening,'SizeMax',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_opening,'DistMin',parameters['opening_refinement_zone_inner_radius'])
    gmsh.model.mesh.field.setNumber(f_opening,'DistMax',parameters['opening_refinement_zone_outer_radius'])
    gmsh.model.mesh.field.setNumber(f_opening,'Sigmoid',True)
    gmsh.model.mesh.field.setNumber(f_opening,'InField',f_distance_opening)


    # create line to define a refinement after the jet impacts the wedge
    refinement_line_start = np.array(gmsh.model.getValue(0,points['wedge-tip'],[]))
    wedge_vector = np.array(gmsh.model.getValue(0,points['wedge-top'],[])) - refinement_line_start
    wedge_vector /= np.linalg.norm(wedge_vector)
    wedge_jet = refinement_line_start + parameters['wedge_jet_refinement_length']*wedge_vector
    points['wedge-jet'] = factory.addPoint(*wedge_jet.tolist(),parameters['lc'])

    define_connected_lines(['wedge-top','wedge-jet'])
    f_distance_wedge_jet = gmsh.model.mesh.field.add('Distance')
    gmsh.model.mesh.field.setNumber(f_distance_wedge_jet,'Sampling',100)
    gmsh.model.mesh.field.setNumbers(f_distance_wedge_jet,'CurvesList',[lines['wedge-top_TO_wedge-jet']])
    f_wedge_jet = gmsh.model.mesh.field.add('Threshold')
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'SizeMin',parameters['wedge_jet_lc'])
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'SizeMax',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'DistMin',parameters['wedge_jet_refinement_zone_inner_radius'])
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'DistMax',parameters['wedge_jet_refinement_zone_outer_radius'])
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'Sigmoid',True)
    gmsh.model.mesh.field.setNumber(f_wedge_jet,'InField',f_distance_wedge_jet)


    # refine close to domain edges
    f_distance_domain_edges = gmsh.model.mesh.field.add('Distance')
    gmsh.model.mesh.field.setNumber(f_distance_domain_edges,'Sampling',100)
    gmsh.model.mesh.field.setNumbers(
        f_distance_domain_edges,
        'PointsList',[points['outlet-left-wall'],points['cavity-start-top']]#,points['outlet-right-wall']]
        )
    f_domain_edges = gmsh.model.mesh.field.add('Threshold')
    gmsh.model.mesh.field.setNumber(f_domain_edges,'SizeMin',parameters['domain_edges_jet_lc'])
    gmsh.model.mesh.field.setNumber(f_domain_edges,'SizeMax',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_domain_edges,'DistMin',parameters['domain_edges_refinement_zone_inner_radius'])
    gmsh.model.mesh.field.setNumber(f_domain_edges,'DistMax',parameters['domain_edges_refinement_zone_outer_radius'])
    gmsh.model.mesh.field.setNumber(f_domain_edges,'Sigmoid',True)
    gmsh.model.mesh.field.setNumber(f_domain_edges,'InField',f_distance_domain_edges)


    f_cylinder_cavity = gmsh.model.mesh.field.add('Cylinder')
    cavity_radius = gmsh.model.getValue(0,points['cavity-right'],[])[0] - gmsh.model.getValue(0,points['center'],[])[0]
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'VIn',parameters['cavity_lc'])
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'VOut',parameters['lc'])
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'Radius',cavity_radius)
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'XCenter',gmsh.model.getValue(0,points['center'],[])[0])
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'YCenter',gmsh.model.getValue(0,points['center'],[])[1])
    gmsh.model.mesh.field.setNumber(f_cylinder_cavity,'ZCenter',gmsh.model.getValue(0,points['center'],[])[2])


    f_min = gmsh.model.mesh.field.add('Min')
    gmsh.model.mesh.field.setNumbers(
        f_min,'FieldsList',
        [f_threshold,f_box_channel,f_cylinder_cavity,f_opening,f_wedge_jet,f_domain_edges],
        )
    gmsh.model.mesh.field.setAsBackgroundMesh(f_min)


    volume = gmsh.model.geo.extrude(
        [(2,surfaces['front'])],
        0,0,parameters['h'],
        [parameters['n_extrude']],[1.0],
        recombine=parameters['recombine_extrude']
        )
    factory.synchronize()


    wall_faces = [f[1] for f in volume[2:2+(index_end_bottom_wall+1)]]
    for i in range(index_outer_left_wall+2,len(volume)-1):
        wall_faces.append(volume[i][1])
    outlet_faces = [f[1] for f in volume[index_end_bottom_wall+3:index_outer_left_wall+2]]

    group_fluid  = gmsh.model.addPhysicalGroup(3,[volume[1][1]],name='fluid')
    group_front  = gmsh.model.addPhysicalGroup(2,[volume[0][1]],name='front')
    group_inlet  = gmsh.model.addPhysicalGroup(2,[volume[-1][1]],name='inlet')
    group_walls  = gmsh.model.addPhysicalGroup(2,wall_faces,name='walls')
    group_back   = gmsh.model.addPhysicalGroup(2,[surfaces['front']],name='back')
    group_outlet = gmsh.model.addPhysicalGroup(2,outlet_faces,name='outlet')


    gmsh.option.setNumber('Mesh.Smoothing',5)
    gmsh.model.mesh.generate(2)
    if parameters['recombine_2D']: gmsh.model.mesh.recombine()
    if parameters['mesh_3D']:
        gmsh.model.mesh.generate(3)
        gmsh.write(f'{output_folder}/{name}.msh')
    else:
        gmsh.write(f'{output_folder}/{name}.msh')

    gmsh.finalize()


if __name__ == '__main__':
    
    whistle_model = 'sports-whistle-v06-half-circle-domain'
    points_file = f'../model/output/vertex-{whistle_model}.csv'

    if len(sys.argv) < 3:
        raise ValueError(
            'Missing parameters file: \
               python gmsh-sports-whistle.py [points file] [parameters file]'
            )
    points_file = sys.argv[1]
    parameters_file = sys.argv[2]
    output_folder = 'output'
    if len(sys.argv) == 4: output_folder = sys.argv[3]

    with open(parameters_file,'r') as f: parameters = yaml.safe_load(f)
    name = parameters['name']

    buildMesh(points_file,parameters,name=name,output_folder=output_folder)
