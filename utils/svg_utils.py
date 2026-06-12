"""SVG utilities: parse environment SVG files and generate per-frame SVGs."""

import re
from collections import defaultdict
import math
from math import sqrt
import xml.etree.ElementTree as ET

import pyvisgraph as vg
from pyvisgraph.visible_vertices import intersect_point, edge_distance, on_segment

SVG_NS = 'http://www.w3.org/2000/svg'
INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'

ET.register_namespace('', SVG_NS)


# ---------------------------------------------------------------------------
# SVG path parsing
# ---------------------------------------------------------------------------

def parse_transform(transform_str):
    """Parse a translate(...) SVG transform string, return (dx, dy)."""
    if not transform_str:
        return 0.0, 0.0
    m = re.match(r'translate\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)', transform_str)
    if m:
        return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0


def _tokenize_path(d):
    token_re = re.compile(
        r'([MmLlHhVvZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
    )
    tokens = []
    for m in token_re.finditer(d):
        tokens.append(m.group(1) if m.group(1) else float(m.group(2)))
    return tokens


def parse_svg_path(d, transform=(0.0, 0.0)):
    """Parse SVG path 'd' into a list of absolute (x, y) vertex tuples.

    Supports straight-line commands only: M, m, L, l, H, h, V, v, Z, z.
    The optional transform=(dx, dy) is applied to every output point.
    """
    tokens = _tokenize_path(d)
    points = []
    cur = [0.0, 0.0]
    start = [0.0, 0.0]
    i = 0
    cmd = None

    def emit():
        points.append((cur[0] + transform[0], cur[1] + transform[1]))

    while i < len(tokens):
        t = tokens[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            if cmd in ('Z', 'z'):
                cur = start[:]
            continue

        if cmd in ('M', 'm'):
            x, y = tokens[i], tokens[i + 1]
            i += 2
            if cmd == 'm':
                cur[0] += x; cur[1] += y
            else:
                cur[0], cur[1] = x, y
            start = cur[:]
            emit()
            cmd = 'l' if cmd == 'm' else 'L'

        elif cmd in ('L', 'l'):
            x, y = tokens[i], tokens[i + 1]
            i += 2
            if cmd == 'l':
                cur[0] += x; cur[1] += y
            else:
                cur[0], cur[1] = x, y
            emit()

        elif cmd in ('H', 'h'):
            x = tokens[i]; i += 1
            cur[0] = cur[0] + x if cmd == 'h' else x
            emit()

        elif cmd in ('V', 'v'):
            y = tokens[i]; i += 1
            cur[1] = cur[1] + y if cmd == 'v' else y
            emit()

        else:
            raise ValueError(f'Unsupported SVG path command: {cmd!r}')

    return points


# ---------------------------------------------------------------------------
# SVG file parsing
# ---------------------------------------------------------------------------

def parse_svg_env_file(svg_path, env_path_id='env'):
    """Parse an environment SVG and return a data dict.

    Looks for a polygon path with *env_path_id* (default 'env'; use 'obstacle'
    for SVGs where the polygon represents an obstacle), id='path' (robot
    trajectory), and id='robot' (robot visualization group).

    Returned dict keys:
        env_polygon_points  list[(x,y)]  parsed polygon vertices in SVG coords
        path_points         list[(x,y)]  trajectory points in SVG coords
        env_path_d          str          raw 'd' attribute of polygon path
        env_path_style      str          style attribute of polygon path
        env_path_transform  str          transform attribute of polygon path
        robot_cx_local      float        cx of robot circles in group coords
        robot_cy_local      float        cy of robot circles in group coords
        robot_group_style   str          style of the robot <g> element
        robot_circles       list[dict]   SVG attributes for each circle
        svg_width           str
        svg_height          str
        svg_viewbox         str
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns_prefix = f'{{{SVG_NS}}}'
    ink_prefix = f'{{{INKSCAPE_NS}}}'

    def find_id(tag, eid):
        for elem in root.iter(ns_prefix + tag):
            if elem.get('id') == eid or elem.get(ink_prefix + 'label') == eid:
                return elem
        return None

    svg_width = root.get('width', '')
    svg_height = root.get('height', '')
    svg_viewbox = root.get('viewBox', '')

    # --- env/obstacle polygon path ---
    env_elem = find_id('path', env_path_id)
    if env_elem is None:
        raise ValueError(f"SVG must contain an element with id='{env_path_id}'")
    env_d = env_elem.get('d', '')
    env_style = env_elem.get('style', '')
    env_transform = env_elem.get('transform', '')
    tx, ty = parse_transform(env_transform)
    env_points = parse_svg_path(env_d, (tx, ty))
    # Drop consecutive duplicate vertices (degenerate segments cause 3-edge nodes)
    env_points_dedup = [env_points[0]] if env_points else []
    for p in env_points[1:]:
        if p != env_points_dedup[-1]:
            env_points_dedup.append(p)
    env_points = env_points_dedup
    # Drop duplicate closing vertex if path ends where it started
    if len(env_points) > 1 and env_points[0] == env_points[-1]:
        env_points = env_points[:-1]

    # --- trajectory path ---
    path_elem = find_id('path', 'path')
    if path_elem is None:
        raise ValueError("SVG must contain an element with id='path'")
    path_points = parse_svg_path(path_elem.get('d', ''))

    # --- shadow / near / far style templates ---
    def get_style(eid):
        elem = find_id('path', eid)
        return elem.get('style', '') if elem is not None else ''

    shadow_style = re.sub(r'marker-\w+:url\([^)]*\);?', '', get_style('shadow'))
    near_style = get_style('near')
    far_style = get_style('far')

    # --- robot group ---
    robot_group = find_id('g', 'robot')
    if robot_group is None:
        raise ValueError("SVG must contain a <g> element with id='robot'")
    robot_group_style = robot_group.get('style', '')

    circles = []
    first_cx, first_cy = None, None
    for circle in robot_group.iter(ns_prefix + 'circle'):
        attrs = {k: v for k, v in circle.attrib.items() if not k.startswith('{')}
        circles.append(attrs)
        if first_cx is None:
            first_cx = float(circle.get('cx', 0))
            first_cy = float(circle.get('cy', 0))

    # --- optional star path ---
    star_elem = find_id('path', 'star')
    star_path_d = star_elem.get('d', '') if star_elem is not None else None
    star_path_style = star_elem.get('style', '') if star_elem is not None else ''
    star_path_transform = star_elem.get('transform', '') if star_elem is not None else ''

    return {
        'env_polygon_points': env_points,
        'path_points': path_points,
        'env_path_d': env_d,
        'env_path_style': env_style,
        'env_path_transform': env_transform,
        'shadow_style': shadow_style,
        'near_style': near_style,
        'far_style': far_style,
        'robot_cx_local': first_cx,
        'robot_cy_local': first_cy,
        'robot_group_style': robot_group_style,
        'robot_circles': circles,
        'star_path_d': star_path_d,
        'star_path_style': star_path_style,
        'star_path_transform': star_path_transform,
        'svg_width': svg_width,
        'svg_height': svg_height,
        'svg_viewbox': svg_viewbox,
    }


# ---------------------------------------------------------------------------
# Path interpolation
# ---------------------------------------------------------------------------

def interpolate_path(points, n):
    """Return n uniformly arc-length-spaced points along a polyline.

    points -- list of (x, y)
    n      -- number of output points (includes both endpoints)
    Returns list of n (x, y) tuples.
    """
    if len(points) < 2:
        raise ValueError('Need at least 2 points to interpolate')

    seg_len = []
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        seg_len.append(sqrt(dx * dx + dy * dy))

    cum = [0.0]
    for sl in seg_len:
        cum.append(cum[-1] + sl)
    total = cum[-1]

    result = []
    for k in range(n):
        target = total * k / (n - 1) if n > 1 else 0.0
        if target >= total:
            result.append(points[-1])
            continue
        # Binary search for the containing segment
        seg = 0
        lo, hi = 0, len(seg_len) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid + 1] < target:
                lo = mid + 1
            else:
                hi = mid
        seg = lo
        t = (target - cum[seg]) / seg_len[seg] if seg_len[seg] > 0 else 0.0
        x = points[seg][0] + t * (points[seg + 1][0] - points[seg][0])
        y = points[seg][1] + t * (points[seg + 1][1] - points[seg][1])
        result.append((x, y))

    return result


# ---------------------------------------------------------------------------
# Shadow / hidden-area computation  (adapted from frontend/display.py)
# ---------------------------------------------------------------------------

def _shadow_endpoint(robot_pos, gap_vertex, graph):
    """Cast a ray from robot_pos through gap_vertex; return (shadow_pt, hit_edge)."""
    dx = gap_vertex.x - robot_pos.x
    dy = gap_vertex.y - robot_pos.y
    length = sqrt(dx * dx + dy * dy)
    if length == 0:
        return None, None
    scale = 1e6 / length
    far = vg.Point(gap_vertex.x + dx * scale, gap_vertex.y + dy * scale)

    min_dist = float('inf')
    nearest = None
    hit_edge = None
    for edge in graph.get_edges():
        if gap_vertex in edge:
            continue
        p = intersect_point(gap_vertex, far, edge)
        if p is None:
            continue
        if not on_segment(edge.p1, p, edge.p2): # verify p is on edge
            continue
        if (p.x - gap_vertex.x) * dx + (p.y - gap_vertex.y) * dy <= 0: # verify p is in the ray direction from gap_vertex
            continue
        d = edge_distance(gap_vertex, p)
        if d < min_dist:
            min_dist = d
            nearest = p
            hit_edge = edge
    return nearest, hit_edge


def _build_shadow_graph(graph, shadow_insertions):
    """Return next_pt/prev_pt dicts with shadow points inserted on boundary edges."""
    next_pt = {}
    prev_pt = {}
    for edge in graph.get_edges():
        next_pt[edge.p1] = edge.p2
        prev_pt[edge.p2] = edge.p1

    edge_to_pts = defaultdict(list)
    for shadow_pt, hit_edge in shadow_insertions:
        edge_to_pts[hit_edge].append(shadow_pt)

    for hit_edge, pts in edge_to_pts.items():
        pts.sort(key=lambda p: edge_distance(hit_edge.p1, p))
        chain = [hit_edge.p1] + pts + [hit_edge.p2]
        for i in range(len(chain) - 1):
            next_pt[chain[i]] = chain[i + 1]
            prev_pt[chain[i + 1]] = chain[i]

    return next_pt, prev_pt


def _trace_shadow_polygon(gap, shadow_pt, next_pt, prev_pt, max_steps=5000):
    """Walk the boundary from gap.vertex to shadow_pt; return vertex list."""
    vertices = [gap.vertex]
    current = gap.vertex
    for _ in range(max_steps):
        nxt = next_pt.get(current) if gap.side == vg.CCW else prev_pt.get(current)
        if nxt is None:
            break
        vertices.append(nxt)
        if nxt == shadow_pt:
            break
        current = nxt
    return vertices


def compute_shadow_polygons(robot_pos, gaps, polygon_graph):
    """Return a list of shadow polygon vertex lists (each a list of vg.Point).

    Each polygon encloses the region hidden behind one gap vertex.
    """
    shadow_info = []
    for gap in gaps:
        shadow_pt, hit_edge = _shadow_endpoint(robot_pos, gap.vertex, polygon_graph)
        if shadow_pt is not None and hit_edge is not None:
            shadow_info.append((gap, shadow_pt, hit_edge))

    if not shadow_info:
        return []

    next_pt, prev_pt = _build_shadow_graph(
        polygon_graph, [(sp, he) for _, sp, he in shadow_info]
    )

    result = []
    for gap, shadow_pt, _ in shadow_info:
        verts = _trace_shadow_polygon(gap, shadow_pt, next_pt, prev_pt)
        if len(verts) >= 3:
            result.append({
                'poly': verts,
                'gap_vertex': gap.vertex,
                'shadow_pt': shadow_pt,
            })
    return result


# ---------------------------------------------------------------------------
# SVG frame generation
# ---------------------------------------------------------------------------

def _xml_escape(s):
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def generate_frame_svg(svg_data, robot_x, robot_y, shadow_polys, frame_number=None,
                       show_event_lines=False, env=None, show_shadow_polys=True):
    """Return an SVG string for one animation frame.

    svg_data          -- dict from parse_svg_env_file()
    robot_x/y         -- robot position in SVG coordinate space
    shadow_polys      -- list of dicts with keys poly, gap_vertex, shadow_pt
    frame_number      -- if not None, renders the frame number in the bottom-right corner
    show_event_lines  -- if True, draw bitangent_comp / extension / inflection edges
    env               -- Environment instance; required when show_event_lines is True
    show_shadow_polys -- if False, gap lines (near/far) are drawn but filled polygons are omitted

    Draw order (bottom → top): event lines, shadow polygons, env, shadow lines, robot, frame label.
    """
    width = svg_data['svg_width']
    height = svg_data['svg_height']
    viewbox = svg_data['svg_viewbox']
    env_d = _xml_escape(svg_data['env_path_d'])
    env_style = _xml_escape(svg_data['env_path_style'])
    env_transform = _xml_escape(svg_data['env_path_transform'])
    shadow_style = _xml_escape(svg_data.get('shadow_style', ''))
    near_style = _xml_escape(svg_data.get('near_style', ''))
    far_style = _xml_escape(svg_data.get('far_style', ''))

    cx_local = svg_data['robot_cx_local']
    cy_local = svg_data['robot_cy_local']
    tx = robot_x - cx_local
    ty = robot_y - cy_local

    # --- robot ---
    robot_parts = []
    robot_style = _xml_escape(svg_data.get('robot_group_style', ''))
    robot_parts.append(
        f'  <g id="robot" style="{robot_style}"'
        f' transform="translate({tx:.6f},{ty:.6f})">'
    )
    for circle_attrs in svg_data['robot_circles']:
        attr_str = ' '.join(f'{k}="{_xml_escape(v)}"' for k, v in circle_attrs.items())
        robot_parts.append(f'    <circle {attr_str}/>')
    robot_parts.append('  </g>')

    # --- shadow lines (near/far per gap) ---
    shadow_line_parts = []
    for item in shadow_polys:
        gv = item['gap_vertex']
        sp = item['shadow_pt']
        shadow_line_parts.append(
            f'  <line x1="{robot_x:.4f}" y1="{robot_y:.4f}"'
            f' x2="{gv.x:.4f}" y2="{gv.y:.4f}" style="{near_style}"/>'
        )
        shadow_line_parts.append(
            f'  <line x1="{gv.x:.4f}" y1="{gv.y:.4f}"'
            f' x2="{sp.x:.4f}" y2="{sp.y:.4f}" style="{far_style}"/>'
        )

    # --- env boundary ---
    env_parts = [
        f'  <path id="env" d="{env_d}" style="{env_style}" transform="{env_transform}"/>',
    ]

    # --- star (static overlay, reproduced verbatim from the source SVG) ---
    star_parts = []
    raw_star_d = svg_data.get('star_path_d')
    if raw_star_d is not None:
        star_d = _xml_escape(raw_star_d)
        star_style = _xml_escape(svg_data.get('star_path_style', ''))
        star_transform = _xml_escape(svg_data.get('star_path_transform', ''))
        star_parts.append(
            f'  <path id="star" d="{star_d}" style="{star_style}"'
            + (f' transform="{star_transform}"' if star_transform else '')
            + '/>'
        )

    # --- shadow polygons ---
    shadow_poly_parts = []
    if show_shadow_polys:
        for item in shadow_polys:
            pts_str = ' '.join(f'{p.x:.4f},{p.y:.4f}' for p in item['poly'])
            shadow_poly_parts.append(f'  <polygon points="{pts_str}" style="{shadow_style}"/>')

    # --- frame number label (bottom-right corner) ---
    frame_label_parts = []
    if frame_number is not None:
        vb = [float(v) for v in viewbox.split()]
        vb_x, vb_y, vb_w, vb_h = vb[0], vb[1], vb[2], vb[3]
        label_x = vb_x + vb_w - 4
        label_y = vb_y + vb_h - 4
        frame_label_parts.append(
            f'  <text x="{label_x:.4f}" y="{label_y:.4f}"'
            f' text-anchor="end" dominant-baseline="auto"'
            f' font-size="{vb_h * 0.03:.4f}" font-family="monospace"'
            f' fill="#333333" opacity="0.7">{frame_number}</text>'
        )

    # --- event lines ---
    event_line_parts = []
    if show_event_lines and env is not None:
        m = re.search(r'stroke-width\s*:\s*([\d.]+)', svg_data.get('near_style', ''))
        sw = float(m.group(1)) if m else 0.3

        def _edge_lines(edges, color1, color2, stroke_width=None):
            w = stroke_width if stroke_width is not None else sw
            for edge in edges:
                color = color1 if edge.side >= 0 else color2
                event_line_parts.append(
                    f'  <line id="{edge.eid}" x1="{edge.p1.x:.4f}" y1="{edge.p1.y:.4f}"'
                    f' x2="{edge.p2.x:.4f}" y2="{edge.p2.y:.4f}"'
                    f' stroke="{color}" stroke-width="{w}" opacity="0.8"/>'
                )

        _edge_lines(env.bitangent_comp.get_edges(), '#0072BD', '#D95319')
        _edge_lines(env.extension.get_edges(),      '#D2E6FF', '#FFDCDC', sw / 4)
        _edge_lines(env.inflection.get_edges(),     '#EDB120', '#7E2F8E')

    # Assemble in draw order: event lines → shadow polygons → env → star → shadow lines → robot → frame label
    header = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg width="{width}" height="{height}" viewBox="{viewbox}"',
        f'     xmlns="http://www.w3.org/2000/svg">',
    ]
    return '\n'.join(
        header + event_line_parts + shadow_poly_parts + env_parts + star_parts
        + shadow_line_parts + robot_parts + frame_label_parts + ['</svg>']
    )


# ---------------------------------------------------------------------------
# Event-lines SVG (static, one file per environment)
# ---------------------------------------------------------------------------

def generate_event_lines_svg(svg_data, env) -> str:
    """Return a standalone SVG showing all critical-event edges for the environment.

    Draws the env boundary plus bitangent_comp / extension / inflection edges,
    using the same coordinate space and stroke-width as the frame SVGs.
    Since these edges are static, only one file is needed per environment.

    Edge colours mirror the pygame show_static_visgraph display:
      - bitangent_comp  (S/M): blue (#0072BD) side=+1 / orange (#D95319) side=-1
      - extension       (N/P): light-blue (#D2E6FF) side=+1 / light-red (#FFDCDC) side=-1
      - inflection      (A/D): yellow (#EDB120) side=+1 / purple (#7E2F8E) side=-1
    """
    width = svg_data['svg_width']
    height = svg_data['svg_height']
    viewbox = svg_data['svg_viewbox']
    env_d = _xml_escape(svg_data['env_path_d'])
    env_style = _xml_escape(svg_data['env_path_style'])
    env_transform = _xml_escape(svg_data['env_path_transform'])

    # Match stroke-width to the near/far gap lines from the SVG template.
    m = re.search(r'stroke-width\s*:\s*([\d.]+)', svg_data.get('near_style', ''))
    sw = float(m.group(1)) if m else 0.3

    def _layer(layer_id, edges, color1, color2, stroke_width=None, split=False):
        w = stroke_width if stroke_width is not None else sw
        if split:
            pos = [e for e in edges if e.side >= 0]
            neg = [e for e in edges if e.side < 0]
            def _lines(subset, color):
                return [
                    f'    <line id="{e.eid}" x1="{e.p1.x:.4f}" y1="{e.p1.y:.4f}"'
                    f' x2="{e.p2.x:.4f}" y2="{e.p2.y:.4f}"'
                    f' stroke="{color}" stroke-width="{w}" opacity="0.8"/>'
                    for e in subset
                ]
            return (
                [f'  <g id="{layer_id}_pos">'] + _lines(pos, color1) + ['  </g>']
                + [f'  <g id="{layer_id}_neg">'] + _lines(neg, color2) + ['  </g>']
            )
        inner = []
        for edge in edges:
            color = color1 if edge.side >= 0 else color2
            inner.append(
                f'    <line id="{edge.eid}" x1="{edge.p1.x:.4f}" y1="{edge.p1.y:.4f}"'
                f' x2="{edge.p2.x:.4f}" y2="{edge.p2.y:.4f}"'
                f' stroke="{color}" stroke-width="{w}" opacity="0.8"/>'
            )
        return [f'  <g id="{layer_id}">'] + inner + ['  </g>']

    header = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg width="{width}" height="{height}" viewBox="{viewbox}"',
        f'     xmlns="http://www.w3.org/2000/svg">',
    ]
    layers = (
        _layer('bitangent_comp', env.bitangent_comp.get_edges(), '#0072BD', '#D95319')
        + _layer('extension',    env.extension.get_edges(),      '#D2E6FF', '#FFDCDC',
                 stroke_width=sw / 4, split=True)
        + _layer('inflection',   env.inflection.get_edges(),     '#EDB120', '#7E2F8E')
    )
    dot_r = sw * 0.5
    env_part = ['  <g id="env_vertices">'] + [
        f'    <circle cx="{x:.4f}" cy="{y:.4f}" r="{dot_r:.4f}" fill="#333333"/>'
        for x, y in svg_data['env_polygon_points']
    ] + ['  </g>']
    return '\n'.join(header + layers + env_part + ['</svg>'])


# ---------------------------------------------------------------------------
# Gap-sensor SVG
# ---------------------------------------------------------------------------

# CCW = 1, CW = -1  (from pyvisgraph)
_CCW = 1
_CW = -1
_COLOR_CCW = "#ED2939"   # red
_COLOR_CW  = "#1100BB"   # blue
COLOR_SENSOR_DEFAULT = "#1a5fb4"


def generate_sensor_svg(gaps, size: int = 500, radius: float = 200.0) -> str:
    """Return an SVG string showing the circular gap-sensor HUD.

    Mirrors the pygame ``draw_gap_sensor`` layout:
      - Thin ring of *radius* centred in a *size* × *size* canvas.
      - Filled dot at the centre.
      - One tick mark per gap at its angular direction, coloured red (CCW)
        or blue (CW), with the gap id as a label just outside the ring.

    Parameters
    ----------
    gaps:
        Iterable of Gap objects (need ``.dir``, ``.side``).
    size:
        Canvas width and height in pixels.
    radius:
        Radius of the sensor ring in pixels.
    """
    cx = cy = size / 2.0
    tick_len    = radius * 0.2        # length of the tick mark beyond the ring
    label_off   = radius * 0.18        # label centre distance from ring edge
    dot_r       = size * 0.02          # centre-dot radius
    stroke_w    = max(1.0, size * 0.006)
    font_size   = size * 0.045

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"'
        f' xmlns="http://www.w3.org/2000/svg">',
        f'  <rect width="{size}" height="{size}" fill="white"/>',
        f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="{radius:.3f}"'
        f' fill="none" stroke="{COLOR_SENSOR_DEFAULT}" stroke-width="{stroke_w:.2f}"/>',
        f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="{dot_r:.3f}" fill="{COLOR_SENSOR_DEFAULT}"/>',
    ]

    for gap in gaps:
        dx, dy = float(gap.dir[0]), float(gap.dir[1])

        x1 = cx + radius * dx
        y1 = cy + radius * dy
        x2 = cx + (radius - tick_len) * dx
        y2 = cy + (radius - tick_len) * dy
        lx = cx + (radius - tick_len + label_off) * dx
        ly = cy + (radius - tick_len + label_off) * dy

        ## Currently not differentiating left or right gaps 
        # if gap.side == _CCW:
        #     color = _COLOR_CCW
        # elif gap.side == _CW:
        #     color = _COLOR_CW
        # else:
        #     color = COLOR_SENSOR_DEFAULT

        parts.append(
            f'  <line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"'
            f' stroke="{COLOR_SENSOR_DEFAULT}" stroke-width="{stroke_w*2:.2f}"/>'
        )

    parts.append('</svg>')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Cyclic-order SVG
# ---------------------------------------------------------------------------

def generate_cyclic_svg(gaps, size: int = 500, radius: float = 200.0) -> str:
    """Return an SVG showing the cyclic order of gaps around the robot.

    Gaps are placed uniformly on a circle (sorted by their clockwise angular
    direction from the robot).  Arc arrows drawn along the circle between
    consecutive gaps indicate the clockwise cyclic order.  No background ring
    or centre dot is drawn.

    Parameters
    ----------
    gaps:
        Iterable of Gap objects (need ``.dir``).
    size:
        Canvas width and height in pixels.
    radius:
        Radius of the layout circle in pixels.
    """
    cx = cy = size / 2.0
    gap_list = list(gaps)
    n = len(gap_list)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"'
        f' xmlns="http://www.w3.org/2000/svg">',
        f'  <rect width="{size}" height="{size}" fill="white"/>',
    ]

    if n == 0:
        parts.append('</svg>')
        return '\n'.join(parts)

    # Sort by clockwise angle in SVG coordinates (y-down: atan2(dy,dx) increases CW)
    gap_list.sort(key=lambda g: math.atan2(float(g.dir[1]), float(g.dir[0])))

    # Uniform positions on the circle, starting at the top and going clockwise
    thetas = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

    sw = max(1.0, size * 0.005)
    tick_half = radius * 0.08   # half-length of each radial tick mark
    font_size = size * 0.045
    arc_sw = sw * 1.8
    color = COLOR_SENSOR_DEFAULT

    # DartArrow marker (markerUnits defaults to strokeWidth)
    parts.append(
        '  <defs>'
        '<marker style="overflow:visible" id="DartArrow"'
        ' refX="0" refY="0" orient="auto-start-reverse"'
        ' markerWidth="0.8" markerHeight="0.8"'
        ' viewBox="0 0 1 1" preserveAspectRatio="xMidYMid">'
        '<path style="fill:context-stroke;fill-rule:evenodd;stroke:none"'
        ' d="M 0,0 5,-5 -12.5,0 5,5 Z" transform="scale(-0.5)"/>'
        '</marker></defs>'
    )

    # Arc arrows between consecutive gaps (clockwise, sweep-flag=1).
    # n=1: single gap gets a near-full-circle self-loop (large-arc=1).
    if n >= 1:
        pad_start = 0.05
        pad_end = 0.15
        for i in range(n):
            t_start = thetas[i] + pad_start
            next_theta = thetas[(i + 1) % n]
            if next_theta <= thetas[i]:   # wrap from last gap back to first
                next_theta += 2 * math.pi
            t_end = next_theta - pad_end

            sx = cx + radius * math.cos(t_start)
            sy = cy + radius * math.sin(t_start)
            ex = cx + radius * math.cos(t_end)
            ey = cy + radius * math.sin(t_end)

            span = t_end - t_start  # always positive by construction
            large_arc = 1 if span > math.pi else 0
            parts.append(
                f'  <path d="M {sx:.3f},{sy:.3f}'
                f' A {radius:.3f},{radius:.3f} 0 {large_arc},1 {ex:.3f},{ey:.3f}"'
                f' fill="none" stroke="{color}" stroke-width="{arc_sw:.2f}"'
                f' marker-end="url(#DartArrow)"/>'
            )

    # Gap tick marks (radial lines straddling the circle) and ID labels
    label_r = radius + tick_half + font_size * 0.7
    for i, gap in enumerate(gap_list):
        t = thetas[i]
        cos_t, sin_t = math.cos(t), math.sin(t)
        x1 = cx + (radius - tick_half) * cos_t
        y1 = cy + (radius - tick_half) * sin_t
        x2 = cx + (radius + tick_half) * cos_t
        y2 = cy + (radius + tick_half) * sin_t
        # lx = cx + label_r * cos_t
        # ly = cy + label_r * sin_t
        parts.append(
            f'  <line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"'
            f' stroke="{color}" stroke-width="{arc_sw:.2f}"/>'
        )

    parts.append('</svg>')
    return '\n'.join(parts)
