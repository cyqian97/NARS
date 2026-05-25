"""Generate SVG animation frames showing hidden areas along a robot path.

Usage:
    python generate_frames.py [path/to/env.svg]

Reads the SVG file, builds the environment, uniformly samples N_PATH_POINTS
points along the trajectory, and writes one SVG frame per point to
environments/<svg_name>/.
"""

import os
import sys

from tqdm import tqdm

from backend.environment import Environment
from backend.robot import Robot
from pyvisgraph.classes import Point
from utils.svg_utils import (
    parse_svg_env_file,
    interpolate_path,
    compute_shadow_polygons,
    generate_frame_svg,
)

N_PATH_POINTS = 1000


def generate_frames(svg_path):
    print(f"Parsing {svg_path} ...")
    svg_data = parse_svg_env_file(svg_path)

    print(f"  Wall vertices: {len(svg_data['env_polygon_points'])}")
    print(f"  Path control points: {len(svg_data['path_points'])}")

    # Build backend environment from the parsed wall polygon
    print("Building environment ...")
    wall = [Point(x, y) for x, y in svg_data['env_polygon_points']]
    env = Environment()
    env.build([wall], status=True)
    polygon_graph = env.polygon_graph

    # Uniformly sample N points along the trajectory polyline
    print(f"Interpolating {N_PATH_POINTS} points along path ...")
    path_pts = interpolate_path(svg_data['path_points'], N_PATH_POINTS)

    # Output: environments/<svg_name>/frame_NNNN.svg
    svg_name = os.path.splitext(os.path.basename(svg_path))[0]
    out_dir = os.path.join(os.path.dirname(os.path.abspath(svg_path)), svg_name)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    # Generate one SVG per interpolated path point
    print("Generating frames ...")
    for i, (px, py) in enumerate(tqdm(path_pts)):
        pos = Point(px, py)
        try:
            robot = Robot(env, pos)
            shadow_polys = compute_shadow_polygons(robot.pos, robot.gaps, polygon_graph)
        except Exception:
            shadow_polys = []
        svg_str = generate_frame_svg(svg_data, px, py, shadow_polys)
        frame_path = os.path.join(out_dir, f'frame_{i:04d}.svg')
        with open(frame_path, 'w', encoding='utf-8') as f:
            f.write(svg_str)

    print(f"Done — {N_PATH_POINTS} frames saved to {out_dir}")


if __name__ == '__main__':
    svg_file = sys.argv[1] if len(sys.argv) > 1 else 'environments/env_0.svg'
    generate_frames(svg_file+"_frames")
