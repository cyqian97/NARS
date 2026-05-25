"""Environment — backend API for building and querying the geometric structures."""

import glob
import json
import os
import re

from pyvisgraph import Point, Edge
from pyvisgraph.vis_graph import VisGraph
from pyvisgraph.visible_vertices import ccw, edge_cross_point, edge_distance, CCW, CW
from backend.gap import GapEvent, GapEventType


class Environment:
    """Owns the geometric structures for a polygon environment.

    After calling build(), the following read-only properties expose each graph:
        polygon_graph    -- directed polygon boundary (PolygonGraph)
        visibility_graph -- bitangent edges between vertices (Graph)
        convex_chains    -- maximal convex vertex chains (ChainGraph)
        bitangent_comp   -- complement rays that trigger S/M events (Graph)
        inflection       -- inflection rays that trigger A/D events (Graph)
        extension        -- extension rays that trigger N/P events (Graph)
    """

    def __init__(self):
        self._vis_graph = VisGraph()
        self._built = False

    # ------------------------------------------------------------------
    # Build / persistence
    # ------------------------------------------------------------------

    def build(self, polygons, status=True):
        """Build all geometric graphs from a list of polygons.

        The first polygon is the outer wall; all others are obstacles.
        Each polygon is a list of Points in order (CW or CCW).
        """
        self._vis_graph.build(polygons, status=status)
        self._built = True

    def save(self, path):
        """Save polygon list to a JSON file."""
        polygons = self._vis_graph.graph.polygons
        data = {"polygons": [[[p.x, p.y] for p in poly] for poly in polygons]}
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path):
        """Load polygon list from a JSON file and rebuild."""
        with open(path, "r") as f:
            data = json.load(f)
        polygons = [[Point(p[0], p[1]) for p in poly] for poly in data["polygons"]]
        self.build(polygons, status=False)

    @staticmethod
    def latest_save(directory="./environments"):
        """Return the path of the most recently created JSON save, or None."""
        pattern = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.json"
        files = glob.glob(os.path.join(directory, "*.json"))
        matches = [f for f in files if re.search(pattern, os.path.basename(f))]
        return max(matches, key=os.path.getctime) if matches else None

    # ------------------------------------------------------------------
    # Geometric queries
    # ------------------------------------------------------------------

    def find_visible_vertices(self, pos):
        """Return all polygon vertices visible (bitangent) from pos."""
        return self._vis_graph.find_visible_vertices(pos)

    def point_valid(self, point):
        """True if point is inside the wall and outside all obstacles."""
        return self._vis_graph.point_valid(point)

    def point_in_polygon(self, point):
        """Return polygon_id if point is inside a polygon, -1 otherwise."""
        return self._vis_graph.point_in_polygon(point)

    def point_in_wall(self, point):
        return self._vis_graph.point_in_wall(point)

    def closest_point(self, point, polygon_id, length=0.001):
        return self._vis_graph.closest_point(point, polygon_id, length)

    def shortest_path(self, origin, destination):
        """Return shortest obstacle-free path as an ordered list of Points."""
        return self._vis_graph.shortest_path(origin, destination)

    def is_edge_valid(self, edge, work_polygon=None):
        """True if edge does not cross any polygon boundary or work_polygon edges."""
        for polygon in self._vis_graph.graph.polygons:
            _l = len(polygon)
            for i, pt in enumerate(polygon):
                if edge_cross_point(edge, Edge(pt, polygon[(i + 1) % _l])):
                    return False
        if work_polygon and len(work_polygon) > 2:
            for i in range(len(work_polygon) - 2):
                if edge_cross_point(edge, Edge(work_polygon[i], work_polygon[i + 1])):
                    return False
        return True

    def gap_events_along(self, path_edge):
        """Return all gap events along path_edge, sorted by distance from p1.

        Intersects path_edge with all three critical-event graphs and classifies
        each crossing as A/D/S/M/N/P based on which side the robot came from.
        """
        events = []

        # Bitangent complement: triggers Merge (M) and Split (S)
        for edge in self._vis_graph.bitangent_comp.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                side = _approach_side(path_edge, edge)
                if side * edge.side == 1:
                    events.append(GapEvent(p, edge, GapEventType.M))
                elif side * edge.side == -1:
                    events.append(GapEvent(p, edge, GapEventType.S))
                else:
                    raise ValueError(f"Unexpected side product: {side * edge.side}")

        # Inflection lines: triggers Appear (A) and Disappear (D)
        for edge in self._vis_graph.inflection.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                side = _approach_side(path_edge, edge)
                if side * edge.side == 1:
                    events.append(GapEvent(p, edge, GapEventType.A))
                elif side * edge.side == -1:
                    events.append(GapEvent(p, edge, GapEventType.D))
                else:
                    raise ValueError(f"Unexpected side product: {side * edge.side}")

        # Extension lines: triggers Proceed (N) and Retreat (P)
        for edge in self._vis_graph.extension.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                side = _approach_side(path_edge, edge)
                if side == -1:
                    events.append(GapEvent(p, edge, GapEventType.N))
                elif side == 1:
                    events.append(GapEvent(p, edge, GapEventType.P))
                else:
                    raise ValueError(f"Unexpected side: {side}")

        events.sort(key=lambda e: edge_distance(e.pos, path_edge.p1))
        return events

    # ------------------------------------------------------------------
    # Graph access (read-only properties)
    # ------------------------------------------------------------------

    @property
    def polygon_graph(self):
        return self._vis_graph.graph

    @property
    def visibility_graph(self):
        return self._vis_graph.visibility_graph

    @property
    def convex_chains(self):
        return self._vis_graph.convex_chains

    @property
    def bitangent_comp(self):
        return self._vis_graph.bitangent_comp

    @property
    def inflection(self):
        return self._vis_graph.inflection

    @property
    def extension(self):
        return self._vis_graph.extension


def _approach_side(path_edge, event_edge):
    """Return which side of event_edge the robot was on before crossing.

    Uses the robot's start position (path_edge.p1). If p1 is collinear with
    the event edge, falls back to the end position (path_edge.p2) with sign flip.
    """
    side = ccw(event_edge.p1, event_edge.p2, path_edge.p1)
    if side == 0:
        side = -ccw(event_edge.p1, event_edge.p2, path_edge.p2)
    return side
