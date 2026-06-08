I want to incoperate functions in C:\Users\selen\OneDrive - Texas A&M University\Project\NARS\figures\vgm\plot_vgm_lift.py into this repo.
That function plots the (p,\theta) curves of all positive and negative tangents of an environment.
The ultimate goal is to be able to generate animation frame of the gaps' motion on the (p,\theta) curves along side those of the robot moving in the environment.

The new environment file /environments/env_1_smooth.svg now has an additional path named "curve",
that is the smooth version of the environment (the "env" curve is a polygon approximation of "curve" so that it could be used in this code).


1. read and understand what plot_vgm_lift.py do and how it is done. Note that there are some details about how to concatenate different plots from different curves. Do not get lost in irrelevent functions. The only addtional thing needed is the function that handles polygonal edges that lead to vertical line in that plot.

2. After you are able to make the plot, confirm with me what it looks like.

3. Then I want you make the gap detected in the polygonal environment to the plot from the smooth curve. The mapping first find candidates with very similar angle (\theta), then with in the candidates, locate the one with the nearest gap point (p).

Write concise and clear comments.
Keep the code structure simple and human-readable.
