"""Generate the VGM lift plot for a smooth SVG environment.

Usage:
    python generate_vgm_lift.py [environments/env_1_smooth.svg]
            [--n-arrows N] [--n-fine N] [--n-steps N]
            [--angle-tol F] [--out FILE]

Plots:
  - 3D VGM lift of the smooth boundary curve (forward tangent = red,
    backward tangent = green)
  - Floor projection of the smooth curve
  - Scatter markers showing where robot-detected polygon gaps map onto
    the lift, coloured by step index along the robot path
"""

import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection

from backend.environment import Environment
from backend.robot import Robot
from pyvisgraph.classes import Edge, Point
from utils.svg_curve_to_function import get_svg_height, sample_tangents, svg_to_curve
from utils.svg_utils import interpolate_path, parse_svg_env_file
from utils.vgm_lift import (
    FLOOR_Z,
    configure_theta_axis,
    draw_lift,
    map_gaps_to_smooth_curve,
    split_at_jumps,
    to_angle,
)

# Default view angles (paste new values printed on mouse-release to update)
VIEW_AZIM = -61.6
VIEW_ELEV = 31.4


def run(svg_path, n_arrows=2000, n_fine=5000, n_steps=200,
        angle_tol=0.15, out=None):

    svg_h = get_svg_height(svg_path)

    # --- smooth curve VGM lift ---
    _, _, beziers = svg_to_curve(svg_path, flip_y=True, path_id='curve')
    sx, sy, sdx, sdy = sample_tangents(
        beziers, n_arrows=n_arrows, flip_y=True, svg_height=svg_h,
        by_angle=True, n_fine=n_fine,
    )
    theta_fwd = to_angle(sdx, sdy)
    theta_opp = (theta_fwd + np.pi) % (2 * np.pi)

    # --- build polygon environment and run robot along the SVG path ---
    svg_data = parse_svg_env_file(svg_path)
    wall = [Point(x, y) for x, y in svg_data['env_polygon_points']]
    env = Environment()
    env.build([wall], status=False)

    path_pts = interpolate_path(svg_data['path_points'], n_steps)
    robot = Robot(env, Point(*path_pts[0]))

    # Collect gap matches at every step along the path
    step_list, x_list, y_list, t_list = [], [], [], []

    def record(step):
        matches = map_gaps_to_smooth_curve(
            robot.gaps, sx, sy, theta_fwd, theta_opp, svg_h, angle_tol,
        )
        for mx, my, mt in matches:
            step_list.append(step)
            x_list.append(mx)
            y_list.append(my)
            t_list.append(mt)

    record(0)
    for i in range(1, len(path_pts)):
        robot.move(Edge(Point(*path_pts[i - 1]), Point(*path_pts[i])))
        record(i)

    # --- build plot ---
    fig = plt.figure(figsize=(9, 7), num='VGM Lift')
    ax = fig.add_subplot(111, projection='3d')
    ax.computed_zorder = False  # use explicit zorder instead of depth sort

    # Close the smooth curve so there is no gap between the last and first sample
    sx_c = np.append(sx, sx[0])
    sy_c = np.append(sy, sy[0])
    segs_fwd, marks_fwd, _ = split_at_jumps(sx_c, sy_c, np.append(theta_fwd, theta_fwd[0]))
    segs_opp, marks_opp, _ = split_at_jumps(sx_c, sy_c, np.append(theta_opp, theta_opp[0]))
    draw_lift(ax, segs_fwd, marks_fwd, [], color='red',   lw=1.5, zorder=4)
    draw_lift(ax, segs_opp, marks_opp, [], color='green', lw=1.5, zorder=4)

    # Floor projection of the smooth curve (closed)
    ax.plot(sx_c, sy_c, zs=FLOOR_Z, zdir='z', color='steelblue', lw=1.5, zorder=2)

    # Gap markers coloured by step index
    if step_list:
        sc = ax.scatter(
            x_list, y_list, t_list,
            c=step_list, cmap='viridis', s=20, zorder=6, depthshade=False,
        )
        fig.colorbar(sc, ax=ax, label='path step', shrink=0.5)

    configure_theta_axis(ax)
    ax.set_box_aspect((1, 1, 0.3))
    ax.xaxis.set_pane_color((1, 1, 1, 0))
    ax.yaxis.set_pane_color((1, 1, 1, 0))
    ax.zaxis.set_pane_color((1, 1, 1, 0))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.view_init(elev=VIEW_ELEV, azim=VIEW_AZIM)

    # Print view angles when the user rotates the plot interactively
    fig.canvas.mpl_connect(
        'button_release_event',
        lambda e: print(f'azim={ax.azim:.1f}  elev={ax.elev:.1f}'),
    )

    plt.tight_layout()
    out_file = out or str(Path(svg_path).with_suffix('')) + '_vgm_lift.svg'
    plt.savefig(out_file, format='svg', bbox_inches='tight')
    print(f'Saved to {out_file}')
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VGM lift plot with gap mapping.')
    parser.add_argument('svg_file', nargs='?', default='environments/env_1_smooth.svg')
    parser.add_argument('--n-arrows',  type=int,   default=2000,
                        help='tangent samples on smooth curve (default 2000)')
    parser.add_argument('--n-fine',    type=int,   default=5000,
                        help='dense sample count for angle-spacing lookup (default 5000)')
    parser.add_argument('--n-steps',   type=int,   default=200,
                        help='robot steps along the SVG path (default 200)')
    parser.add_argument('--angle-tol', type=float, default=0.15,
                        help='max circular angle diff for a candidate match (default 0.15 rad)')
    parser.add_argument('--out', default=None, help='output SVG filename')
    args = parser.parse_args()
    run(args.svg_file, args.n_arrows, args.n_fine, args.n_steps,
        args.angle_tol, args.out)
