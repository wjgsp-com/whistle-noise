#!/bin/bash
#
# Case launcher
# Need to run freecad-extract-points.py before!
#
###############################################################################

set -e # stop if eror

runs_folder=$( realpath '../runs/')

# change following variables for 
case_name='whistle'
dimension='2D'
model='LES.WALE'
inlet_u='5.5'
nprocs='14'

mesh_name="fine-wall-modelled-${dimension}"
model_name='sports-whistle'

run_name="LES.WALE-${dimension}.wall.resolved-${inlet_u}"

full_name="${case_name}_${run_name}"
destination_folder="${runs_folder}/${full_name}"

[[ -d $destination_folder ]] && rm -r $destination_folder
rsync -a $case_name/ $destination_folder

# mesh before calling
cp "../model/output/vertex-${model_name}.csv" "$destination_folder/constant"
cp "../mesh/gmsh-sports-whistle.py" $destination_folder
cp "../mesh/parameters-${mesh_name}.yml" "$destination_folder/constant"
cd $destination_folder

echo "Meshing..."
python gmsh-sports-whistle.py \
    "constant/vertex-${model_name}.csv" \
    "constant/parameters-${mesh_name}.yml" \
    ./constant \
    > log.gmsh
echo "Done."

bash setup.sh -d $dimension -m $model -u $inlet_u -n $nprocs

nohup ./Allrun &> log.Allrun &