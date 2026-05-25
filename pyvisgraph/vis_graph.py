from pyvisgraph.classes import Edge
from pyvisgraph.graph import PolygonGraph, ChainGraph, Graph
from pyvisgraph.shortest_path import shortest_path
from pyvisgraph.visible_vertices import (
    bitangent_lines,
    point_in_polygon,
    point_in_wall,
    point_valid,
    convex_chain,
    bitangent_complement,
    inflection_lines,
    extension_lines,
    edge_distance,
    closest_point,
    ccw,
)


class VisGraph:
    """Builds and stores all geometric structures needed for gap-event detection.

    Attributes:
        graph          -- PolygonGraph: directed polygon boundary edges
        visibility_graph -- Graph: bitangent (visibility) edges between polygon vertices
        convex_chains  -- ChainGraph: maximal convex vertex chains
        bitangent_comp -- Graph: bitangent complement rays  (trigger S/M events)
        inflection     -- Graph: inflection rays            (trigger A/D events)
        extension      -- Graph: extension rays             (trigger N/P events)
    """

    def __init__(self):
        self.graph = None
        self.visibility_graph = None
        self.convex_chains = None
        self.bitangent_comp = None
        self.inflection = None
        self.extension = None

    def build(self, polygons, status=True):
        """Build all geometric graphs from a list of polygons.

        polygons -- list of polygons; each polygon is an ordered list of Points.
                    The first polygon is the outer wall; the rest are obstacles.
        """
        from tqdm import tqdm

        self.graph = PolygonGraph(polygons)
        self.visibility_graph = Graph()
        self.convex_chains = ChainGraph()
        self.bitangent_comp = Graph()
        self.inflection = Graph()
        self.extension = Graph()

        points = self.graph.get_points()
        batch_size = 10
        batches = [points[i:i + batch_size] for i in range(0, len(points), batch_size)]

        for batch in tqdm(batches, disable=not status):
            for p1 in batch:
                for p2 in bitangent_lines(p1, self.graph, scan="half"):
                    self.visibility_graph.add_edge(Edge(p1, p2))

        convex_chain(self.graph, self.convex_chains)
        bitangent_complement(self.graph, self.visibility_graph, self.bitangent_comp)
        inflection_lines(self.graph, self.convex_chains, self.inflection)
        extension_lines(self.graph, self.convex_chains, self.extension)

    def find_visible_vertices(self, point):
        """Return all polygon vertices visible (bitangent) from point."""
        return bitangent_lines(point, self.graph)

    def shortest_path(self, origin, destination):
        """Return shortest path between origin and destination as a list of Points."""
        origin_exists = origin in self.visibility_graph
        dest_exists = destination in self.visibility_graph
        if origin_exists and dest_exists:
            return shortest_path(self.visibility_graph, origin, destination)

        add_to_visg = PolygonGraph([])
        orgn = None if origin_exists else origin
        dest = None if dest_exists else destination
        if not origin_exists:
            for v in bitangent_lines(origin, self.graph, destination=dest):
                add_to_visg.add_edge(Edge(origin, v))
        if not dest_exists:
            for v in bitangent_lines(destination, self.graph, origin=orgn):
                add_to_visg.add_edge(Edge(destination, v))
        return shortest_path(self.visibility_graph, origin, destination, add_to_visg)

    def point_in_polygon(self, point):
        return point_in_polygon(point, self.graph)

    def point_in_wall(self, point):
        return point_in_wall(point, self.graph)

    def point_valid(self, point):
        return point_valid(point, self.graph)

    def closest_point(self, point, polygon_id, length=0.001):
        return closest_point(point, self.graph, polygon_id, length)
