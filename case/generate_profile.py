"""

Generate velocity profile for inlet

Call it with: python generate_profile [velocity]

TODO: make it read points file and replace hard coded inlet_bottom and
inlet_top

"""

import sys

import numpy as np
import matplotlib.pyplot as plt

plot_profile = False

if len(sys.argv) < 2:
    raise ValueError('Missing inlet velocity: python generate_profile [velocity]')
target_average_velocity = float(sys.argv[1])

filename = '0.orig/Uprofile.csv'

inlet_bottom = 6.6/1000
inlet_top = 9.6/1000

inlet_height = inlet_top - inlet_bottom

# parabolic profile
n_points = 200
h = np.linspace(-.5,+.5,n_points)
u_norm = -h**2
u_norm -= u_norm[0]

total_velocity = np.trapz(u_norm,h)
scaling_factor = target_average_velocity / total_velocity

u = u_norm *scaling_factor
y = inlet_bottom + inlet_height*(h + 0.5)

arr = np.zeros((n_points,4))
arr[:,0] = y
arr[:,1] = u


foam_header = r'''
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  2206                                  |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    arch        "LSB;label=32;scalar=64";
    class       IOobject;
    location    "0";
    object      Uprofile.csv;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
'''

with open(filename,'w') as f:
    f.write(foam_header)
    np.savetxt(f,arr,delimiter=',')



if plot_profile:
    fig, ax = plt.subplots(1,1,layout='constrained')
    ax.plot(u,y)
    ax.set_xlabel('u, m/s')
    ax.set_ylabel('y, m')
    ax.grid()
    fig.savefig('profile.png')