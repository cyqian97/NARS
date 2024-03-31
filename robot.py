
from pyvisgraph import Point, Edge, edge_cross_point, edge_distance, ccw, CCW, CW
from algorithm import *
from gap_classes import *


class Robot():
    def __init__(self, vis_graph, p):
        self.vis_graph = vis_graph
        self.gaps = []
        self.pos = p
        self.gap_count = 0
        self.detect_gaps()
        self.alg = algorithm_1(self.gaps)
        print(self.alg)
        return

    def detect_gaps(self):
        gap_vertices = self.vis_graph.find_bitangent(self.pos)
        current_gaps = []
        for v in gap_vertices:
            dir = (v-self.pos).unit_vec()
            side = 0  # for point obstacle, the gap has no side, thus side = 0
            next_point = self.vis_graph.graph.get_next_point(v)
            if next_point:
                side = ccw(self.pos, v, next_point)
            current_gaps.append(Gap(-1, v, side, dir))
        for gap in current_gaps:
            gap.id = self.assign_gap_id()
            self.gaps.append(gap)
        print([g.id for g in self.gaps])

    def assign_gap_id(self):
        id = self.gap_count
        self.gap_count += 1
        return id

    def update_dir(self):
        for gap in self.gaps:
            gap.dir = (gap.vertex-self.pos).unit_vec()

    def move(self, path_edge):
        print("\n====================")
        print(f"Move: {path_edge}")
        events = self.gap_events(path_edge)
        event_info = None
        for i, event in enumerate(events):
            if event.etype == GapEventType.N:
                if event.edge.side == CCW:
                    gap_count, gap = self.find_gap(event.edge.p1)
                    gap.vertex = self.vis_graph.graph.get_next_point(
                        event.edge.p1)
                elif event.edge.side == CW:
                    gap_count, gap = self.find_gap(
                        self.vis_graph.graph.get_prev_point(event.edge.p1))
                    gap.vertex = event.edge.p1
                else:
                    raise Exception(f"event.edge.side must be {CCW} or {CW}, but is {event.edge.side}")
                # print(f"Gap #{gap.id} proceed")
            elif event.etype == GapEventType.P:
                if event.edge.side == CW:
                    gap_count, gap = self.find_gap(event.edge.p1)
                    gap.vertex = self.vis_graph.graph.get_prev_point(
                        event.edge.p1)
                elif event.edge.side == CCW:
                    gap_count, gap = self.find_gap(
                        self.vis_graph.graph.get_next_point(event.edge.p1))
                    gap.vertex = event.edge.p1
                else:
                    raise Exception(f"event.edge.side must be {CCW} or {CW}, but is {event.edge.side}")
                # print(f"Gap #{gap.id} retreat")
            elif event.etype == GapEventType.A:
                _gap = Gap(self.assign_gap_id(), event.edge.p1, event.edge.side,
                           (event.edge.p1 - event.edge.p2).unit_vec())
                self.gaps.append(_gap)
                event_info = EventInfo(event.etype,_gap.id,None)
                print(f"Event {i}: Gap #{_gap.id} appeared")
            elif event.etype == GapEventType.D:
                gap_count, gap = self.find_gap(event.edge.p1)
                event_info = EventInfo(event.etype,gap.id,None)
                print(f"Event {i}: Gap #{gap.id} disappeared")
                self.gaps.pop(gap_count)
            elif event.etype == GapEventType.S:
                gap_count, gap = self.find_gap(event.edge.p1)
                # gap.vertex = event.edge.p1
                dual_edge = event.edge.dual
                _gap = Gap(self.assign_gap_id(),
                           dual_edge.p1, -1*dual_edge.side, (event.edge.p1 - event.edge.p2).unit_vec())
                self.gaps.append(_gap)
                event_info = EventInfo(event.etype,gap.id,_gap.id)
                print(f"Event {i}: Gap #{gap.id} split into gap #{_gap.id}")
            elif event.etype == GapEventType.M:
                gap_count, gap = self.find_gap(event.edge.p1)
                # gap.vertex = event.edge.p1
                dual_edge = event.edge.dual
                dual_gap_count, dual_gap = self.find_gap(dual_edge.p1)
                event_info = EventInfo(event.etype,gap.id,dual_gap.id)
                print(f"Event {i}: Gap #{dual_gap.id} merged into gap #{gap.id}")
                self.gaps.pop(dual_gap_count)
            
            self.pos = event.pos
            self.update_dir()
            if not is_tracking_events(event):
                self.alg(event_info)
                print(self.alg)
        
            
        self.pos = path_edge.p2
        self.update_dir()
        print("Gap Sensor: ", end="")
        print([g.id for g in self.gaps])

    def find_gap(self, event_vertex):
        for gap_count, gap in enumerate(self.gaps):
            if gap.vertex == event_vertex:
                return gap_count, gap
        raise Exception(f"ERROR: Gap not found!")

        # if not gap_side:
        #     gap_side = event_edge.side
        # gap_vertex = event_edge.p1
        # while gap_vertex:
        #     for gap_count, gap in enumerate(self.gaps):
        #         if gap.vertex == gap_vertex and gap.side == gap_side:
        #             return gap_count, gap
        #     if event_edge.side == CCW:
        #         gap_vertex = self.vis_graph.graph.get_prev_point(
        #             gap_vertex)
        #     elif event_edge.side == CW:
        #         gap_vertex = self.vis_graph.graph.get_next_point(
        #             gap_vertex)
        #     else:
        #         raise Exception(f"ERROR: Wrong edge side value. side should be {
        #                         CCW} or {CW}, but is {event_edge.side}")
        # raise Exception(f"ERROR: Gap not found!")

    def gap_events(self, path_edge):
        events = []
        for edge in self.vis_graph.bitcomp.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:  # path line contains the starting but not the ending point
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side == 0:
                    _side = - ccw(edge.p1, edge.p2, path_edge.p2)
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
                if _side == 0:
                    _side = - ccw(edge.p1, edge.p2, path_edge.p2)
                if _side * edge.side == 1:
                    events.append(GapEvent(p, edge, GapEventType.A))
                elif _side * edge.side == -1:
                    events.append(GapEvent(p, edge, GapEventType.D))
                else:
                    raise Exception(
                        f"ERROR: _side * edge.side should be 1 or -1, but is {_side * edge.side}")

        for edge in self.vis_graph.extlines.get_edges():
            p = edge_cross_point(path_edge, edge)
            if p and p != path_edge.p2:
                _side = ccw(edge.p1, edge.p2, path_edge.p1)
                if _side == 0:
                    _side = - ccw(edge.p1, edge.p2, path_edge.p2)
                if _side == -1:
                    events.append(GapEvent(p, edge, GapEventType.N))
                elif _side == 1:
                    events.append(GapEvent(p, edge, GapEventType.P))
                else:
                    raise Exception(
                        f"ERROR: _side must be 1 or -1, but is {_side}")

        events.sort(key=lambda event: edge_distance(event.pos, path_edge.p1))
        print("Events summary: " ,end = "")
        for event in events:
            print(event.etype.name, end=" ")
        print()
        return events

