"""VGM lift plotting utilities.

Core functions adapted from plot_vgm_lift.py (external figures/vgm directory).
Added: map_gaps_to_smooth_curve — projects robot-detected polygon gaps onto the
smooth-curve VGM lift using angle-then-position matching.
"""

import numpy as np

PI2 = 2 * np.pi
JUMP_THRESHOLD = np.pi  # |Δθ| above this signals a wrap-around, not a real bend
FLOOR_Z = -np.pi        # z-level of the 2-D floor projection


def to_angle(dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Unit tangent vectors → angles in [0, 2π)."""
    return np.arctan2(dy, dx) % PI2


def _circ_diff(a: np.ndarray, b: float) -> np.ndarray:
    """Minimum circular distance between array a and scalar b (both in [0, 2π))."""
    d = np.abs(a - b)
    return np.minimum(d, PI2 - d)


def split_at_jumps(x, y, theta):
    """
    Partition (x, y, theta) into continuous segments, splitting where
    |Δθ| > π (a wrap-around through the 0/2π seam).

    Returns
    -------
    segments  : list of (xs, ys, ts) arrays
    markers   : list of (xm, ym, tm, kind) where kind ∈ {'up', 'down'}
    gap_fills : list of ([x0,xb,xb,x1], [y0,yb,yb,y1], [t0,tA,tB,t1])
                connecting each wrap-around through the seam
    """
    dtheta = np.diff(theta)
    jump_idx = np.where(np.abs(dtheta) > JUMP_THRESHOLD)[0]

    segments, markers, gap_fills = [], [], []
    prev = 0
    for i in jump_idx:
        segments.append((x[prev:i + 1], y[prev:i + 1], theta[prev:i + 1]))
        x0, y0, t0 = x[i], y[i], theta[i]
        x1, y1, t1 = x[i + 1], y[i + 1], theta[i + 1]
        if dtheta[i] < 0:
            # θ fell from near 2π to near 0
            markers.append((x0, y0, t0, 'down'))
            markers.append((x1, y1, t1, 'up'))
            span = (PI2 - t0) + t1
            alpha = (PI2 - t0) / span if span > 0 else 0.5
            xb = x0 + alpha * (x1 - x0)
            yb = y0 + alpha * (y1 - y0)
            gap_fills.append(([x0, xb, xb, x1], [y0, yb, yb, y1], [t0, PI2, 0, t1]))
        else:
            # θ rose from near 0 to near 2π
            markers.append((x0, y0, t0, 'up'))
            markers.append((x1, y1, t1, 'down'))
            span = t0 + (PI2 - t1)
            alpha = t0 / span if span > 0 else 0.5
            xb = x0 + alpha * (x1 - x0)
            yb = y0 + alpha * (y1 - y0)
            gap_fills.append(([x0, xb, xb, x1], [y0, yb, yb, y1], [t0, 0, PI2, t1]))
        prev = i + 1
    segments.append((x[prev:], y[prev:], theta[prev:]))
    return segments, markers, gap_fills


def draw_lift(ax, segments, markers, gap_fills, color,
              label=None, ls='-', lw=1.4, zorder=3):
    """Draw one 3D lift curve with wrap-around markers."""
    for k, (xs, ys, ts) in enumerate(segments):
        ax.plot(xs, ys, ts, color=color, lw=lw, ls=ls,
                label=label if k == 0 else None, zorder=zorder)
    for xm, ym, tm, kind in markers:
        ax.scatter(xm, ym, tm,
                   marker=('v' if kind == 'up' else '^'),
                   color=color, s=30, zorder=6, depthshade=False)


def configure_theta_axis(ax):
    """Set z-axis appearance for θ ∈ [−π, 2π]."""
    ax.set_zlim(FLOOR_Z, PI2)
    ax.set_zticks([0, np.pi / 2, np.pi, 3 * np.pi / 2, PI2])
    ax.set_zticklabels(['0', 'π/2', 'π', '3π/2', '2π'])
    ax.set_zlabel('θ')
    ax.set_xlabel('')
    ax.set_ylabel('')


def map_gaps_to_smooth_curve(gaps, smooth_x, smooth_y, theta_fwd, theta_opp,
                              svg_height, dist_tol=3.0):
    """
    Find the best-matching point on the smooth-curve VGM lift for each gap.

    A gap is a bitangent point: the line-of-sight from the robot to the gap vertex
    is tangent to the smooth boundary, so gap.dir approximates the boundary tangent
    direction at that vertex.  We flip the y-component of gap.dir to convert from
    SVG y-down coordinates to the plot's y-up system.

    Algorithm per gap
    -----------------
    1. θ_gap  = atan2(-dir[1], dir[0]) % 2π   (y-flipped direction)
    2. Sort all smooth samples by min(circ_diff(θ_fwd, θ_gap), circ_diff(θ_opp, θ_gap))
    3. Walk samples in that order; accept the first whose position is within dist_tol
       of the gap vertex (vertex y also flipped to match plot coordinates)

    Parameters
    ----------
    gaps            : list of Gap objects (gap.vertex Point, gap.dir numpy array)
    smooth_x/y      : sampled smooth-curve positions in plot y-up coordinates, shape (N,)
    theta_fwd/opp   : forward / backward tangent angles of smooth samples, shape (N,)
    svg_height      : SVG canvas height used to flip y coordinates
    dist_tol        : maximum Euclidean distance for a candidate to be accepted

    Returns
    -------
    list of (x, y, theta) triples, one per successfully matched gap
    """
    results = []
    for gap in gaps:
        # gap.dir is in SVG y-down coords; flip y to match the plot's y-up system
        dx = float(gap.dir[0])
        dy = -float(gap.dir[1])
        theta_gap = np.arctan2(dy, dx) % PI2

        # Gap vertex in plot y-up coordinates
        gx = float(gap.vertex.x)
        gy = svg_height - float(gap.vertex.y)

        diff_fwd = _circ_diff(theta_fwd, theta_gap)
        diff_opp = _circ_diff(theta_opp, theta_gap)

        # Walk samples in order of increasing angular distance; accept first
        # whose position is within dist_tol of the gap vertex
        for idx in np.argsort(np.minimum(diff_fwd, diff_opp)):
            if np.hypot(smooth_x[idx] - gx, smooth_y[idx] - gy) < dist_tol:
                theta_match = (theta_fwd[idx] if diff_fwd[idx] <= diff_opp[idx]
                               else theta_opp[idx])
                results.append((smooth_x[idx], smooth_y[idx], float(theta_match)))
                break

    return results
