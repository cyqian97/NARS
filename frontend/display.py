import math
import pygame
from collections import defaultdict
from numpy import array

from utils.utils import *
import pyvisgraph as vg
from pyvisgraph.visible_vertices import intersect_point, edge_distance

gameDisplay = None
display_width = 1600
display_height = 900


def init_game_display():
    global gameDisplay
    gameDisplay = pygame.display.set_mode((display_width, display_height))
    return gameDisplay


def draw_polygon(polygon, color, size, complete=True):
    global gameDisplay
    if complete:
        if len(polygon) > 1:
            polygon.append(polygon[0])
            pygame.draw.polygon(gameDisplay, color, [point() for point in polygon])
        else:
            draw_star(gameDisplay, purple, (polygon[0].x, polygon[0].y), size * 3)
    else:
        p1 = polygon[0]
        for p2 in polygon[1:]:
            pygame.draw.line(gameDisplay, color, (p1.x, p1.y), (p2.x, p2.y), size)
            p1 = p2


def draw_edges(edges, color, size):
    global gameDisplay
    for edge in edges:
        pygame.draw.line(
            gameDisplay, color, (edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y), size
        )


def draw_edges_side(edges, color1, color2, size):
    global gameDisplay
    for edge in edges:
        if edge.side == 1:
            pygame.draw.line(
                gameDisplay, color1, (edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y), size
            )
        elif edge.side == -1:
            pygame.draw.line(
                gameDisplay, color2, (edge.p1.x, edge.p1.y), (edge.p2.x, edge.p2.y), size
            )
        else:
            raise Exception(f"Edge side should be -1 or 1, not {edge.side}")


def draw_vertices(points, color, size):
    global gameDisplay
    for p in points:
        pygame.draw.circle(gameDisplay, color, (p.x, p.y), size)


def draw_star(screen, color, point, size):
    x, y = point
    pts = []
    for i in range(10):
        radius = size if i % 2 == 0 else size / 2
        angle = math.radians(i * 36 - 90)
        pts.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
    pygame.draw.polygon(screen, color, pts)


def draw_gap_sensor(robot):
    global gameDisplay
    center = array((220, 250))
    radius = 150
    pygame.draw.circle(gameDisplay, black, center, radius, 3)
    pygame.draw.circle(gameDisplay, black, center, 10)
    if robot:
        for gap in robot.gaps:
            d = gap.dir
            start = center + radius * d
            end = center + (radius + 6) * d
            text_pos = center + (radius + 16) * d - array([5, 5])
            if gap.side == vg.CCW:
                pygame.draw.line(gameDisplay, red, start, end, 3)
                # draw_text(str(gap.id), red, 25, text_pos[0], text_pos[1])
            elif gap.side == vg.CW:
                pygame.draw.line(gameDisplay, blue, start, end, 3)
                # draw_text(str(gap.id), blue, 25, text_pos[0], text_pos[1])
            else:
                pygame.draw.line(gameDisplay, black, start, end, 3)
                # draw_text(str(gap.id), black, 25, text_pos[0], text_pos[1])


def draw_text(mode_txt, color, size, x, y):
    font = pygame.font.SysFont(None, size)
    text = font.render(mode_txt, True, color)
    gameDisplay.blit(text, (x, y))


def _compute_shadow_endpoint(robot_pos, gap_vertex, graph):
    dx = gap_vertex.x - robot_pos.x
    dy = gap_vertex.y - robot_pos.y
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return None, None
    far = vg.Point(gap_vertex.x + dx / length * 3000,
                   gap_vertex.y + dy / length * 3000)
    min_dist = float('inf')
    nearest = None
    hit_edge = None
    for edge in graph.get_edges():
        if gap_vertex in edge:
            continue
        p = intersect_point(gap_vertex, far, edge)
        if p is None:
            continue
        if not (min(edge.p1.x, edge.p2.x) - 1 <= p.x <= max(edge.p1.x, edge.p2.x) + 1):
            continue
        if not (min(edge.p1.y, edge.p2.y) - 1 <= p.y <= max(edge.p1.y, edge.p2.y) + 1):
            continue
        if (p.x - gap_vertex.x) * dx + (p.y - gap_vertex.y) * dy <= 0:
            continue
        d = edge_distance(gap_vertex, p)
        if d < min_dist:
            min_dist = d
            nearest = p
            hit_edge = edge
    return nearest, hit_edge


def _build_shadow_graph(graph, shadow_insertions):
    next_pt = {}
    prev_pt = {}
    for edge in graph.get_edges():
        next_pt[edge.p1] = edge.p2
        prev_pt[edge.p2] = edge.p1

    edge_to_pts = defaultdict(list)
    for shadow_pt, hit_edge in shadow_insertions:
        edge_to_pts[hit_edge].append(shadow_pt)

    for hit_edge, pts in edge_to_pts.items():
        pts.sort(key=lambda p: edge_distance(hit_edge.p1, p))
        chain = [hit_edge.p1] + pts + [hit_edge.p2]
        for i in range(len(chain) - 1):
            next_pt[chain[i]] = chain[i + 1]
            prev_pt[chain[i + 1]] = chain[i]

    return next_pt, prev_pt


def _trace_invisible_area(gap, shadow_pt, next_pt, prev_pt, max_steps=5000):
    vertices = [gap.vertex]
    current = gap.vertex
    for _ in range(max_steps):
        nxt = next_pt.get(current) if gap.side == vg.CCW else prev_pt.get(current)
        if nxt is None:
            break
        vertices.append(nxt)
        if nxt == shadow_pt:
            break
        current = nxt
    return vertices


def draw_invisible_areas(robot, graph):
    global gameDisplay
    if robot is None or not robot.gaps:
        return

    shadow_info = []
    for gap in robot.gaps:
        shadow_pt, hit_edge = _compute_shadow_endpoint(robot.pos, gap.vertex, graph)
        if shadow_pt is not None and hit_edge is not None:
            shadow_info.append((gap, shadow_pt, hit_edge))
    if not shadow_info:
        return

    next_pt, prev_pt = _build_shadow_graph(
        graph, [(sp, he) for _, sp, he in shadow_info]
    )

    overlay = pygame.Surface((display_width, display_height), pygame.SRCALPHA)
    for gap, shadow_pt, _ in shadow_info:
        vertices = _trace_invisible_area(gap, shadow_pt, next_pt, prev_pt)
        if len(vertices) >= 3:
            pts = [(int(p.x), int(p.y)) for p in vertices]
            pygame.draw.polygon(overlay, (80, 80, 80, 160), pts)
    gameDisplay.blit(overlay, (0, 0))


def draw_help_screen():
    global gameDisplay
    rectw, recth = 550, 500
    rectwi, recthi = rectw - 10, recth - 10
    startx = display_width * 0.5 - rectw / 2
    starty = display_height * 0.5 - recth / 2
    startxi = display_width * 0.5 - rectwi / 2
    startyi = display_height * 0.5 - recthi / 2
    pygame.draw.rect(gameDisplay, black, (startx, starty, rectw, recth))
    pygame.draw.rect(gameDisplay, white, (startxi, startyi, rectwi, recthi))

    draw_text("-- VISIBILITY GRAPH SIMULATOR --", black, 30, startxi + 90, startyi + 10)
    draw_text("Q - QUIT", black, 25, startxi + 10, startyi + 45)
    draw_text("H - TOGGLE HELP SCREEN (THIS SCREEN)", black, 25, startxi + 10, startyi + 80)
    draw_text("D - TOGGLE DRAW MODE", black, 25, startxi + 10, startyi + 115)
    draw_text("    Draw polygons by left clicking to set a point of the",
              black, 25, startxi + 10, startyi + 150)
    draw_text("    polygon. Right click to close and finish the polygon.",
              black, 25, startxi + 10, startyi + 180)
    draw_text("    U - UNDO LAST POLYGON POINT PLACEMENT", black, 25, startxi + 10, startyi + 215)
    draw_text("    C - CLEAR THE SCREEN", black, 25, startxi + 10, startyi + 250)
    draw_text("P - TOGGLE PATH MODE", black, 25, startxi + 10, startyi + 285)
    draw_text("    L - LOAD PATH", black, 25, startxi + 10, startyi + 320)
    draw_text("S - SAVE MAP", black, 25, startxi + 10, startyi + 355)
    draw_text("L - LOAD MAP", black, 25, startxi + 10, startyi + 390)
