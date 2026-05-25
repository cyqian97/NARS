I want to lead a environment and a path from an svg file, compute the hidden areas (shaded regions) along the path, and output a sequence of svg frames. The environment is defined in environments/env_0.svg. It contains a "env" path that defines the wall of the environment (the 0th outmost polygon), a "path" path that is a polyline and defines the robot path, and a "robot" group which consists of two circle and defines how the robot should be visualized.

I want you to
1. read the "env" path and set it the outer boundary of the environment (wall)
2. read the "path" path, uniformly interpolate N_PATH_POINTS=1000 points along the path
3. For each point along the path, compute the hidden regions
4. Generate a svg file to visualize the environment, the robot, and the hidden regions at each interpolated point on the trajectory.
5. In the generate svg files, the environment is visualized in the same way as in the environment svg file, the "robot" group should be put at the position of the interpolated point, a gray polygon should be drawn on top of the environment for each hidden region.


Below are additional requirements for the implementation:
1. the svg related functions should be put in the utils folder
2. the frames should be save in the environments folder, in a subfolder named the same as the svg file