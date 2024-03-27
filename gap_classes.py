
from pyvisgraph import Point, Edge
from numpy.linalg import norm
from enum import Enum
from dataclasses import dataclass

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
    N = 4
    P = 5

def is_tracking_events(event):
    return event.etype in [GapEventType.P,GapEventType.N]

@dataclass
class GapEvent:
    pos: Point
    edge: Edge
    etype: GapEventType

@dataclass
class EventInfo:
    etype: GapEventType
    gap1_id: int # closer gap's id
    gap2_id: int # further gap's id
    