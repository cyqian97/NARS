"""Generate cylinder animation frames showing gap direction history.

Usage:
    python generate_cylinder_frames.py [env.svg] [--n-frames N] [--stride S]
                                       [--final-only] [--window-size WxH]

Outputs PNG frames to <env>_cylinder_frames/ directory.
Each frame shows the S^1 x [0,T] cylinder with gap direction trajectories
accumulated up to that point in time.
"""

import argparse
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pyvista as pv
from tqdm import tqdm

from backend.environment import Environment
from backend.gap import GapEventType
from backend.robot import Robot
from pyvisgraph import CCW, CW
from pyvisgraph.classes import Edge, Point
from utils.svg_utils import interpolate_path, parse_svg_env_file

N_PATH_POINTS = 500

CYLINDER_RADIUS = 1.0
CURVE_RADIUS = 1.01   # slightly outside cylinder surface for visibility
TOTAL_HEIGHT = 3.0

ANGLE_OFFSET = 4.7    # global angular offset to rotate the S^1 view
SHOW_SEAM_LINE = False   # toggle the black vertical seam line at theta=0
SHOW_CAPS = False         # toggle top and bottom end caps of the cylinder
CYLINDER_OPACITY_PAST   = 0.5  # opacity of the cylinder portion already traversed
CYLINDER_OPACITY_FUTURE = 0.2  # opacity of the cylinder portion not yet traversed
CURVE_LINE_WIDTH = 40   # tube width of the gap trajectory curves

CURVE_COLORS = [
    "#0173B2",  # blue
    "#DE8F05",  # orange
    "#029E73",  # green
    "#CC78BC",  # purple
    "#CA9161",  # tan
    "#FBAFE4",  # pink
    "#949494",  # gray
    "#ECE133",  # yellow
    "#56B4E9",  # sky blue
    "#D55E00",  # vermillion
]

CAMERA_POSITION = [
    (3.84, -5.61, -0.7),
    (0.0, 0.0, 1.5),
    (-0.78, -0.61, 0.15),
]

WINDOW_SIZE = (3840, 2160)


# ---------------------------------------------------------------------------
# Gap tracking
# ---------------------------------------------------------------------------

class TrackedRobot(Robot):
    """Robot subclass that assigns stable IDs to gaps and records history.

    Overrides _apply_event to intercept vertex-changing events (N/P) and
    appearance/disappearance events (A/D/S/M) so that each gap retains a
    stable integer ID across the full trajectory.
    """

    def __init__(self, env, pos):
        self._next_id = 0
        self._vertex_to_id = {}
        super().__init__(env, pos)
        for gap in self.gaps:
            self._alloc_id(gap.vertex)

    def _alloc_id(self, vertex):
        gid = self._next_id
        self._next_id += 1
        self._vertex_to_id[vertex] = gid
        return gid

    def _apply_event(self, event):
        etype = event.etype
        edge = event.edge
        graph = self.env.polygon_graph

        # --- update vertex-to-id mapping BEFORE parent mutates gap list ---
        if etype == GapEventType.N:
            if edge.side == CCW:
                old_v, new_v = edge.p1, graph.get_next_point(edge.p1)
            else:
                old_v, new_v = graph.get_prev_point(edge.p1), edge.p1
            gid = self._vertex_to_id.pop(old_v, None)
            if gid is not None:
                self._vertex_to_id[new_v] = gid

        elif etype == GapEventType.P:
            if edge.side == CW:
                old_v, new_v = edge.p1, graph.get_prev_point(edge.p1)
            else:
                old_v, new_v = graph.get_next_point(edge.p1), edge.p1
            gid = self._vertex_to_id.pop(old_v, None)
            if gid is not None:
                self._vertex_to_id[new_v] = gid

        elif etype == GapEventType.D:
            self._vertex_to_id.pop(edge.p1, None)

        elif etype == GapEventType.M:
            self._vertex_to_id.pop(edge.dual.p1, None)

        result = super()._apply_event(event)

        # --- register newly created gaps AFTER parent appends them ---
        if etype == GapEventType.A:
            if edge.p1 not in self._vertex_to_id:
                self._alloc_id(edge.p1)

        elif etype == GapEventType.S:
            if edge.dual.p1 not in self._vertex_to_id:
                self._alloc_id(edge.dual.p1)

        return result

    def current_gap_angles(self):
        """Return dict {gap_id: angle_rad} for all currently visible gaps."""
        result = {}
        for gap in self.gaps:
            gid = self._vertex_to_id.get(gap.vertex)
            if gid is not None:
                angle = np.arctan2(float(gap.dir[1]), float(gap.dir[0]))
                result[gid] = angle
        return result


def run_simulation(svg_path):
    """Parse SVG, build environment, run TrackedRobot; return gap histories.

    Returns
    -------
    histories : dict {gap_id: [(step, angle_rad), ...]}
        Sorted by step for each gap_id.
    n_steps : int
        Total number of steps taken.
    """
    print(f"Parsing {svg_path} ...")
    svg_data = parse_svg_env_file(svg_path)

    print("Building environment ...")
    wall = [Point(x, y) for x, y in svg_data["env_polygon_points"]]
    env = Environment()
    env.build([wall], status=True)

    print(f"Interpolating {N_PATH_POINTS} path points ...")
    path_pts = interpolate_path(svg_data["path_points"], N_PATH_POINTS)

    print("Simulating robot ...")
    robot = TrackedRobot(env, Point(*path_pts[0]))
    histories = {}

    def record(step):
        for gid, angle in robot.current_gap_angles().items():
            histories.setdefault(gid, []).append((step, angle))

    record(0)
    for i in tqdm(range(1, len(path_pts))):
        robot.move(Edge(Point(*path_pts[i - 1]), Point(*path_pts[i])))
        record(i)

    return histories, len(path_pts) - 1


# ---------------------------------------------------------------------------
# Cylinder frame rendering
# ---------------------------------------------------------------------------

def _add_cylinder_shell(plotter, max_step, total_steps):
    split_z = max_step / total_steps * TOTAL_HEIGHT

    if split_z > 0:
        past = pv.Cylinder(
            center=(0, 0, split_z / 2),
            direction=(0, 0, 1),
            radius=CYLINDER_RADIUS,
            height=split_z,
            resolution=200,
            capping=SHOW_CAPS,
        )
        plotter.add_mesh(past, opacity=CYLINDER_OPACITY_PAST, color="gray",
                         smooth_shading=True, show_edges=False, lighting=True)

    if split_z < TOTAL_HEIGHT:
        future_height = TOTAL_HEIGHT - split_z
        future = pv.Cylinder(
            center=(0, 0, split_z + future_height / 2),
            direction=(0, 0, 1),
            radius=CYLINDER_RADIUS,
            height=future_height,
            resolution=200,
            capping=SHOW_CAPS,
        )
        plotter.add_mesh(future, opacity=CYLINDER_OPACITY_FUTURE, color="gray",
                         smooth_shading=True, show_edges=False, lighting=True)


def _add_grid_lines(plotter):
    n_vert = 12
    for theta in np.linspace(0, 2 * np.pi, n_vert, endpoint=False):
        is_seam = np.isclose(theta, 0.0)
        if is_seam and not SHOW_SEAM_LINE:
            continue
        zv = np.linspace(0, TOTAL_HEIGHT, 50)
        pts = np.column_stack((np.cos(theta) * np.ones(50),
                               np.sin(theta) * np.ones(50), zv))
        line = pv.Spline(pts, 50)
        color = "black" if is_seam else "white"
        width = 10 if is_seam else 6
        plotter.add_mesh(line, color=color, line_width=width,
                         smooth_shading=True, lighting=True)

    n_horiz = 8
    for z_val in np.linspace(0, TOTAL_HEIGHT, n_horiz):
        theta_c = np.linspace(0, 2 * np.pi, 100)
        pts = np.column_stack((np.cos(theta_c), np.sin(theta_c),
                                z_val * np.ones(100)))
        circle = pv.Spline(pts, 100)
        color = "black" if np.isclose(z_val, 0.0) else "white"
        width = 10 if np.isclose(z_val, 0.0) else 5
        plotter.add_mesh(circle, color=color, line_width=width,
                         smooth_shading=True, lighting=True)


def _add_gap_curves(plotter, histories, max_step, total_steps):
    for gap_id, raw_history in sorted(histories.items()):
        pts_this_frame = [(s, a) for s, a in raw_history if s <= max_step]
        if len(pts_this_frame) < 2:
            continue

        curve_pts = []
        for step, angle in pts_this_frame:
            theta = angle + ANGLE_OFFSET
            z = step / total_steps * TOTAL_HEIGHT
            x = np.cos(theta) * CURVE_RADIUS
            y = np.sin(theta) * CURVE_RADIUS
            curve_pts.append((x, y, z))

        points = np.array(curve_pts)
        color = CURVE_COLORS[gap_id % len(CURVE_COLORS)]
        spline = pv.Spline(points, len(curve_pts))
        plotter.add_mesh(
            spline,
            color=color,
            line_width=CURVE_LINE_WIDTH,
            render_lines_as_tubes=True,
            smooth_shading=True,
            lighting=True,
        )


def _render_frame_task(args):
    histories, step, total_steps, out_path, window_size = args
    render_frame(histories, step, total_steps, out_path, window_size)


def render_frame(histories, max_step, total_steps, output_path,
                 window_size=WINDOW_SIZE):
    """Render one PNG frame of the cylinder up to max_step."""
    plotter = pv.Plotter(off_screen=True)

    _add_cylinder_shell(plotter, max_step, total_steps)
    _add_grid_lines(plotter)
    _add_gap_curves(plotter, histories, max_step, total_steps)

    plotter.camera_position = CAMERA_POSITION
    plotter.set_background("white")
    plotter.enable_anti_aliasing("ssaa")
    plotter.screenshot(output_path, transparent_background=False,
                       window_size=list(window_size))
    plotter.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_cylinder_frames(svg_path, stride=10, final_only=False,
                              window_size=WINDOW_SIZE, workers=None):
    histories, total_steps = run_simulation(svg_path)

    base = os.path.splitext(os.path.abspath(svg_path))[0]
    out_dir = base + "_cylinder_frames"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    print(f"Output directory: {out_dir}")

    if final_only:
        out_path = os.path.join(out_dir, "frame_final.png")
        print("Rendering final frame ...")
        render_frame(histories, total_steps, total_steps, out_path, window_size)
        print(f"Saved: {out_path}")
        return

    frame_steps = list(range(0, total_steps + 1, stride))
    if frame_steps[-1] != total_steps:
        frame_steps.append(total_steps)

    tasks = [
        (histories, step, total_steps,
         os.path.join(out_dir, f"frame_{i:04d}.png"), window_size)
        for i, step in enumerate(frame_steps)
    ]

    n_workers = workers or os.cpu_count()
    print(f"Rendering {len(frame_steps)} frames (stride={stride}, workers={n_workers}) ...")
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        list(tqdm(executor.map(_render_frame_task, tasks), total=len(tasks)))
    elapsed = time.perf_counter() - t0

    print(f"Done — {len(frame_steps)} frames written to {out_dir} in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate cylinder frames of gap direction history."
    )
    parser.add_argument("svg_file", nargs="?", default="environments/env_0.svg")
    parser.add_argument("--stride", type=int, default=20,
                        help="Render one frame every STRIDE steps (default 20)")
    parser.add_argument("--final-only", action="store_true",
                        help="Render only the final frame showing complete history")
    parser.add_argument("--window-size", default="3840x2160",
                        help="Output resolution as WxH (default 3840x2160)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel render workers (default: all CPUs)")
    args = parser.parse_args()

    w, h = (int(v) for v in args.window_size.split("x"))
    generate_cylinder_frames(
        args.svg_file,
        stride=args.stride,
        final_only=args.final_only,
        window_size=(w, h),
        workers=args.workers,
    )
