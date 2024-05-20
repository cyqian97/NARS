from copy import deepcopy
from collections import defaultdict


class UGraph(defaultdict):
    def __init__(self):
        super().__init__(set)

    def add_edge(self, v1, v2):
        self[v1].update([v2])
        self[v2].update([v1])

    def exist_edge(self, v1, v2):
        return v2 in self[v1]


class MatchingGraph:
    def __init__(self, node_num):
        """Matching graph data structure"""
        self.node_num = node_num
        self.num_p = {}  # The remaining positive connector numbers of nodes
        self.num_n = {}  # The remaining negative connector numbers of nodes
        # Current edges. {(ID1,side1):[(ID2,side2),(ID2,side3)]}. Must also include {(ID2,side2):(ID1,side1)}
        self.edges = UGraph()
        self.convex_connect = UGraph()
        self.shortest_connect = UGraph()

    def copy(self):
        return deepcopy(self)

    def __keys_asserts__(self, keys):
        assert isinstance(keys, tuple) and len(keys) == 2
        ID, side = keys
        assert ID < self.node_num
        assert (
            side == 1 or side == -1
        ), f"__getitem__: ERROR: side must be +1 or -1, but is {side}"
        return ID, side

    def __getitem__(self, keys):
        ID, side = self.__keys_asserts__(keys)
        if side == 1 and ID in self.num_p:
            return self.num_p[ID]
        elif side == -1 and ID in self.num_n:
            return self.num_n[ID]
        else:
            return 0

    def __setitem__(self, keys, value):
        ID, side = self.__keys_asserts__(keys)
        assert isinstance(value, int) and value >= 0
        if side == 1:
            self.num_p[ID] = value
        else:
            self.num_n[ID] = value

    def add_node(self, ID, n_p, n_n):
        assert (
            isinstance(ID, int)
            and ID >= 0
            and ID not in self.num_p
            and ID not in self.num_n
        )
        self.num_p[ID] = n_p
        self.num_n[ID] = n_n
        return

    def feasible_ids(self, ID1, side1, side2):
        return [
            ID2
            for ID2 in range(self.node_num)
            if self.can_connect(ID1, side1, ID2, side2)
        ]
    
    def add_convex_connect(self,v1,v2):
        self.convex_connect.add_edge(v1,v2)
        self.shortest_connect.add_edge(v1,v2)

    def add_shortest_connect(self,v1,v2):
        self.shortest_connect.add_edge(v1,v2)


    def connect(self, ID1, side1, ID2, side2):
        assert ID1 != ID2, f"connect: ERROR: ID1 is equal to ID2, ID1=ID2={ID1}"
        if self.can_connect(ID1, side1, ID2, side2):
            self[ID1, side1] -= 1
            self[ID2, side2] -= 1
            self.edges.add_edge((ID1, side1),(ID2, side2))

            # update convex connect
            if side1 == 1 and side2 == -1:
                self.add_convex_connect((ID1, 1),(ID2, -1))
                for ID0, side0 in self.convex_connect[ID1, -1]:
                    assert side0 == 1
                    self.add_convex_connect((ID0, 1),(ID2, -1))
            elif side1 == -1 and side2 == 1:
                self.add_convex_connect((ID2, 1),(ID1, -1))
                for ID0, side0 in self.convex_connect[ID2, -1]:
                    assert side0 == 1
                    self.add_convex_connect((ID0, 1),(ID1, -1))
            # update shortest connect
            elif side1 == 1 and side2 == 1:
                pass
            elif side1 == 1 and side2 == 1:
                pass

            return True
        else:
            return False

    def can_connect(self, ID1, side1, ID2, side2):
        if (
            ID1 != ID2
            and self[ID1, side1] > 0
            and self[ID2, side2] > 0
            and (ID2, side2) not in self.edges[ID1, side1]
        ):
            return True
        else:
            return False

    def next_id(self, ID):
        """Get the next node ID in the counterclockwise direction"""
        return (ID + 1) % self.node_num

    def exist_edge(self, v1, v2):
        return v2 in self.edges[v1]

    def exist_convex_path(self, ID1, ID2):
        """Check it there is a convex path going counterclockwise from ID1,+1 to node ID2,-1"""
        if ID1 == ID2:
            return True
        elif self.convex_connect.exist_edge((ID1, 1), (ID2, -1)):
            return True
        return False

    def exist_shortest_path(self, ID1, side1, ID2, side2, ID3, ID4):
        """Check it there is a shortest path going from ID1,side1 to node ID2, side while touching convex curves between ID3 and ID4 are allowed"""
        return False

    def all_edges(self):
        """all_edges get all edges in self.edges"""
        return [
            (ID, 1, *pairs)
            for ID in range(self.node_num)
            for pairs in self.edges[ID, 1]
            if pairs[0] > ID
        ] + [
            (*pairs, ID, -1)
            for ID in range(self.node_num)
            for pairs in self.edges[ID, -1]
            if pairs[0] > ID
        ]

    def check_matching(self):
        edges = self.all_edges()
        for i in range(len(edges) - 1):
            edge1 = edges[i]
            for j in range(i + 1, len(edges)):
                edge2 = edges[j]
                id_in = check_cross(edge1[0], edge1[2], edge2[0], edge2[2])
                if id_in == edge2[0] and not self.exist_convex_path(id_in, edge1[2]):
                    return False
                elif id_in == edge2[2] and not self.exist_convex_path(edge1[0], id_in):
                    return False
        return True

    def __str__(self):
        s = "\n"
        for edge in self.all_edges():
            s += f"{edge[0]}, {edge[1]}\t => {edge[2]}, {edge[3]}\n"
        return s


def is_cw(ID1, ID2, ID3):
    """Check if ID1=>ID2=>ID3 is counterclockwise order in a cyclic list.
    For example in list [1,2,3,4,5], 1=>3=>5, 3=>5=>1, and 5=>1=>3 are counterclockwise.
    """
    # TODO: add side check into this fucntion
    assert not (ID1 == ID2 and ID2 == ID3), f"is_cw: ERROR: all three ids are the same!"
    return (
        (ID1 <= ID2 and ID2 < ID3)
        or (ID1 < ID2 and ID2 <= ID3)
        or (ID2 <= ID3 and ID3 < ID1)
        or (ID2 < ID3 and ID3 <= ID1)
        or (ID3 <= ID1 and ID1 < ID2)
        or (ID3 < ID1 and ID1 <= ID2)
    )


def check_cross(ID1, ID2, ID3, ID4):
    """check_cross checks if edge ID1-ID2 crosses edge ID3-ID4

    Returns:
        int: if cross, return ID = ID3/ID4 s.t. is_cw(ID1,ID,ID2), else return -1
    """
    # TODO: add side check into this fucntion
    if ID1 == ID3 or ID1 == ID4 or ID2 == ID3 or ID2 == ID4:
        return -1
    elif is_cw(ID1, ID3, ID2) and not is_cw(ID1, ID4, ID2):
        return ID3
    elif is_cw(ID1, ID4, ID2) and not is_cw(ID1, ID3, ID2):
        return ID4
    else:
        return -1
