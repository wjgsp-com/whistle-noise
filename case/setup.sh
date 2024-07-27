#!/bin/bash
#
# Defining the case
#
# ```
#  setup.sh -d {dimension} -m {model} -u {velocity} -n {number of procs}
# ```
#
# Arguments
# ---------
# d: `2D` or `3D``
# m: `test`, `URANS` or `LES`
# u: inlet average velocity in meters per second
# n: number of processors
#
###################################################################

# default setup
dimension='2D'
model='test'
inlet_velocity=6.0
nprocs=14

while getopts "d:m:u:n:" arg; do
  case $arg in
    d) dimension=$OPTARG ;;
    m) model=$OPTARG ;;
    u) inlet_velocity=$OPTARG ;;
    n) nprocs=$OPTARG ;;
  esac
done

# generate the velocity profile
python generate_profile.py $inlet_velocity

files=$( find . -name "*.${dimension}*" -o -name "*.${model}*")
for f in $files
do
  folder=$( dirname $f )
  dict=$( basename $f )
  dict=${dict%%.*}
  cp -v $f $folder/$dict
  # remove all the options
  find . -name "$dict.*" -type f -delete
done

# replace the number of procs
sed -i "s/numberOfSubdomains  14;/numberOfSubdomains  ${nprocs};/g" system/decomposeParDict
