from pyvisgraph import Edge, ccw, CCW, CW
from backend.gap import Gap, GapEventType, EventInfo, is_tracking_event
from backend.gnt import GNT


class Robot:
    """Robot that detects gaps and processes gap events as it moves.

    pos  -- current Point position
    gaps -- list of currently visible Gap objects
    gnt  -- GNT algorithm instance tracking the gap navigation tree
    """

    def __init__(self, env, pos):
        self.env = env
        self.pos = pos
        self.gaps = []
        self._gap_count = 0
        self._detect_gaps()
        self.gnt = GNT(self.gaps)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def move(self, path_edge):
        """Process all gap events along path_edge and advance position."""
        events = self.env.gap_events_along(path_edge)
        for event in events:
            event_info = self._apply_event(event)
            self.pos = event.pos
            self._update_directions()
            if not is_tracking_event(event):
                self.gnt(event_info)

        self.pos = path_edge.p2
        self._update_directions()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_gaps(self):
        """Find all bitangent vertices from the current position and register them as gaps."""
        graph = self.env.polygon_graph
        for v in self.env.find_visible_vertices(self.pos):
            dir = (v - self.pos).unit_vec()
            side = 0  # point obstacles have no side
            next_point = graph.get_next_point(v)
            if next_point:
                side = ccw(self.pos, v, next_point)
            gap = Gap(self._next_gap_id(), v, side, dir)
            self.gaps.append(gap)

    def _apply_event(self, event):
        """Mutate gap list for one event; return EventInfo for the GNT."""
        graph = self.env.polygon_graph
        etype = event.etype
        edge = event.edge

        if etype == GapEventType.N:
            if edge.side == CCW:
                gap = self._find_gap(edge.p1)
                gap.vertex = graph.get_next_point(edge.p1)
            else:  # CW
                gap = self._find_gap(graph.get_prev_point(edge.p1))
                gap.vertex = edge.p1
            return None

        elif etype == GapEventType.P:
            if edge.side == CW:
                gap = self._find_gap(edge.p1)
                gap.vertex = graph.get_prev_point(edge.p1)
            else:  # CCW
                gap = self._find_gap(graph.get_next_point(edge.p1))
                gap.vertex = edge.p1
            return None

        elif etype == GapEventType.A:
            new_gap = Gap(
                self._next_gap_id(),
                edge.p1,
                edge.side,
                (edge.p1 - edge.p2).unit_vec(),
            )
            self.gaps.append(new_gap)
            return EventInfo(etype, new_gap.id, None)

        elif etype == GapEventType.D:
            gap = self._find_gap(edge.p1)
            self.gaps.remove(gap)
            return EventInfo(etype, gap.id, None)

        elif etype == GapEventType.S:
            gap = self._find_gap(edge.p1)
            dual = edge.dual
            new_gap = Gap(
                self._next_gap_id(),
                dual.p1,
                -1 * dual.side,
                (edge.p1 - edge.p2).unit_vec(),
            )
            self.gaps.append(new_gap)
            return EventInfo(etype, gap.id, new_gap.id)

        elif etype == GapEventType.M:
            gap = self._find_gap(edge.p1)
            dual_gap = self._find_gap(edge.dual.p1)
            self.gaps.remove(dual_gap)
            return EventInfo(etype, gap.id, dual_gap.id)

    def _find_gap(self, vertex):
        for gap in self.gaps:
            if gap.vertex == vertex:
                return gap
        raise RuntimeError(f"Gap with vertex {vertex} not found.")

    def _next_gap_id(self):
        gid = self._gap_count
        self._gap_count += 1
        return gid

    def _update_directions(self):
        for gap in self.gaps:
            gap.dir = (gap.vertex - self.pos).unit_vec()
