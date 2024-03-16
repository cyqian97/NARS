
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
            dir = (v-self.pos).to_vec()
            dir = dir/norm(dir)
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

    def gap_events(self, path_edge):
        events = gap_events(
            path_edge, self.vis_graph.bitcomp, self.vis_graph.inflx)
        for event in events:
            if event[2] == 'a':
                gap = Gap(self.assign_gap_id(),event[1].p1,event[1].side)


    def gap_events(self, path_edge):
        events = []
        for edge in self.vis_graph.bitcomp.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:  # path line contains the starting but not the ending point
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side * edge.side == 1:
                    events.append((p, edge, 'm'))
                elif _side * edge.side == -1:
                    events.append((p, edge, 's'))
                else:
                    raise Exception(
                        f"ERROR: _side * edge.side should be 1 or -1, but is {_side * edge.side}")

        for edge in self.vis_graph.inflx.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side * edge.side == 1:
                    events.append((p, edge, 'a'))
                elif _side * edge.side == -1:
                    events.append((p, edge, 'd'))
                else:
                    raise Exception(
                        f"ERROR: _side * edge.side should be 1 or -1, but is {_side * edge.side}")

        events.sort(key=lambda p: edge_distance(p[0], path_edge.p1))
        for p in events:
            print(p[2], end=" ")
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
    APP = 0
    DIS = 1
    MER = 2
    SPL = 3


@dataclass
class GapEvent:
    pos: Point
    edge: Edge
    etype: GapEventType