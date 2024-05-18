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

from collections import defaultdict
import sys
from pyvisgraph.classes import Point, Edge, Chain
from pyvisgraph.visible_vertices import polygon_crossing, edge_cross_point

eps = 0.01


class Graph(object):
    """
    A Graph is represented by a dict where the keys are Points in the Graph
    and the dict values are sets containing Edges incident on each Point.
    A separate set *edges* contains all Edges in the graph.
    """

    def __init__(self):
        self.graph = defaultdict(set)
        self.edges = set()

    def get_adjacent_points(self, point):
        return [edge.get_adjacent(point) for edge in self[point]]

    def get_next_point(self, point):
        edges = self[point]
        for edge in edges:
            if point == edge.p1:
                return edge.p2
        return None

    def get_prev_point(self, point):
        edges = self[point]
        for edge in edges:
            if point == edge.p2:
                return edge.p1
        return None

    def get_points(self):
        return list(self.graph)

    def get_edges(self):
        return self.edges

    def add_edge(self, edge):
        self.graph[edge.p1].add(edge)
        self.graph[edge.p2].add(edge)
        self.edges.add(edge)

    def add_edges(self, edges):
        for edge in edges:
            self.add_edge(edge)

    def add_point(self, point):
        assert not point in self.graph, f"add_point: {point} already in graph"
        self.graph[point] = set()

    def add_points(self, points):
        for point in points:
            self.add_point(point)

    def is_edge_intersect(self, edge):
        for _edge in self.edges:
            if edge_cross_point(_edge, edge):
                return True
        return False

    def __contains__(self, item):
        if isinstance(item, Point):
            return item in self.graph
        if isinstance(item, Edge):
            return item in self.edges
        return False

    def __getitem__(self, p):
        if isinstance(p, Point):
            if p in self.graph:
                return self.graph[p]
        else:
            if p[0] in self.graph and p[1] in self.graph:
                return self.graph[p[0]].intersection(self.graph[p[1]])
        return set()

    def __str__(self):
        res = ""
        points = list(self.graph.keys())
        points.sort(key=lambda p: (p.x, p.y))
        for point in points:
            res += "\n" + str(point) + ": "
            for edge in self.graph[point]:
                res += str(edge) + ", "
        return res

    def __repr__(self):
        return self.__str__()


class PolygonGraph(Graph):
    """
    The input must be a list of polygons, where each polygon is a list of
    in-order (clockwise or counter clockwise) Points. If only one polygon,
    it must still be a list in a list, i.e. [[Point(0,0), Point(2,0),
    Point(2,1)]].

    *polygons* dictionary: key is a integer polygon ID and values are the
    edges that make up the polygon. Note only polygons with 3 or more Points
    will be classified as a polygon. Non-polygons like just one Point will be
    given a polygon ID of -1 and not maintained in the dict.

    Wall and obstacles: the wall is the polygon with pid=0. All other polygons
    are obstacles and should be within the wall. The exterior of the wall and
    the interiors of all obstacles are infeasible for the robot.

    Edge direction: follow the direction of an edge, the infeasible area should
    be on the righthand side.
    """

    def __init__(self, polygons):
        self.graph = defaultdict(set)
        self.edges = set()
        self.polygon_edges = defaultdict(set)
        self.polygon_vertices = defaultdict(list)
        self.polygons = []
        pid = 0
        for polygon in polygons:
            while polygon[0] == polygon[-1] and len(polygon) > 1:
                polygon.pop()
            if len(polygon) == 2:
                print(
                    "len(polygon) should not be 2, edge obstacle are currently not allowed."
                )
                continue
            elif len(polygon) == 1:
                for point in polygon:
                    point.polygon_id = pid
                    # Currently, the single point is not added to polygon_vertices
                    self.add_point(point)
            else:
                # But modifying an object that affects its hash or equality while it's in a set can lead to undefined behavior.
                current_edges = []
                for i, point in enumerate(polygon):
                    sibling_point = polygon[(i + 1) % len(polygon)]
                    edge = Edge(point, sibling_point)
                    if len(polygon) > 2:
                        point.polygon_id = pid
                        sibling_point.polygon_id = pid
                        self.polygon_edges[pid].add(edge)
                        self.polygon_vertices[pid].append(point)
                        current_edges.append(edge)
                    self.add_edge(edge)

                # Make sure the infeasible area is on the righthand side of each edge looking from p1 to p2
                # If not, flip p1 and p2 of the edge
                mid_point = (current_edges[0].p1 + current_edges[0].p2) / 2
                dir = (
                    eps
                    * (current_edges[0].p2 - current_edges[0].p1).to_vec()
                    / current_edges[0].length()
                )
                dir = [
                    dir[1],
                    -dir[0],
                    # The y axis is after x axis in pygame, thus this rotation in counterclockwise 90deg.
                ]
                test_point = mid_point + Point.from_vec(dir)
                if polygon_crossing(test_point, current_edges):
                    # print("CounterClockwise")
                    for edge in current_edges:
                        edge.flip()
                # else:
                #     print("Clockwise")

                # For the first polygon, which is the wall, the edge direction is flip as the exterior is the boundary side
                if pid == 0:
                    for edge in current_edges:
                        edge.flip()
            self.polygons.append(polygon)
            pid += 1


class ChainGraph(Graph):
    def __init__(self):
        self.graph = defaultdict(set)
        self.edges = set()
        self.chains = defaultdict(Chain)

    def new_chain(self, chain_id, vertices, edges):
        assert (
            not chain_id in self.chains
        ), f"new_chain: Chain id {chain_id} already in chains"
        self.chains[chain_id] = Chain(chain_id, set(vertices), set(edges))
        self.add_points(vertices)
        self.add_edges(edges)
        self.start_and_end(chain_id)

    def add_to_chain(self, chain_id, vertices, edges):
        assert (
            chain_id in self.chains
        ), f"add_to_chain: Chain id {chain_id} not in chains"
        self.chains[chain_id].add_edges(edges)
        self.chains[chain_id].add_points(vertices)
        self.add_edges(edges)
        self.start_and_end(chain_id)

    def add_or_new_chain(self, chain_id, vertices, edges):
        if chain_id in self.chains:
            self.add_to_chain(chain_id, vertices, edges)
        else:
            self.new_chain(chain_id, vertices, edges)

    def start_and_end(self, chain_id):
        assert (
            chain_id in self.chains
        ), f"add_to_chain: Chain id {chain_id} not in chains"
        self.chains[chain_id].start = None
        self.chains[chain_id].end = None

        vertices = self.chains[chain_id].vertices
        if len(vertices) == 1:
            self.chains[chain_id].start = list(vertices)[0]
            self.chains[chain_id].end = list(vertices)[0]

        for p in vertices:
            if self.get_next_point(p) in vertices and (
                not self.get_prev_point(p) in vertices
            ):
                self.chains[chain_id].start = p
            if (not self.get_next_point(p) in vertices) and self.get_prev_point(
                p
            ) in vertices:
                self.chains[chain_id].end = p
