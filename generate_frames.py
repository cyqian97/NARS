"""Generate per-frame visualizations along a robot path.

Usage:
    python generate_frames.py [path/to/env.svg]

For each of N_PATH_POINTS uniformly spaced points along the trajectory the
script writes four files into four sibling output directories:

    <env>_frames/frame_NNNN.svg        shadow / hidden-area frames
    <env>_sensors_svg/frame_NNNN.svg   gap-sensor HUD frames (SVG)
    <env>_sensors_tex/frame_NNNN.tex   gap-sensor HUD frames (TikZ)
    <env>_cyclic_svg/frame_NNNN.svg    cyclic-order diagrams (SVG)

With --event-lines, one additional file is written:

    <env>_event_lines.svg              all critical-event edges (static, one frame)
"""

import os
import shutil
import sys

from tqdm import tqdm

from backend.environment import Environment
from backend.robot import Robot
from pyvisgraph.classes import Point, Edge
from utils.svg_utils import (
    parse_svg_env_file,
    interpolate_path,
    compute_shadow_polygons,
    generate_frame_svg,
    generate_event_lines_svg,
    generate_sensor_svg,
    generate_cyclic_svg,
)
from utils.tex_utils import generate_sensor_tex

N_PATH_POINTS = 500


def generate_frames(svg_path, show_frame_number=False, show_event_lines=False):
    """Parse *svg_path* once, then write all three frame types per path point."""
    print(f"Parsing {svg_path} ...")
    svg_data = parse_svg_env_file(svg_path)
    print(f"  Wall vertices   : {len(svg_data['env_polygon_points'])}")
    print(f"  Path ctrl points: {len(svg_data['path_points'])}")

    print("Building environment ...")
    wall = [Point(x, y) for x, y in svg_data['env_polygon_points']]
    env = Environment()
    env.build([wall], status=True)
    polygon_graph = env.polygon_graph

    print(f"Interpolating {N_PATH_POINTS} points along path ...")
    path_pts = interpolate_path(svg_data['path_points'], N_PATH_POINTS)
    

    base = os.path.splitext(os.path.abspath(svg_path))[0]
    dirs = {
        'shadow':      base + '_frames',
        'sensor_svg':  base + '_sensors_svg',
        'sensor_tex':  base + '_sensors_tex',
        'cyclic_svg':  base + '_cyclic_svg',
    }
    for d in dirs.values():
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    print(f"Output dirs:\n" + "\n".join(f"  {d}" for d in dirs.values()))

    if show_event_lines:
        el_path = base + '_event_lines.svg'
        with open(el_path, 'w', encoding='utf-8') as f:
            f.write(generate_event_lines_svg(svg_data, env))
        print(f"Event lines SVG: {el_path}")

    print("Generating frames ...")
    robot = Robot(env, Point(*path_pts[0]))
    for i, (px, py) in enumerate(path_pts): #enumerate(tqdm(path_pts))
        print(f"Frame {i:04d} / {N_PATH_POINTS}  pos=({px:.4f}, {py:.4f})")
        if i > 0:
            robot.move(Edge(Point(*path_pts[i - 1]), Point(px, py)))

        gaps = robot.gaps
        try:
            shadow_polys = compute_shadow_polygons(robot.pos, gaps, polygon_graph)
        except Exception:
            shadow_polys = []

        name = f'frame_{i:04d}'

        with open(os.path.join(dirs['shadow'], name + '.svg'), 'w', encoding='utf-8') as f:
            f.write(generate_frame_svg(svg_data, px, py, shadow_polys,
                                       frame_number=i if show_frame_number else None,
                                       show_event_lines=show_event_lines, env=env))

        with open(os.path.join(dirs['sensor_svg'], name + '.svg'), 'w', encoding='utf-8') as f:
            f.write(generate_sensor_svg(gaps))

        with open(os.path.join(dirs['sensor_tex'], name + '.tex'), 'w', encoding='utf-8') as f:
            f.write(generate_sensor_tex(gaps))

        # with open(os.path.join(dirs['cyclic_svg'], name + '.svg'), 'w', encoding='utf-8') as f:
        #     f.write(generate_cyclic_svg(gaps))

    print(f"Done — {N_PATH_POINTS} frames written to each output directory.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('svg_file', nargs='?', default='environments/env_1.svg')
    parser.add_argument('--frame-number', action='store_true',
                        help='Overlay the frame index in the bottom-right corner of each SVG')
    parser.add_argument('--event-lines', action='store_true',
                        help='Write a single <env>_event_lines.svg with all critical-event edges')
    args = parser.parse_args()
    generate_frames(args.svg_file, show_frame_number=args.frame_number,
                    show_event_lines=args.event_lines)
