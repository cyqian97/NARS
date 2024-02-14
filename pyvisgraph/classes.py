from math import sqrt
from numpy import array


class Point(object):
    __slots__ = ("x", "y", "polygon_id", "cov_chain_id")

    def __init__(self, x, y, polygon_id=-1, cov_chain_id=-1):
        self.x = float(x)
        self.y = float(y)
        self.polygon_id = polygon_id
        self.cov_chain_id = cov_chain_id

    @classmethod
    def from_vec(cls, vec):
        return cls(vec[0], vec[1])

    def to_vec(self):
        return array([self.x, self.y])

    def __eq__(self, point):
        return point and self.x == point.x and self.y == point.y

    def __ne__(self, point):
        return not self.__eq__(point)

    def __lt__(self, point):
        """This is only needed for shortest path calculations where heapq is
        used. When there are two points of equal distance, heapq will
        instead evaluate the Points, which doesnt work in Python 3 and
        throw a TypeError."""
        return hash(self) < hash(point)

    def __str__(self):
        return "(%.2f, %.2f)" % (self.x, self.y)

    def __hash__(self):
        return self.x.__hash__() ^ self.y.__hash__()

    def __repr__(self):
        return "Point(%.2f, %.2f)" % (self.x, self.y)

    def __call__(self):
        return (self.x, self.y)

    def __add__(self, other):
        if isinstance(other, Point):
            return Point((self.x + other.x), (self.y + other.y))
        else:
            raise TypeError("Both arguments must be Point")

    def __sub__(self, other):
        if isinstance(other, Point):
            return Point((self.x - other.x), (self.y - other.y))
        else:
            raise TypeError("Both arguments must be Point")

    def __mul__(self, num):
        return Point(self.x * num, self.y * num)

    def __truediv__(self, num):
        return Point(self.x / num, self.y / num)


class Edge(object):
    __slots__ = ("p1", "p2")

    def __init__(self, point1, point2):
        self.p1 = point1
        self.p2 = point2

    def get_adjacent(self, point):
        if point == self.p1:
            return self.p2
        return self.p1

    def length(self):
        return sqrt((self.p2.x - self.p1.x) ** 2 + (self.p2.y - self.p1.y) ** 2)
    
    def flip(self):
        p = self.p1
        self.p1 = self.p2
        self.p2 = p

    def __contains__(self, point):
        return self.p1 == point or self.p2 == point

    def __eq__(self, edge):
        if self.p1 == edge.p1 and self.p2 == edge.p2:
            return True
        if self.p1 == edge.p2 and self.p2 == edge.p1:
            return True
        return False

    def __ne__(self, edge):
        return not self.__eq__(edge)

    def __str__(self):
        return "({}, {})".format(self.p1, self.p2)

    def __repr__(self):
        return "Edge({!r}, {!r})".format(self.p1, self.p2)

    def __hash__(self):
        return self.p1.__hash__() ^ self.p2.__hash__()
