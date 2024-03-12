from pyvisgraph.visible_vertices import edge_cross_point,edge_distance, ccw, CCW, CW

#path edge is a line, p1 is start and p2 is end
def gap_events(path_edge,bitcomp,inflx):
    events = []
    for edge in bitcomp.get_edges():
        p = edge_cross_point(path_edge,edge)
        if p and p!=path_edge.p2: # path line contains the starting but not the ending point
            _side = ccw(edge.p1, edge.p2,path_edge.p1)
            if _side == CCW:
                events.append((p,'b','->'))
            elif _side == CW:
                events.append((p,'b','<-'))
            else:
                raise Exception("Error: path_edge.e1 is on the line of a bitangent complement")



    for edge in inflx.get_edges():
        p = edge_cross_point(path_edge,edge)
        if p and p!=path_edge.p2: 
            _side = ccw(edge.p1, edge.p2,path_edge.p1)
            if _side == CCW:
                events.append((p,'i','->'))
            elif _side == CW:
                events.append((p,'i','<-'))
            else:
                raise Exception("Error: path_edge.e1 is on the line of a inflection line")

    events.sort(key=lambda p:edge_distance(p[0],path_edge.p1))
    for p in events:
        print(p[1]+p[2], end =" ") 
    return events
    