"""SVG utilities: parse environment SVG files and generate per-frame SVGs."""

import re
from collections import defaultdict
from math import sqrt
import xml.etree.ElementTree as ET

import pyvisgraph as vg
from pyvisgraph.visible_vertices import intersect_point, edge_distance

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

def parse_svg_env_file(svg_path):
    """Parse an environment SVG and return a data dict.

    Looks for elements with id='env' (wall path), id='path' (robot trajectory),
    and id='robot' (robot visualization group).

    Returned dict keys:
        env_polygon_points  list[(x,y)]  parsed wall vertices in SVG coords
        path_points         list[(x,y)]  trajectory points in SVG coords
        env_path_d          str          raw 'd' attribute of env path
        env_path_style      str          style attribute of env path
        env_path_transform  str          transform attribute of env path
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

    # --- env path ---
    env_elem = find_id('path', 'env')
    if env_elem is None:
        raise ValueError("SVG must contain an element with id='env'")
    env_d = env_elem.get('d', '')
    env_style = env_elem.get('style', '')
    env_transform = env_elem.get('transform', '')
    tx, ty = parse_transform(env_transform)
    env_points = parse_svg_path(env_d, (tx, ty))
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
        if not (min(edge.p1.x, edge.p2.x) - 1e-6 <= p.x <= max(edge.p1.x, edge.p2.x) + 1e-6):
            continue
        if not (min(edge.p1.y, edge.p2.y) - 1e-6 <= p.y <= max(edge.p1.y, edge.p2.y) + 1e-6):
            continue
        if (p.x - gap_vertex.x) * dx + (p.y - gap_vertex.y) * dy <= 0:
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


def generate_frame_svg(svg_data, robot_x, robot_y, shadow_polys):
    """Return an SVG string for one animation frame.

    svg_data     -- dict from parse_svg_env_file()
    robot_x/y   -- robot position in SVG coordinate space
    shadow_polys -- list of dicts with keys poly, gap_vertex, shadow_pt

    Draw order (bottom → top): robot, shadow lines, env, shadow polygons.
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

    # --- shadow polygons ---
    shadow_poly_parts = []
    for item in shadow_polys:
        pts_str = ' '.join(f'{p.x:.4f},{p.y:.4f}' for p in item['poly'])
        shadow_poly_parts.append(f'  <polygon points="{pts_str}" style="{shadow_style}"/>')

    # Assemble in draw order: shadow polygons → env → shadow lines → robot
    header = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg width="{width}" height="{height}" viewBox="{viewbox}"',
        f'     xmlns="http://www.w3.org/2000/svg">',
    ]
    return '\n'.join(
        header + shadow_poly_parts + env_parts + shadow_line_parts + robot_parts + ['</svg>']
    )
