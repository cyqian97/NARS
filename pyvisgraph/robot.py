
from pyvisgraph.gap_sensor import gap_events 
from pyvisgraph import Point
from numpy import array
from numpy.linalg import norm

class Robot():
    def __init__(self,vis_graph,p):
        self.vis_graph = vis_graph
        self.gaps = []
        self.pos = p
        self.next_gap_id = 0
        self.detect_gaps()
        return

    def detect_gaps(self):
        gap_vertices = self.vis_graph.find_visible(self.pos)
        for v in gap_vertices:
            dir = (v-self.pos).to_vec()
            dir = dir/norm(dir)
            self.gaps.append(Gap(self.next_gap_id,v,dir))
            self.next_gap_id+=1
        print([g.id for g in self.gaps])
    
    def update():
        events = gap_events(path_edge,self.vis_graph.bitcomp,self.vis_graph.inflx)
        # for event in events:



class Gap():
    __slots__ = ("id", "vertex", "dir")

    def __init__(self,id,vertex,dir):
        assert isinstance(id,int)
        assert isinstance(vertex,Point)
        assert (norm(dir)-1) > -1e-10  and (norm(dir)-1) < 1e-10
        self.id = id
        self.vertex = vertex
        self.dir = dir

    



    
