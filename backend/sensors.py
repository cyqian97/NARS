from backend.gap import Gap, GapEventTypev
from dataclasses import dataclass

class HGNT:
    __slots__ = ("idmap")

    def __init__(self):
        self._gap_count = 0
        self.idmap = {}

    def first_observation(self, gaps):
        for gap in gaps:
            self.idmap[gap] = self._next_gap_id()

    def first_signal(self):
        return 

    def _next_gap_id(self):
        gid = self._gap_count
        self._gap_count += 1
        return gid
    

class GapNode:
    def __init__(self, id):
        self.id = id
        self.cw = None
        self.ccw = None

class CyclicList:
    def _init_(self, ids = None): # ids must be sorted clockwise
        self.nodes = []
        if ids:
            for id in ids:
                gn = GapNode(id)
                if self.nodes:
                    self.nodes[-1].cw = gn
                    gn.ccw = self.nodes[-1]
                self.nodes.append(gn)
            self.nodes[-1].cw = self.nodes[0]
            self.nodes[0].ccw = self.nodes[-1]
    
    def delete(self, node):
        if len(self.nodes) == 0:
            return
        elif len(self.nodes) == 1:
            self.nodes.clear()
        else:
            node.ccw.cw = node.cw
            node.cw.ccw = node.ccw
            self.nodes.remove(node)

    def insert_cw(self, newnode, anchornode):
        #insert the new node on the cw side of the anchor node
        newnode.ccw = anchornode
        newnode.cw = anchornode.cw
        anchornode.cw.ccw = newnode
        anchornode.cw = newnode
        self.nodes.append(newnode)

    

