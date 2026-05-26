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
    generate_sensor_svg,
)
from utils.tex_utils import generate_sensor_tex

N_PATH_POINTS = 1000


def generate_frames(svg_path):
    # Support "path/to/env.svg_frames" convention:
    #   input SVG  → "path/to/env.svg"
    #   output dir → "path/to/env_frames/"
    if svg_path.endswith('_frames'):
        actual_svg = svg_path[: -len('_frames')]
        dir_suffix = '_frames'
    else:
        actual_svg = svg_path
        dir_suffix = ''

    print(f"Parsing {actual_svg} ...")
    svg_data = parse_svg_env_file(actual_svg)

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

    # Output: environments/<svg_name>[_frames]/frame_NNNN.svg
    svg_name = os.path.splitext(os.path.basename(actual_svg))[0] + dir_suffix
    out_dir = os.path.join(os.path.dirname(os.path.abspath(actual_svg)), svg_name)
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


def generate_sensor_frames(svg_path):
    """Generate one gap-sensor SVG per path point and write to *_sensors_svg/.

    Each frame is a standalone HUD showing the circular sensor ring with a
    coloured tick mark for every currently visible gap.

    Output directory: <svg_dir>/<svg_name>_sensors_svg/
    """
    if svg_path.endswith('_sensors_svg'):
        actual_svg = svg_path[: -len('_sensors_svg')]
        dir_suffix = '_sensors_svg'
    else:
        actual_svg = svg_path
        dir_suffix = '_sensors_svg'

    print(f"Parsing {actual_svg} ...")
    svg_data = parse_svg_env_file(actual_svg)

    print(f"  Wall vertices: {len(svg_data['env_polygon_points'])}")
    print(f"  Path control points: {len(svg_data['path_points'])}")

    print("Building environment ...")
    wall = [Point(x, y) for x, y in svg_data['env_polygon_points']]
    env = Environment()
    env.build([wall], status=True)

    print(f"Interpolating {N_PATH_POINTS} points along path ...")
    path_pts = interpolate_path(svg_data['path_points'], N_PATH_POINTS)

    svg_name = os.path.splitext(os.path.basename(actual_svg))[0] + dir_suffix
    out_dir = os.path.join(os.path.dirname(os.path.abspath(actual_svg)), svg_name)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    print("Generating sensor frames ...")
    for i, (px, py) in enumerate(tqdm(path_pts)):
        pos = Point(px, py)
        try:
            robot = Robot(env, pos)
            gaps = robot.gaps
        except Exception:
            gaps = []
        svg_str = generate_sensor_svg(gaps)
        frame_path = os.path.join(out_dir, f'frame_{i:04d}.svg')
        with open(frame_path, 'w', encoding='utf-8') as f:
            f.write(svg_str)

    print(f"Done — {N_PATH_POINTS} sensor frames saved to {out_dir}")


def generate_sensor_tex_frames(svg_path):
    """Generate one standalone LaTeX/TikZ sensor file per path point.

    Each .tex file can be compiled with ``pdflatex`` or ``lualatex`` to
    produce a standalone PDF of the sensor HUD for that frame.

    Output directory: <svg_dir>/<svg_name>_sensors_tex/
    """
    if svg_path.endswith('_sensors_tex'):
        actual_svg = svg_path[: -len('_sensors_tex')]
        dir_suffix = '_sensors_tex'
    else:
        actual_svg = svg_path
        dir_suffix = '_sensors_tex'

    print(f"Parsing {actual_svg} ...")
    svg_data = parse_svg_env_file(actual_svg)

    print(f"  Wall vertices: {len(svg_data['env_polygon_points'])}")
    print(f"  Path control points: {len(svg_data['path_points'])}")

    print("Building environment ...")
    wall = [Point(x, y) for x, y in svg_data['env_polygon_points']]
    env = Environment()
    env.build([wall], status=True)

    print(f"Interpolating {N_PATH_POINTS} points along path ...")
    path_pts = interpolate_path(svg_data['path_points'], N_PATH_POINTS)

    svg_name = os.path.splitext(os.path.basename(actual_svg))[0] + dir_suffix
    out_dir = os.path.join(os.path.dirname(os.path.abspath(actual_svg)), svg_name)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    print("Generating sensor TeX frames ...")
    for i, (px, py) in enumerate(tqdm(path_pts)):
        pos = Point(px, py)
        try:
            robot = Robot(env, pos)
            gaps = robot.gaps
        except Exception:
            gaps = []
        tex_str = generate_sensor_tex(gaps)
        frame_path = os.path.join(out_dir, f'frame_{i:04d}.tex')
        with open(frame_path, 'w', encoding='utf-8') as f:
            f.write(tex_str)

    print(f"Done — {N_PATH_POINTS} sensor TeX frames saved to {out_dir}")


if __name__ == '__main__':
    svg_file = sys.argv[1] if len(sys.argv) > 1 else 'environments/env_0.svg'
    generate_frames(svg_file + "_frames")
    generate_sensor_frames(svg_file)
    generate_sensor_tex_frames(svg_file)
