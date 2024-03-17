
from pyvisgraph import Point, Edge
from pyvisgraph.visible_vertices import edge_cross_point, edge_distance, ccw, CCW, CW
from numpy import array
from numpy.linalg import norm
from enum import Enum
from dataclasses import dataclass


class Robot():
    def __init__(self, vis_graph, p):
        self.vis_graph = vis_graph
        self.gaps = []
        self.pos = p
        self.gap_count = 0
        self.detect_gaps()
        return

    def detect_gaps(self):
        gap_vertices = self.vis_graph.find_visible(self.pos)
        current_gaps = []
        for v in gap_vertices:
            dir = (v-self.pos).unit_vec()
            next_point = self.vis_graph.graph.get_next_point(v)
            if next_point:
                side = ccw(self.pos, v, next_point)
            else:
                side = 0
            current_gaps.append(Gap(-1, v, side, dir))
        self.associate_gaps(current_gaps)

    def associate_gaps(self, current_gaps, motion=None):
        """Associate new gap sensor results to previous ones (in progress)

        Args:
            current_gaps (_type_): _description_
            motion (_type_, optional): _description_. Defaults to None.
        """
        if not self.gaps:
            for gap in current_gaps:
                gap.id = self.assign_gap_id()
                self.gaps.append(gap)
        print([g.id for g in self.gaps])

    def assign_gap_id(self):
        id = self.gap_count
        self.gap_count += 1
        return id

    def move(self, path_edge):
        events = self.gap_events(path_edge)
        for event in events:
            if event.etype == GapEventType.A:
                self.gaps.append(Gap(self.assign_gap_id(), event.edge.p1, event.edge.side,
                                 (event.edge.p1 - event.edge.p2).unit_vec()))
            elif event.etype == GapEventType.D:
                _gap_vertex = event.edge.p1
                _gap_found = False
                while (not _gap_found) and _gap_vertex:
                    for _count, gap in enumerate(self.gaps):
                        if gap.vertex == _gap_vertex:
                            self.gaps.pop(_count)
                            _gap_found = True
                            break
                    if not _gap_found:
                        if event.edge.side == CCW:
                            _gap_vertex = self.vis_graph.graph.get_prev_point(
                                _gap_vertex)
                        elif event.edge.side == CW:
                            _gap_vertex = self.vis_graph.graph.get_next_point(
                                _gap_vertex)
                        else:
                            raise Exception(f"ERROR: Wrong edge side value. side should be {
                                            CCW} or {CW}, but is {event.edge.side}")
            elif event.etype == GapEventType.S:
                _gap_vertex = event.edge.p1
                _gap_found = False
                while (not _gap_found) and _gap_vertex:
                    for _count, gap in enumerate(self.gaps):
                        if gap.vertex == _gap_vertex:
                            gap.vertex = event.edge.p1
                            dual_edge = event.edge.dual
                            self.gaps.append(Gap(self.assign_gap_id(
                            ), dual_edge.p1, dual_edge.side, (event.edge.p1 - event.edge.p2).unit_vec()))
                            _gap_found = True
                            break
                    if not _gap_found:
                        if event.edge.side == CCW:
                            _gap_vertex = self.vis_graph.graph.get_prev_point(
                                _gap_vertex)
                        elif event.edge.side == CW:
                            _gap_vertex = self.vis_graph.graph.get_next_point(
                                _gap_vertex)
                        else:
                            raise Exception(f"ERROR: Wrong edge side value. side should be {
                                            CCW} or {CW}, but is {event.edge.side}")

        print([g.id for g in self.gaps])

    def gap_events(self, path_edge):
        events = []
        for edge in self.vis_graph.bitcomp.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:  # path line contains the starting but not the ending point
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side * edge.side == 1:
                    events.append(GapEvent(p, edge, GapEventType.M))
                elif _side * edge.side == -1:
                    events.append(GapEvent(p, edge, GapEventType.S))
                else:
                    raise Exception(
                        f"ERROR: _side * edge.side should be 1 or -1, but is {_side * edge.side}")

        for edge in self.vis_graph.inflx.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side * edge.side == 1:
                    events.append(GapEvent(p, edge, GapEventType.A))
                elif _side * edge.side == -1:
                    events.append(GapEvent(p, edge, GapEventType.D))
                else:
                    raise Exception(
                        f"ERROR: _side * edge.side should be 1 or -1, but is {_side * edge.side}")

        events.sort(key=lambda event: edge_distance(event.pos, path_edge.p1))
        for event in events:
            print(event.etype.name, end=" ")
        print()
        return events


class Gap():
    __slots__ = ("id", "vertex", "side", "dir")

    def __init__(self, id, vertex, side, dir):
        assert isinstance(id, int)
        assert isinstance(vertex, Point)
        assert (norm(dir)-1) > -1e-10 and (norm(dir)-1) < 1e-10
        self.id = id
        self.vertex = vertex
        self.dir = dir
        self.side = side


# class syntax
class GapEventType(Enum):
    A = 0
    D = 1
    M = 2
    S = 3


@dataclass
class GapEvent:
    pos: Point
    edge: Edge
    etype: GapEventType
