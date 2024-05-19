class MatchingGraph():
    def __init__(self):
        """Matching graph data structure
        """
        self.node_num = 0
        self.num_p = {}  # The remaining positive connector numbers of nodes
        self.num_n = {}  # The remaining negative connector numbers of nodes
        # Current edges. {(id1,side1):[(id2,side2),(id2,side3)]}. Must also include {(id2,side2):(id1,side1)}
        self.edges = defaultdict(set)

    def __keys_asserts__(self, keys):
        assert isinstance(keys, tuple) and len(keys) == 2
        id, side = keys
        assert isinstance(id, int) and 0 <= id < self.node_num
        assert side == 1 or side == - \
            1, f"__getitem__: ERROR: side must be +1 or -1, but is {side}"
        return id, side

    def __getitem__(self, keys):
        id, side = self.__keys_asserts__(keys)
        if side == 1:
            return self.num_p[id]
        else:
            return self.num_n[id]

    def __setitem__(self, keys, value):
        id, side = self.__keys_asserts__(keys)
        if side == 1:
            self.num_p[id] = value
        else:
            self.num_n[id] = value

    def add_node(self, id, n_p, n_n):
        assert id not in self.num_p and id not in self.num_n
        self.node_num += 1
        self.num_p[id] = n_p
        self.num_n[id] = n_n
        return

    def connect(self, id1, side1, id2, side2):
        if self.can_connect(id1, side1, id2, side2):
            self[id1, side1] -= 1
            self[id2, side2] -= 1
            self.edges[id1, side1].update([(id2, side2)])
            self.edges[id2, side2].update([(id1, side1)])
            return True
        else:
            return False

    def can_connect(self, id1, side1, id2, side2):
        if self[id1, side1] > 0 and self[id2, side2] > 0 and (id2, side2) not in self.edges[id1, side1]:
            return True
        else:
            return False

    def next_id(self, id):
        """Get the next node id in the clockwise direction
        """
        return id % self.node_num

    def exist_edge(self, id1, side1, id2, side2):
        return (id2, side2) in self.edges[id1, side1]

    def exist_convex_path(self, id1, id2):
        """Check it there is a convex path going clockwise from id1,+1 to node id2,-1
        """
        if (id1 == id2):
            return True
        elif (self.exist_edge(id1, 1, id2, -1)):
            return True
        else:
            id1 = self.next_id(id1)
            while (id1 != id2):
                if self.exist_edge(id1, 1, id2, -1):
                    return self.exist_convex_path(id1, id2)
                else:
                    id1 = self.next_id(id1)
        return False


def is_cw(id1, id2, id3):
    """Check if id1=>id2=>id3 is clockwise order in a cyclic list.
    For example in list [1,2,3,4,5], 1=>3=>5, 3=>5=>1, and 5=>1=>3 are clockwise.
    """
    assert not (id1 == id2 and id2 ==
                id3), f"is_cw: ERROR: all three ids are the same!"
    return ((id1 <= id2 and id2 < id3) or (id1 < id2 and id2 <= id3) or
            (id2 <= id3 and id3 < id1) or (id2 < id3 and id3 <= id1) or
            (id3 <= id1 and id1 < id2) or (id3 < id1 and id1 <= id2))
