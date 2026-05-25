from pyvisgraph import Point, Edge
from numpy.linalg import norm
from enum import Enum
from dataclasses import dataclass


class Gap:
    __slots__ = ("id", "vertex", "side", "dir")

    def __init__(self, id, vertex, side, dir):
        assert isinstance(id, int)
        assert isinstance(vertex, Point)
        assert abs(norm(dir) - 1) < 1e-10
        self.id = id
        self.vertex = vertex
        self.side = side
        self.dir = dir


class GapEventType(Enum):
    A = 0  # Appear
    D = 1  # Disappear
    M = 2  # Merge
    S = 3  # Split
    N = 4  # Proceed (gap vertex advances to next polygon point)
    P = 5  # Retreat (gap vertex retreats to previous polygon point)


def is_tracking_event(event):
    """N and P are tracking events: gap vertex shifts but topology is unchanged."""
    return event.etype in (GapEventType.N, GapEventType.P)


@dataclass
class GapEvent:
    pos: Point    # position along path where event occurs
    edge: Edge    # the critical-event edge that was crossed
    etype: GapEventType


@dataclass
class EventInfo:
    etype: GapEventType
    gap1_id: int   # primary gap
    gap2_id: int   # secondary gap (None for A/D)
