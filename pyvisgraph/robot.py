
from pyvisgraph.gap_sensor import gap_events 
from pyvisgraph import Point
from pyvisgraph.visible_vertices import ccw
from numpy import array
from numpy.linalg import norm

class Robot():
    def __init__(self,vis_graph,p):
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
                side = ccw(self.pos,v,next_point)
            else:
                side = 0
            current_gaps.append(Gap(-1,v,side,dir))
        self.associate_gaps(current_gaps)
    
    def associate_gaps(self,current_gaps,motion = None):
        if not self.gaps:
            for gap in current_gaps:
                self.assign_gap_id(gap)
                self.gaps.append(gap)

        
        print([g.id for g in self.gaps])

    def assign_gap_id(self,gap):
        gap.id = self.gap_count
        self.gap_count += 1


class Gap():
    __slots__ = ("id", "vertex","side", "dir")

    def __init__(self,id,vertex,side,dir):
        assert isinstance(id,int)
        assert isinstance(vertex,Point)
        assert (norm(dir)-1) > -1e-10  and (norm(dir)-1) < 1e-10
        self.id = id
        self.vertex = vertex
        self.dir = dir
        self.side = side

    



    
