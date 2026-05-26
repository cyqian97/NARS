Previously you use this codebase to compute gaps and shadow areas along a path in the environment from environments/env_0.svg, now I want you to also visualize the gap sensor at each of these points along the same path. In the pygame script, there is already a sensor visualization, consists of a big circle with a dot in the center, and short line segments on the big circle indicating the gap detections and there directions. You will plot the same thing but this time in svg.


These are requirements on implementation
1. Add new functions into generate_frames.py rather than start a new file.
2. Output dir: {env_file_name}_sensors_svg