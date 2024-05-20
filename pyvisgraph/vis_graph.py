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

from timeit import default_timer
from sys import stdout, version_info
from multiprocessing import Pool
from tqdm import tqdm
from warnings import warn

from pyvisgraph.classes import Edge
from pyvisgraph.graph import PolygonGraph, ChainGraph, Graph
from pyvisgraph.shortest_path import shortest_path
from pyvisgraph.visible_vertices import (
    bitangent_lines,
    point_in_polygon,
    point_in_wall,
    point_valid,
    convex_chain,
    bitangent_complement,
    inflection_lines,
    extention_lines,
    edge_distance,
    intersect_point,
    on_segment,
    ccw,
)
from pyvisgraph.visible_vertices import closest_point

PYTHON3 = version_info[0] == 3
if PYTHON3:
    xrange = range
    import pickle
else:
    import cPickle as pickle


class VisGraph(object):

    def __init__(self):
        self.graph = None
        self.visgraph = None
        self.conv_chains = None
        self.bitcomp = None
        self.inflx = None
        self.input = None

    def load(self, filename):
        """Load obstacle graph and visibility graph."""
        with open(filename, "rb") as load:
            self.graph, self.visgraph, self.input, self.conv_chains, self.bitcomp = (
                pickle.load(load)
            )

    def save(self, filename):
        """Save obstacle graph and visibility graph."""
        self.save_csv(filename)
        with open(filename, "wb") as output:
            pickle.dump(
                (self.graph, self.visgraph, self.input, self.conv_chains, self.bitcomp),
                output,
                -1,
            )
    
    def save_csv(self,filename):
        with open(filename + ".csv", "w") as file:
            for chain_id, chain in self.conv_chains.chains.items():
                p = chain.start
                while True:
                    # record chain_id, side, other chain_id, other side
                    for bitcomp in self.bitcomp[p]:
                        dual = bitcomp.dual
                        file.write(
                            f"{chain_id},{bitcomp.side},{dual.p1.chain_id},{dual.side}\n"
                        )
                    if p == chain.end:
                        break
                    else:
                        p = self.conv_chains.get_next_point(p)

    def build(self, input, workers=1, status=True):
        """Build visibility graph based on a list of polygons.

        The input must be a list of polygons, where each polygon is a list of
        in-order (clockwise or counter clockwise) Points. It only one polygon,
        it must still be a list in a list, i.e. [[Point(0,0), Point(2,0),
        Point(2,1)]].
        Take advantage of processors with multiple cores by setting workers to
        the number of subprocesses you want. Defaults to 1, i.e. no subprocess
        will be started.
        Set status=False to turn off the statusbar when building.
        """
        self.input = input  # copy of input to save the raw polygon info
        self.graph = PolygonGraph(input)
        self.visgraph = Graph()
        self.conv_chains = ChainGraph()
        self.bitcomp = Graph()
        self.inflx = Graph()
        self.extlines = Graph()

        points = self.graph.get_points()
        batch_size = 10

        if workers == 1:
            for batch in tqdm(
                [
                    points[i : i + batch_size]
                    for i in xrange(0, len(points), batch_size)
                ],
                disable=not status,
            ):
                for edge in _bitangent_lines(self.graph, batch):
                    self.visgraph.add_edge(edge)
            _conv_chain(self.graph, self.conv_chains)
            _bit_comp(self.graph, self.visgraph, self.bitcomp)
            _inflx_lines(self.graph, self.conv_chains, self.inflx)
            _ext_lines(self.graph, self.conv_chains, self.extlines)

        else:
            pool = Pool(workers)
            batches = [
                (self.graph, points[i : i + batch_size])
                for i in xrange(0, len(points), batch_size)
            ]

            results = list(
                tqdm(
                    pool.imap(_bitangent_lines_wrapper, batches),
                    total=len(batches),
                    disable=not status,
                )
            )
            for result in results:
                for edge in result:
                    self.visgraph.add_edge(edge)

    def find_bitangent(self, point):
        """Find vertices visible from point."""
        return bitangent_lines(point, self.graph)

    def update(self, points, origin=None, destination=None):
        """Update visgraph by checking visibility of Points in list points."""

        for p in points:
            for v in bitangent_lines(
                p, self.graph, origin=origin, destination=destination
            ):
                self.visgraph.add_edge(Edge(p, v))

    def shortest_path(self, origin, destination):
        """Find and return shortest path between origin and destination.

        Will return in-order list of Points of the shortest path found. If
        origin or destination are not in the visibility graph, their respective
        visibility edges will be found, but only kept temporarily for finding
        the shortest path.
        """

        origin_exists = origin in self.visgraph
        dest_exists = destination in self.visgraph
        if origin_exists and dest_exists:
            return shortest_path(self.visgraph, origin, destination)
        orgn = None if origin_exists else origin
        dest = None if dest_exists else destination
        add_to_visg = PolygonGraph([])
        if not origin_exists:
            for v in bitangent_lines(origin, self.graph, destination=dest):
                add_to_visg.add_edge(Edge(origin, v))
        if not dest_exists:
            for v in bitangent_lines(destination, self.graph, origin=orgn):
                add_to_visg.add_edge(Edge(destination, v))
        return shortest_path(self.visgraph, origin, destination, add_to_visg)

    def point_in_polygon(self, point):
        """Return polygon_id if point in a polygon, -1 otherwise."""

        return point_in_polygon(point, self.graph)

    def point_in_wall(self, point):
        """Return True if point in a polygon 0 (wall), False otherwise."""
        return point_in_wall(point, self.graph)

    def point_valid(self, point):
        """Return True if the point p is interior to polygon 0 (wall) and not interior to other polygons, False otherwise."""
        return point_valid(point, self.graph)

    def closest_point(self, point, polygon_id, length=0.001):
        """Return closest Point outside polygon from point.

        Note method assumes point is inside the polygon, no check is
        performed.
        """

        return closest_point(point, self.graph, polygon_id, length)


def _bitangent_lines_wrapper(args):
    try:
        return _bitangent_lines(*args)
    except KeyboardInterrupt:
        pass


def _bitangent_lines(graph, points):
    visible_edges = []
    for p1 in points:
        for p2 in bitangent_lines(p1, graph, scan="half"):
            visible_edges.append(Edge(p1, p2))
    return visible_edges


def _conv_chain(graph, conv_chain):
    convex_chain(graph, conv_chain)


def _bit_comp(graph, visgraph, bitcomp):
    bitangent_complement(graph, visgraph, bitcomp)


def _inflx_lines(graph, conv_chain, inflx):
    inflection_lines(graph, conv_chain, inflx)


def _ext_lines(graph, conv_chain, extlines):
    extention_lines(graph, conv_chain, extlines)
