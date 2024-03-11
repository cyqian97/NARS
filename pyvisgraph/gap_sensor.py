from pyvisgraph.visible_vertices import edge_cross_point,edge_distance

#path edge is a line, p1 is start and p2 is end
def gap_events(path_edge,bitcomp,inflx):
    events = []
    for edge in bitcomp.get_edges():
        p = edge_cross_point(path_edge,edge)
        if p and p!=path_edge.p2: # path line contains the starting but not the ending point
            events.append((p,'b'))
    for edge in inflx.get_edges():
        p = edge_cross_point(path_edge,edge)
        if p and p!=path_edge.p2: 
            events.append((p,'i'))
    events.sort(key=lambda p:edge_distance(p[0],path_edge.p1))
    for p in events:
        print(p[1], end =" ") 
    return events
    