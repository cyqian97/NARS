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

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

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
from utils.svg_curve_to_function import get_svg_height, sample_tangents, svg_to_curve
from utils.vgm_lift import (
    FLOOR_Z, configure_theta_axis, draw_lift,
    map_gaps_to_smooth_curve, split_at_jumps, to_angle,
)

N_PATH_POINTS = 500
VIEW_AZIM = -61.6
VIEW_ELEV = 31.4


def generate_frames(svg_path, show_frame_number=False, show_event_lines=False,
                    generate_vgm=False, n_arrows=2000, n_fine=5000, dist_tol=3.0):
    """Parse *svg_path* once, then write all frame types per path point."""
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

    # --- VGM lift setup (optional) ---
    vgm_lift_data = None
    if generate_vgm:
        try:
            svg_h = get_svg_height(svg_path)
            _, _, beziers = svg_to_curve(svg_path, flip_y=True, path_id='curve')
            sx, sy, sdx, sdy = sample_tangents(
                beziers, n_arrows=n_arrows, flip_y=True, svg_height=svg_h,
                by_angle=True, n_fine=n_fine,
            )
            theta_fwd = to_angle(sdx, sdy)
            theta_opp = (theta_fwd + np.pi) % (2 * np.pi)
            sx_c = np.append(sx, sx[0])
            sy_c = np.append(sy, sy[0])
            segs_fwd, marks_fwd, _ = split_at_jumps(sx_c, sy_c, np.append(theta_fwd, theta_fwd[0]))
            segs_opp, marks_opp, _ = split_at_jumps(sx_c, sy_c, np.append(theta_opp, theta_opp[0]))
            vgm_lift_data = {
                'sx': sx, 'sy': sy, 'sx_c': sx_c, 'sy_c': sy_c, 'svg_h': svg_h,
                'theta_fwd': theta_fwd, 'theta_opp': theta_opp,
                'segs_fwd': segs_fwd, 'marks_fwd': marks_fwd,
                'segs_opp': segs_opp, 'marks_opp': marks_opp,
            }
            dirs['vgm_lift'] = base + '_vgm_lift_frames'
            print("VGM lift data ready.")
        except Exception as e:
            print(f"VGM lift setup failed: {e}")

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

        if vgm_lift_data is not None:
            vd = vgm_lift_data
            matches = map_gaps_to_smooth_curve(
                gaps, vd['sx'], vd['sy'], vd['theta_fwd'], vd['theta_opp'],
                vd['svg_h'], dist_tol,
            )
            fig = plt.figure(figsize=(9, 7))
            ax = fig.add_subplot(111, projection='3d')
            ax.computed_zorder = False
            draw_lift(ax, vd['segs_fwd'], vd['marks_fwd'], [], color='red',   lw=1.5, zorder=4)
            draw_lift(ax, vd['segs_opp'], vd['marks_opp'], [], color='green', lw=1.5, zorder=4)
            ax.plot(vd['sx_c'], vd['sy_c'], zs=FLOOR_Z, zdir='z', color='steelblue', lw=1.5, zorder=2)
            if matches:
                mx_list, my_list, mt_list = zip(*matches)
                ax.scatter(mx_list, my_list, mt_list, c='orange', s=80, zorder=6, depthshade=False)
            configure_theta_axis(ax)
            ax.set_box_aspect((1, 1, 0.3))
            ax.xaxis.set_pane_color((1, 1, 1, 0))
            ax.yaxis.set_pane_color((1, 1, 1, 0))
            ax.zaxis.set_pane_color((1, 1, 1, 0))
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.view_init(elev=VIEW_ELEV, azim=VIEW_AZIM)
            plt.savefig(os.path.join(dirs['vgm_lift'], name + '.png'), dpi=120, bbox_inches='tight')
            plt.close(fig)

    print(f"Done — {N_PATH_POINTS} frames written to each output directory.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('svg_file', nargs='?', default='environments/env_1_smooth.svg')
    parser.add_argument('--frame-number', action='store_true',
                        help='Overlay the frame index in the bottom-right corner of each SVG')
    parser.add_argument('--event-lines', action='store_true',
                        help='Write a single <env>_event_lines.svg with all critical-event edges')
    parser.add_argument('--vgm-lift', action='store_true',
                        help='Also generate VGM lift frames (requires a "curve" path in the SVG)')
    parser.add_argument('--n-arrows', type=int, default=2000,
                        help='Tangent samples on smooth curve for VGM lift (default 2000)')
    parser.add_argument('--n-fine', type=int, default=8000,
                        help='Dense sample count for angle-spacing lookup (default 8000)')
    parser.add_argument('--dist-tol', type=float, default=3.0,
                        help='Max distance from gap vertex to smooth curve for a match (default 3.0)')
    args = parser.parse_args()
    generate_frames(args.svg_file, show_frame_number=args.frame_number,
                    show_event_lines=args.event_lines, generate_vgm=args.vgm_lift,
                    n_arrows=args.n_arrows, n_fine=args.n_fine, dist_tol=args.dist_tol)
