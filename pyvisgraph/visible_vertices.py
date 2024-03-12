"""
The MIT License (MIT)

Copyright (c) 2016 Christian August Reksten-Monsen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import division
from math import pi, sqrt, atan, acos
from pyvisgraph.classes import Point, Edge

INF = 10000
CCW = 1
CW = -1
COLLINEAR = 0
"""Due to floating point representation error, some functions need to
   truncate floating point numbers to a certain tolerance."""
COLIN_TOLERANCE = 10
T = 10**COLIN_TOLERANCE
T2 = 10.0**COLIN_TOLERANCE

# TODO: change function name to bitangent_lines


def visible_vertices(point, graph, origin=None, destination=None, scan="full"):
    """Returns list of Points in graph visible by point.

    If origin and/or destination Points are given, these will also be checked
    for visibility. scan 'full' will check for visibility against all points in
    graph, 'half' will check for visibility against half the points. This saves
    running time when building a complete visibility graph, as the points
    that are not checked will eventually be 'point'.
    """
    edges = graph.get_edges()
    points = graph.get_points()
    if origin:
        points.append(origin)
    if destination:
        points.append(destination)
    points.sort(key=lambda p: (angle(point, p), edge_distance(point, p)))

    # Initialize open_edges with any intersecting edges on the half line from
    # point along the positive x-axis
    open_edges = OpenEdges()
    point_inf = Point(INF, point.y)
    for edge in edges:
        if point in edge:
            continue
        if edge_intersect(point, point_inf, edge):
            if on_segment(point, edge.p1, point_inf):
                continue
            if on_segment(point, edge.p2, point_inf):
                continue
            open_edges.insert(point, point_inf, edge)

    visible = []
    prev = None
    prev_visible = None
    for p in points:
        if p == point:
            continue
        if scan == "half" and angle(point, p) > pi:
            break

        # Update open_edges - remove clock wise edges incident on p
        if open_edges:
            for edge in graph[p]:
                if ccw(point, p, edge.get_adjacent(p)) == CW:
                    open_edges.delete(point, p, edge)

        # Check if p is visible from point
        is_visible = False
        # ...Non-collinear points
        if (
            prev is None
            or ccw(point, prev, p) != COLLINEAR
            or not on_segment(point, prev, p)
        ):
            if len(open_edges) == 0:
                is_visible = True
            elif not edge_intersect(point, p, open_edges.smallest()):
                is_visible = True
        # ...For collinear points, if previous point was not visible, p is not
        elif not prev_visible:
            is_visible = False
        # ...For collinear points, if previous point was visible, need to check
        # that the edge from prev to p does not intersect any open edge.
        else:
            # TODO: need to add this back, colinear points on wall has problem
            is_visible = False  # The further points on the same line is invisible
            # is_visible = True
            # for edge in open_edges:
            #     if prev not in edge and edge_intersect(prev, p, edge):
            #         is_visible = False
            #         break
            # if is_visible and edge_in_polygon(prev, p, graph):
            #         is_visible = False

        # Check if the visible edge is interior to its polygon
        if is_visible and p not in graph.get_adjacent_points(point):
            is_visible = not edge_in_polygon(point, p, graph)

        # Check the two ends of a bitangent line, the two edges on each side should be on the same side of the line
        if is_visible:
            sides = []
            _edges = graph[p]
            if len(_edges) == 2:
                for _edge in _edges:
                    sides.append(ccw(point, p, _edge.get_adjacent(p)))
                if sides[0] != sides[1]:
                    is_visible = False
            elif len(_edges) == 0:
                is_visible = True
            else:
                raise Exception(
                    "len(_edges) should be 0 or 2, but is {}".format(len(_edges))
                )

        if is_visible:
            sides = []
            _edges = graph[point]
            if len(_edges) == 2:
                for edge in _edges:
                    sides.append(ccw(p, point, edge.get_adjacent(point)))
                if sides[0] != sides[1]:
                    is_visible = False
            elif len(_edges) == 0:
                is_visible = True
            else:
                raise Exception(
                    "len(_edges) should be 0 or 2, but is {}".format(len(_edges))
                )

        if is_visible:
            visible.append(p)

        # Update open_edges - Add counter clock wise edges incident on p
        for edge in graph[p]:
            if (point not in edge) and ccw(point, p, edge.get_adjacent(p)) == CCW:
                open_edges.insert(point, p, edge)

        prev = p
        prev_visible = is_visible
    return visible


def convex_chain(graph, conv_chain):
    """_summary_
    convex_chain compute the convex vertex chains in 'graph', and put them in 'conv_chain'
    Args:
        graph (PolygonGraph): The original graph
        conv_chain (ChainGraph): The convex chain graph

    Raises:
        Exception: _description_
        Exception: _description_
    """
    chain_id = 0
    for pid, polygon in graph.polygon_vertices.items():
        chain_id_init = chain_id
        is_prev_conv = False

        p = polygon[0]
        prev_point = graph.get_prev_point(p)
        p_n = graph.get_next_point(prev_point)
        p_p = graph.get_prev_point(prev_point)
        if not p_n or not p_p:
            raise Exception(f"point {prev_point} has no prev or next point")
        if ccw(p_p, prev_point, p_n) == CCW:
            is_prev_conv = True

        chain_points = []
        chain_edges = []
        for i in range(len(polygon)):
            p_p = graph.get_prev_point(p)
            p_n = graph.get_next_point(p)
            if not p_n or not p_p:
                raise Exception(f"point {p} has no prev or next point")
            if ccw(p_p, p, p_n) == CCW:  # Add convex vertex to the current chain
                chain_points.append(p)
                if is_prev_conv:  # If the previos vertex is also convex, add the edge between them
                    chain_edges.append(list(graph[p_p, p])[0])
                is_prev_conv = True
            else:
                if is_prev_conv:  # Reach the end of the chain
                    conv_chain.new_chain(chain_id, chain_points, chain_edges)
                    chain_points = []
                    chain_edges = []
                    chain_id += 1
                is_prev_conv = False
            p = p_n

        if chain_points:
            # If vertices remain in the current chain after traverse the polygon, 
            # it means the chain continues from end of the polygon to the beginning of the polygon
            conv_chain.add_or_new_chain(
                chain_id_init, chain_points, chain_edges)
            chain_points = []
            chain_edges = []
            chain_id += 1


def bitangent_complement(graph, visgraph, bitcomp):
    # Calculate Bitangent Complement Lines
    for bit_line in visgraph.get_edges():
        # print(bit_line)
        p1 = bit_line.p1
        p2 = bit_line.p2
        p1_d_min = float("inf")
        p1_p_min = None
        p2_d_min = float("inf")
        p2_p_min = None
        p1_vec = (p2 - p1).to_vec()
        p2_vec = p1_vec * -1
        for edge in graph.get_edges():
            p = intersect_point(p1, p2, edge)
            if p and p != p1 and p != p2 and on_segment(edge.p1, p, edge.p2):
                # print(edge)
                # print(p)
                if (p - p1).to_vec().dot(p1_vec) < 0:
                    d = edge_distance(p, p1)
                    if d < p1_d_min:
                        p1_d_min = d
                        p1_p_min = p
                if (p - p2).to_vec().dot(p2_vec) < 0:
                    d = edge_distance(p, p2)
                    if d < p2_d_min:
                        p2_d_min = d
                        p2_p_min = p
        if p1_p_min:
            _next_point = graph.get_next_point(bit_line.p1)
            if _next_point:
                edge = Edge(bit_line.p1, p1_p_min)
                edge.side = ccw(p1_p_min, bit_line.p1, _next_point) 
                if edge.side == COLLINEAR:
                    raise Exception("ERROR: Bitangent complement is collinear with a boundary edge")
                bitcomp.add_edge(edge)

        else:
            raise Exception("bitangent complement for p1 not found")

        if p2_p_min:
            _next_point = graph.get_next_point(bit_line.p2)
            if _next_point:
                edge = Edge(bit_line.p2, p2_p_min)
                edge.side = ccw(p2_p_min, bit_line.p2, _next_point)
                if edge.side == COLLINEAR:
                    raise Exception("ERROR: Bitangent complement is collinear with a boundary edge")
                bitcomp.add_edge(edge)
        else:
            raise Exception("bitangent complement for p2 not found")


def inflection_lines(graph, conv_chain, inflx):

    for chain_id, chain in conv_chain.chains.items():
        if chain.start:
            p_p = graph.get_prev_point(chain.start)
            edge = ray_cast(p_p, chain.start, graph)
            edge.side = CW #In GUI, boundary on the lhs
            inflx.add_edge(edge)

            p_n = graph.get_next_point(chain.end)
            edge = ray_cast(p_n, chain.end, graph)
            edge.side = CCW #In GUI, boundary on the rhs
            inflx.add_edge(edge)


def ray_cast(p1, p2, graph):
    """
    extend an ray from p2 in the direction of p1->p2 until it hit an edge
    """
    p2_d_min = float("inf")
    p2_p_min = None
    p2_vec = (p2 - p1).to_vec()
    for edge in graph.get_edges():
        p = intersect_point(p1, p2, edge)
        if p and p != p1 and p != p2 and on_segment(edge.p1, p, edge.p2):
            if (p - p2).to_vec().dot(p2_vec) > 0:
                d = edge_distance(p, p2)
                if d < p2_d_min:
                    p2_d_min = d
                    p2_p_min = p
    if p2_p_min:
        edge = Edge(p2, p2_p_min)
        edge.side = ccw(p2_p_min, p2, graph.get_next_point(p2))
        return edge
    else:
        raise Exception("Cannot extend p1->p2")


def polygon_crossing(p1, poly_edges):
    """Returns True if Point p1 is internal to the polygon. The polygon is
    defined by the Edges in poly_edges. Uses crossings algorithm and takes into
    account edges that are collinear to p1."""
    p2 = Point(INF, p1.y)
    intersect_count = 0
    for edge in poly_edges:
        if p1.y < edge.p1.y and p1.y < edge.p2.y:
            continue
        if p1.y > edge.p1.y and p1.y > edge.p2.y:
            continue
        if p1.x > edge.p1.x and p1.x > edge.p2.x:
            continue
        # Deal with points collinear to p1
        edge_p1_collinear = ccw(p1, edge.p1, p2) == COLLINEAR
        edge_p2_collinear = ccw(p1, edge.p2, p2) == COLLINEAR
        if edge_p1_collinear and edge_p2_collinear:
            continue
        if edge_p1_collinear or edge_p2_collinear:
            collinear_point = edge.p1 if edge_p1_collinear else edge.p2
            if collinear_point.x > p1.x and edge.get_adjacent(collinear_point).y > p1.y:
                intersect_count += 1
        elif edge_intersect(p1, p2, edge):
            intersect_count += 1
    if intersect_count % 2 == 0:
        return False
    return True


def edge_in_polygon(p1, p2, graph):
    """Return true if the edge from p1 to p2 is interior to any polygon
    in graph."""
    if p1.polygon_id != p2.polygon_id:
        return False
    if p1.polygon_id == -1 or p2.polygon_id == -1:
        return False

    mid_point = Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
    if p1.polygon_id == 0 and p2.polygon_id == 0:
        return not polygon_crossing(mid_point, graph.polygon_edges[p1.polygon_id])
    else:
        return polygon_crossing(mid_point, graph.polygon_edges[p1.polygon_id])


def point_in_polygon(p, graph):
    """Return true if the point p is interior to any polygon in graph."""
    for polygon in graph.polygon_edges:
        if polygon_crossing(p, graph.polygon_edges[polygon]):
            return polygon
    return -1


def point_in_wall(p, graph):
    """Return true if the point p is interior to polygon 0 (wall) in graph."""
    if polygon_crossing(p, graph.polygon_edges[0]):
        return True
    else:
        return False


def point_valid(p, graph):
    """Return true if the point p is interior to polygon 0 (wall) and not interior to other polygons."""
    for polygon in graph.polygon_edges:
        if polygon == 0:
            if not polygon_crossing(p, graph.polygon_edges[0]):
                return False
        elif polygon_crossing(p, graph.polygon_edges[polygon]):
            return False
    return True


def unit_vector(c, p):
    magnitude = edge_distance(c, p)
    return Point((p.x - c.x) / magnitude, (p.y - c.y) / magnitude)


def closest_point(p, graph, polygon_id, length=0.001):
    """Assumes p is interior to the polygon with polygon_id. Returns the
    closest point c outside the polygon to p, where the distance from c to
    the intersect point from p to the edge of the polygon is length."""
    polygon_edges = graph.polygon_edges[polygon_id]
    close_point = None
    close_edge = None
    close_dist = None
    # Finds point closest to p, but on a edge of the polygon.
    # Solution from http://stackoverflow.com/a/6177788/4896361
    for i, e in enumerate(polygon_edges):
        num = (p.x - e.p1.x) * (e.p2.x - e.p1.x) + \
            (p.y - e.p1.y) * (e.p2.y - e.p1.y)
        denom = (e.p2.x - e.p1.x) ** 2 + (e.p2.y - e.p1.y) ** 2
        u = num / denom
        pu = Point(e.p1.x + u * (e.p2.x - e.p1.x),
                   e.p1.y + u * (e.p2.y - e.p1.y))
        pc = pu
        if u < 0:
            pc = e.p1
        elif u > 1:
            pc = e.p2
        d = edge_distance(p, pc)
        if i == 0 or d < close_dist:
            close_dist = d
            close_point = pc
            close_edge = e

    # Extend the newly found point so it is outside the polygon by `length`.
    if close_point in close_edge:
        c = close_edge.p1 if close_point == close_edge.p1 else close_edge.p2
        edges = list(graph[c])
        v1 = unit_vector(c, edges[0].get_adjacent(c))
        v2 = unit_vector(c, edges[1].get_adjacent(c))
        vsum = unit_vector(Point(0, 0), Point(v1.x + v2.x, v1.y + v2.y))
        close1 = Point(c.x + (vsum.x * length), c.y + (vsum.y * length))
        close2 = Point(c.x - (vsum.x * length), c.y - (vsum.y * length))
        if point_in_polygon(close1, graph) == -1:
            return close1
        return close2
    else:
        v = unit_vector(p, close_point)
        return Point(close_point.x + v.x * length, close_point.y + v.y * length)


def edge_distance(p1, p2):
    """Return the Euclidean distance between two Points."""
    return sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)


def intersect_point(p1, p2, edge):
    """Return intersect Point where the edge from p1, p2 intersects edge"""
    if p1 in edge:
        return p1
    if p2 in edge:
        return p2
    if edge.p1.x == edge.p2.x:
        if p1.x == p2.x:
            return None
        pslope = (p1.y - p2.y) / (p1.x - p2.x)
        intersect_x = edge.p1.x
        intersect_y = pslope * (intersect_x - p1.x) + p1.y
        return Point(intersect_x, intersect_y)

    if p1.x == p2.x:
        eslope = (edge.p1.y - edge.p2.y) / (edge.p1.x - edge.p2.x)
        intersect_x = p1.x
        intersect_y = eslope * (intersect_x - edge.p1.x) + edge.p1.y
        return Point(intersect_x, intersect_y)

    pslope = (p1.y - p2.y) / (p1.x - p2.x)
    eslope = (edge.p1.y - edge.p2.y) / (edge.p1.x - edge.p2.x)
    if eslope == pslope:
        return None
    intersect_x = (eslope * edge.p1.x - pslope * p1.x + p1.y - edge.p1.y) / (
        eslope - pslope
    )
    intersect_y = eslope * (intersect_x - edge.p1.x) + edge.p1.y
    return Point(intersect_x, intersect_y)


def edge_cross_point(edge1, edge2):
    p = intersect_point(edge1.p1, edge1.p2, edge2)
    if p and on_segment(edge1.p1, p, edge1.p2) and on_segment(edge2.p1, p, edge2.p2):
        return p
    else:
        return None


def point_edge_distance(p1, p2, edge):
    """Return the Eucledian distance from p1 to intersect point with edge.
    Assumes the line going from p1 to p2 intersects edge before reaching p2."""
    ip = intersect_point(p1, p2, edge)
    if ip is not None:
        return edge_distance(p1, ip)
    return 0


def angle(center, point):
    """Return the angle (radian) of point from center of the radian circle.
     ------p
     |   /
     |  /
    c|a/
    """
    dx = point.x - center.x
    dy = point.y - center.y
    if dx == 0:
        if dy < 0:
            return pi * 3 / 2
        return pi / 2
    if dy == 0:
        if dx < 0:
            return pi
        return 0
    if dx < 0:
        return pi + atan(dy / dx)
    if dy < 0:
        return 2 * pi + atan(dy / dx)
    return atan(dy / dx)


def angle2(point_a, point_b, point_c):
    """Return angle B (radian) between point_b and point_c.
           c
         /  \
       /    B\
      a-------b
    """
    a = (point_c.x - point_b.x) ** 2 + (point_c.y - point_b.y) ** 2
    b = (point_c.x - point_a.x) ** 2 + (point_c.y - point_a.y) ** 2
    c = (point_b.x - point_a.x) ** 2 + (point_b.y - point_a.y) ** 2
    cos_value = (a + c - b) / (2 * sqrt(a) * sqrt(c))
    return acos(int(cos_value * T) / T2)


def ccw(A, B, C):
    """Return 1 if counter clockwise, -1 if clock wise, 0 if collinear"""
    #  Rounding this way is faster than calling round()
    area = int(((B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x)) * T) / T2
    if area > 0:
        return CCW
    if area < 0:
        return CW
    return 0


def on_segment(p, q, r):
    """Given three colinear points p, q, r, the function checks if point q
    lies on line segment 'pr'."""
    if (q.x <= max(p.x, r.x)) and (q.x >= min(p.x, r.x)):
        if (q.y <= max(p.y, r.y)) and (q.y >= min(p.y, r.y)):
            return True
    return False


def edge_intersect(p1, q1, edge):
    """Return True if edge from A, B interects edge.
    http://www.geeksforgeeks.org/check-if-two-given-line-segments-intersect/"""
    p2 = edge.p1
    q2 = edge.p2
    o1 = ccw(p1, q1, p2)
    o2 = ccw(p1, q1, q2)
    o3 = ccw(p2, q2, p1)
    o4 = ccw(p2, q2, q1)

    # General case
    if o1 != o2 and o3 != o4:
        return True
    # p1, q1 and p2 are colinear and p2 lies on segment p1q1
    if o1 == COLLINEAR and on_segment(p1, p2, q1):
        return True
    # p1, q1 and p2 are colinear and q2 lies on segment p1q1
    if o2 == COLLINEAR and on_segment(p1, q2, q1):
        return True
    # p2, q2 and p1 are colinear and p1 lies on segment p2q2
    if o3 == COLLINEAR and on_segment(p2, p1, q2):
        return True
    # p2, q2 and q1 are colinear and q1 lies on segment p2q2
    if o4 == COLLINEAR and on_segment(p2, q1, q2):
        return True
    return False


class OpenEdges(object):
    def __init__(self):
        self._open_edges = []

    def insert(self, p1, p2, edge):
        self._open_edges.insert(self._index(p1, p2, edge), edge)

    def delete(self, p1, p2, edge):
        index = self._index(p1, p2, edge) - 1
        if self._open_edges[index] == edge:
            del self._open_edges[index]

    def smallest(self):
        return self._open_edges[0]

    def _less_than(self, p1, p2, edge1, edge2):
        """Return True if edge1 is smaller than edge2, False otherwise."""
        if edge1 == edge2:
            return False
        if not edge_intersect(p1, p2, edge2):
            return True
        edge1_dist = point_edge_distance(p1, p2, edge1)
        edge2_dist = point_edge_distance(p1, p2, edge2)
        if edge1_dist > edge2_dist:
            return False
        if edge1_dist < edge2_dist:
            return True
        # If the distance is equal, we need to compare on the edge angles.
        if edge1_dist == edge2_dist:
            if edge1.p1 in edge2:
                same_point = edge1.p1
            else:
                same_point = edge1.p2
            angle_edge1 = angle2(p1, p2, edge1.get_adjacent(same_point))
            angle_edge2 = angle2(p1, p2, edge2.get_adjacent(same_point))
            if angle_edge1 < angle_edge2:
                return True
            return False

    def _index(self, p1, p2, edge):
        lo = 0
        hi = len(self._open_edges)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._less_than(p1, p2, edge, self._open_edges[mid]):
                hi = mid
            else:
                lo = mid + 1
        return lo

    def __len__(self):
        return len(self._open_edges)

    def __getitem__(self, index):
        return self._open_edges[index]
