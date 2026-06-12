"""
Convert a single SVG curve to a Python parametric function and sample points.

Supports: M (moveto), L (lineto), C (cubic bezier), Q (quadratic bezier), Z (closepath)
Usage: python svg_curve_to_function.py curve.svg
"""

import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def parse_svg_path(d: str) -> list[tuple]:
    """Parse SVG path d attribute into a list of (command, [args]) segments."""
    tokens = re.findall(r"[MmLlCcQqZzVvHh]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    segments = []
    i = 0
    current_cmd = None
    while i < len(tokens):
        if tokens[i].isalpha():
            current_cmd = tokens[i]
            i += 1
        else:
            args_per_cmd = {"M": 2, "m": 2, "L": 2, "l": 2,
                            "C": 6, "c": 6, "Q": 4, "q": 4,
                            "V": 1, "v": 1, "H": 1, "h": 1,
                            "Z": 0, "z": 0}
            n = args_per_cmd.get(current_cmd, 0)
            if n == 0:
                segments.append((current_cmd, []))
                current_cmd = None
            else:
                args = [float(tokens[i + j]) for j in range(n)]
                segments.append((current_cmd, args))
                i += n
                continue
        if current_cmd in ("Z", "z"):
            segments.append((current_cmd, []))
            current_cmd = None
    return segments


def segments_to_beziers(segments: list[tuple]) -> list[np.ndarray]:
    """Convert parsed segments to a list of cubic Bezier control point arrays (shape 4x2)."""
    beziers = []
    current = np.array([0.0, 0.0])
    start = np.array([0.0, 0.0])

    for cmd, args in segments:
        if cmd == "M":
            current = np.array([args[0], args[1]])
            start = current.copy()
        elif cmd == "m":
            current = current + np.array([args[0], args[1]])
            start = current.copy()
        elif cmd in ("L", "l"):
            p0 = current.copy()
            p3 = current + np.array(args) if cmd == "l" else np.array(args)
            # Elevate line to cubic bezier
            p1 = p0 + (p3 - p0) / 3
            p2 = p0 + 2 * (p3 - p0) / 3
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd == "C":
            p0 = current.copy()
            p1 = np.array([args[0], args[1]])
            p2 = np.array([args[2], args[3]])
            p3 = np.array([args[4], args[5]])
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd == "c":
            p0 = current.copy()
            p1 = current + np.array([args[0], args[1]])
            p2 = current + np.array([args[2], args[3]])
            p3 = current + np.array([args[4], args[5]])
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd == "Q":
            p0 = current.copy()
            qp1 = np.array([args[0], args[1]])
            p3 = np.array([args[2], args[3]])
            # Elevate quadratic to cubic
            p1 = p0 + 2 / 3 * (qp1 - p0)
            p2 = p3 + 2 / 3 * (qp1 - p3)
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd == "q":
            p0 = current.copy()
            qp1 = current + np.array([args[0], args[1]])
            p3 = current + np.array([args[2], args[3]])
            p1 = p0 + 2 / 3 * (qp1 - p0)
            p2 = p3 + 2 / 3 * (qp1 - p3)
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd in ("V", "v", "H", "h"):
            p0 = current.copy()
            if cmd == "V":
                p3 = np.array([current[0], args[0]])
            elif cmd == "v":
                p3 = current + np.array([0.0, args[0]])
            elif cmd == "H":
                p3 = np.array([args[0], current[1]])
            else:  # h
                p3 = current + np.array([args[0], 0.0])
            p1 = p0 + (p3 - p0) / 3
            p2 = p0 + 2 * (p3 - p0) / 3
            beziers.append(np.array([p0, p1, p2, p3]))
            current = p3
        elif cmd in ("Z", "z"):
            if not np.allclose(current, start):
                p0 = current.copy()
                p3 = start.copy()
                p1 = p0 + (p3 - p0) / 3
                p2 = p0 + 2 * (p3 - p0) / 3
                beziers.append(np.array([p0, p1, p2, p3]))
            current = start.copy()

    return beziers


def eval_cubic_bezier(P: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Evaluate cubic Bezier curve at parameter t in [0,1]. Returns (N,2) array."""
    t = t[:, None]
    return ((1 - t) ** 3 * P[0]
            + 3 * (1 - t) ** 2 * t * P[1]
            + 3 * (1 - t) * t ** 2 * P[2]
            + t ** 3 * P[3])


def eval_cubic_bezier_tangent(P: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Derivative of cubic Bezier at t. Returns (N,2) unnormalized tangent vectors."""
    t = t[:, None]
    return (3 * (1 - t) ** 2 * (P[1] - P[0])
            + 6 * (1 - t) * t * (P[2] - P[1])
            + 3 * t ** 2 * (P[3] - P[2]))


def sample_curve(beziers: list[np.ndarray], n_points: int = 300) -> tuple[np.ndarray, np.ndarray]:
    """Sample n_points evenly distributed across all bezier segments."""
    n_seg = len(beziers)
    pts_per_seg = max(n_points // n_seg, 10)
    xs, ys = [], []
    for P in beziers:
        t = np.linspace(0, 1, pts_per_seg)
        pts = eval_cubic_bezier(P, t)
        xs.append(pts[:, 0])
        ys.append(pts[:, 1])
    return np.concatenate(xs), np.concatenate(ys)


def _endpoint_tangent(P: np.ndarray, at_end: bool) -> np.ndarray:
    """
    Return the tangent direction at the start (at_end=False) or end (at_end=True)
    of a cubic bezier, falling back through control points when the derivative is zero
    (e.g. when P2==P3 or P0==P1, which some SVG editors use to mark corner nodes).
    """
    if at_end:
        candidates = [P[3] - P[2], P[3] - P[1], P[3] - P[0]]
    else:
        candidates = [P[1] - P[0], P[2] - P[0], P[3] - P[0]]
    for v in candidates:
        if not np.allclose(v, 0):
            return v
    return np.array([1.0, 0.0])  # fully degenerate segment, arbitrary fallback


def _build_angle_lookup(beziers: list[np.ndarray],
                        n_fine: int = 2000,
                        corner_steps: int = 20,
                        corner_threshold: float = np.deg2rad(2),
                        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a dense (position, tangent, cumulative_bend) lookup table.

    At each bezier junction where the tangent jumps by more than corner_threshold,
    a directional sweep is inserted: all entries share the corner position but
    their direction rotates linearly from the arriving to the departing tangent.
    This lets by_angle spacing place arrows *at the corner* while the direction
    rotates, rather than skipping over the jump.

    Returns
    -------
    pts_all  : (N, 2) positions
    tans_all : (N, 2) unnormalized tangents
    cumulative_bend : (N,) monotonically increasing total bending in radians
    """
    n = len(beziers)
    pts_per_seg = max(n_fine // n, 10)

    all_pts, all_tans = [], []

    for k, P in enumerate(beziers):
        # Sample segment open at t=1 to avoid double-counting the shared endpoint
        t = np.linspace(0, 1, pts_per_seg, endpoint=False)
        all_pts.append(eval_cubic_bezier(P, t))
        all_tans.append(eval_cubic_bezier_tangent(P, t))

        # At the junction to the next segment, check for a corner
        if k < n - 1:
            corner_pt = eval_cubic_bezier(P, np.array([1.0]))[0]
            leaving_tan = _endpoint_tangent(P, at_end=True)
            arriving_tan = _endpoint_tangent(beziers[k + 1], at_end=False)

            a0 = np.arctan2(leaving_tan[1], leaving_tan[0])
            a1 = np.arctan2(arriving_tan[1], arriving_tan[0])
            # Shortest signed angular difference in (-π, π]
            diff = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi

            if abs(diff) > corner_threshold:
                # Insert a sweep: same position, direction rotates a0 → a1
                sweep_angles = np.linspace(a0, a0 + diff, corner_steps + 2)[1:-1]
                sweep_tans = np.column_stack([np.cos(sweep_angles), np.sin(sweep_angles)])
                all_pts.append(np.tile(corner_pt, (corner_steps, 1)))
                all_tans.append(sweep_tans)

    # Include the very last endpoint
    last_P = beziers[-1]
    all_pts.append(eval_cubic_bezier(last_P, np.array([1.0])))
    all_tans.append(_endpoint_tangent(last_P, at_end=True)[np.newaxis, :])

    pts_all = np.vstack(all_pts)
    tans_all = np.vstack(all_tans)

    raw_angles = np.arctan2(tans_all[:, 1], tans_all[:, 0])
    angle_diffs = np.diff(np.unwrap(raw_angles))
    cumulative_bend = np.concatenate([[0.0], np.cumsum(np.abs(angle_diffs))])

    # Blend with arc length so that straight segments (zero bending) still
    # receive samples proportional to their physical length.  Corner sweeps
    # (fixed position, non-zero bending) are carried by the bend component;
    # straight bezier sides are carried by the arc component.
    seg_lengths = np.sqrt(np.sum(np.diff(pts_all, axis=0) ** 2, axis=1))
    cumulative_arc = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    total_bend = cumulative_bend[-1]
    total_arc = cumulative_arc[-1]
    if total_bend > 0 and total_arc > 0:
        cumulative_bend = (cumulative_bend / total_bend
                           + cumulative_arc / total_arc)

    return pts_all, tans_all, cumulative_bend


def sample_tangents(beziers: list[np.ndarray], n_arrows: int = 20,
                    flip_y: bool = True, svg_height: float | None = None,
                    by_angle: bool = False, n_fine: int = 2000,
                    corner_steps: int = 20,
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample unit tangent vectors at n_arrows positions.

    Parameters
    ----------
    by_angle     : space arrows by equal cumulative bending angle; otherwise by parameter t.
    n_fine       : dense sample count for the angle lookup (by_angle only).
    corner_steps : number of interpolated arrow directions inserted at each corner
                   so that arrows can rotate smoothly through the junction (by_angle only).

    Returns
    -------
    x, y   : arrow base positions
    dx, dy : unit tangent direction (y already flipped if flip_y=True)
    """
    n = len(beziers)

    if by_angle:
        pts_all, tans_all, cumulative_bend = _build_angle_lookup(
            beziers, n_fine=n_fine, corner_steps=corner_steps,
        )

        targets = np.linspace(cumulative_bend[0], cumulative_bend[-1], n_arrows + 2)[1:-1]
        idx = np.searchsorted(cumulative_bend, targets).clip(0, len(pts_all) - 1)

        px, py = pts_all[idx, 0], pts_all[idx, 1]
        tx, ty = tans_all[idx, 0], tans_all[idx, 1]

        if flip_y:
            py = (svg_height - py) if svg_height is not None else -py
            ty = -ty

        norm = np.hypot(tx, ty)
        norm[norm == 0] = 1.0
        return px, py, tx / norm, ty / norm

    # Original parameter-space spacing
    t_global = np.linspace(0, 1, n_arrows, endpoint=False) + 0.5 / n_arrows
    xs, ys, dxs, dys = [], [], [], []

    for k, P in enumerate(beziers):
        t0, t1 = k / n, (k + 1) / n
        mask = (t_global >= t0) & (t_global < t1)
        if not mask.any():
            continue
        local_t = (t_global[mask] - t0) / (t1 - t0)
        pts = eval_cubic_bezier(P, local_t)
        tans = eval_cubic_bezier_tangent(P, local_t)

        px, py = pts[:, 0], pts[:, 1]
        tx, ty = tans[:, 0], tans[:, 1]

        if flip_y:
            py = (svg_height - py) if svg_height is not None else -py
            ty = -ty

        norm = np.hypot(tx, ty)
        norm[norm == 0] = 1.0
        xs.append(px);  ys.append(py)
        dxs.append(tx / norm);  dys.append(ty / norm)

    return (np.concatenate(xs), np.concatenate(ys),
            np.concatenate(dxs), np.concatenate(dys))


def _path_element_start(content: str, path_id: str | None = None) -> int:
    """Return the character index of the opening '<' of the target <path> element."""
    if path_id:
        for attr in (f'id="{path_id}"', f'inkscape:label="{path_id}"'):
            pos = content.find(attr)
            if pos >= 0:
                start = content.rfind('<path', 0, pos)
                if start >= 0:
                    return start
        raise ValueError(f"No <path> with id or inkscape:label equal to '{path_id}' found.")
    # Skip paths inside <defs>
    defs_end = content.find('</defs>')
    search_from = defs_end + len('</defs>') if defs_end >= 0 else 0
    start = content.find('<path', search_from)
    if start < 0:
        raise ValueError("No <path d='...'> found outside <defs> in the SVG file.")
    return start


def _path_element_d(content: str, path_start: int) -> str:
    """Extract the d attribute from a <path> element starting at path_start."""
    end = content.find('>', path_start)
    elem = content[path_start:end + 1]
    match = re.search(r'\sd="([^"]+)"', elem, re.DOTALL)
    if not match:
        raise ValueError("Located <path> element has no d attribute.")
    return match.group(1)


def extract_path_d(svg_path: str, path_id: str | None = None) -> str:
    """Extract the d attribute from a <path> element in an SVG file."""
    content = Path(svg_path).read_text(encoding="utf-8")
    start = _path_element_start(content, path_id)
    return _path_element_d(content, start)


def get_svg_height(svg_path: str) -> float | None:
    """Extract SVG canvas height to flip y-axis (SVG y increases downward)."""
    content = Path(svg_path).read_text(encoding="utf-8")
    match = re.search(r'<svg[^>]+height="([0-9.]+)"', content)
    if match:
        return float(match.group(1))
    match = re.search(r'viewBox="[0-9.]+ [0-9.]+ [0-9.]+ ([0-9.]+)"', content)
    if match:
        return float(match.group(1))
    return None


def svg_to_curve(svg_path: str, n_points: int = 300, flip_y: bool = True,
                 path_id: str | None = None):
    """
    Parse SVG, return sampled (x, y) arrays and Bezier control points.

    Returns
    -------
    x, y    : numpy arrays of shape (n_points,)
    beziers : list of cubic Bezier control point arrays (4x2)
    """
    d = extract_path_d(svg_path, path_id=path_id)
    segments = parse_svg_path(d)
    beziers = segments_to_beziers(segments)
    x, y = sample_curve(beziers, n_points)

    if flip_y:
        h = get_svg_height(svg_path)
        if h is not None:
            y = h - y
        else:
            y = -y

    return x, y, beziers


def make_parametric_function(beziers: list[np.ndarray], flip_y: bool = True,
                              svg_height: float | None = None):
    """Return a Python function f(t) -> (x, y) for t in [0, 1] spanning the full curve."""
    n = len(beziers)
    segs = [P.copy() for P in beziers]
    h = svg_height

    def curve(t):
        t = np.atleast_1d(np.asarray(t, dtype=float))
        x_out = np.empty_like(t)
        y_out = np.empty_like(t)
        for k, P in enumerate(segs):
            t0, t1 = k / n, (k + 1) / n
            mask = (t >= t0) & (t <= t1)
            if not mask.any():
                continue
            local_t = (t[mask] - t0) / (t1 - t0)
            pts = eval_cubic_bezier(P, local_t)
            x_out[mask] = pts[:, 0]
            y_out[mask] = pts[:, 1]
            if flip_y:
                y_out[mask] = (h - pts[:, 1]) if h is not None else -pts[:, 1]
        return x_out, y_out

    return curve
