
from pyvisgraph import gap_sensor 

class Robot():
    def __init__(self,vis_graph,p):
        self.vis_graph = vis_graph
        self.gaps = {}
        self.detect_gaps(p)
        return

    def detect_gaps(self, p):
        self.gap_vertices = self.vis_graph.find_visible(p)
        self.gap_ids = []
        self.next_gap_id = 0
        for v in self.gap_vertices:
            self.gap_ids.append(self.next_gap_id)
            self.next_gap_id+=1
        print(self.gap_ids)
    



    
