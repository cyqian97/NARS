NODE_NUM = 0 # the total number of nodes

class Node():
    __slots__ = ("id", "num_p", "num_n")

    def __init__(self, id, num_p, num_n):
        """Node class fror matching problem

        Args:
            id (int): node id, start from 1
            num_p (int): number of positive connectors
            num_n (int): number of negative connectors
        """
        self.id = id
        self.num_p = num_p
        self.num_n = num_n
        NODE_NUM+=1

    def __getitem__(self, side):
        if side == 1:
            return self.num_p
        elif side == -1:
            return self.num_n
        else:
            raise Exception(
                f"__getitem__: ERROR: side must be +1 or -1, but is {side}")

    def connected(side):
        if side == 1:
            if self.num_p > 0:
                self.num_p -= 1
            else:
                raise Exception(
                    f"connected: ERROR: no more positive connectors")
        elif side == -1:
            if self.num_n > 0:
                self.num_n -= 1
            else:
                raise Exception(
                    f"connected: ERROR: no more negative connectors")
        else:
            raise Exception(
                f"__getitem__: ERROR: side must be +1 or -1, but is {side}")


class Edge():
    def __init__(n1, side1, n2, side2):
        self.n1 = n1
        self.n2 = n2
        self.side1 = side1
        self.side2 = side2

    def __eq__(self, edge):
        if self.n1 == edge.n1 and self.n2 == edge.n2 and self.side1 == edge.side1 and self.side2 == edge.side2:
            return True
        elif self.n1 == edge.n2 and self.n2 == edge.n1 and self.side1 == edge.side2 and self.side2 == edge.side1:
            return True
        else:
            return False

    def __hash__(self):
        return hash((self.n1, self.side1)) ^ hash((self.n2, self.side2))


def can_connect(n1, side1, n2, side2):
    if n1[side1] > 0 and n2[side2] > 0:
        return True
    else:
        return False


def connect(n1, side1, n2, side2):
    if n1[side1] > 0 and n2[side2] > 0:
        n1.connected(side1)
        n2.connected(side2)
        return Edge(n1, side1, n2, side2)


def is_cw(n1, n2, n3):
    """Check if n1=>n2=>n3 is clockwise order in a cyclic list.
    For example in list [1,2,3,4,5], 1=>3=>5, 3=>5=>1, and 5=>1=>3 are clockwise.
    """
    assert not (n1.id == n2.id and n2.id ==
                n3.id), f"is_cw: ERROR: all three ids are the same!"
    return ((n1 <= n2 and n2 < n3) or (n1 < n2 and n2 <= n3) or
            (n2 <= n3 and n3 < n1) or (n2 < n3 and n3 <= n1) or
            (n3 <= n1 and n1 < n2) or (n3 < n1 and n1 <= n2))


def next_id(node):
    """Get the next node id in the clockwise direction

    Args:
        node (Node): current node
        NODE_NUM (int): the total number of nodes
    """
    return ((node.id - 1) % NODE_NUM)+1


def exist_convex_path(n_p, n_n, NODE_NUM):
    """Check it there is a convex path going clockwise from n1 to n2

    Args:
        n1 (Node): 
        n2 (Node): 
        NODE_NUM (int): the total number of nodes
    """
    next_id = n1.id
    while 
