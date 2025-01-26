
import pygame
from numpy import array

from utils import *
import pyvisgraph as vg

# The unique gameDisplay variable
from visgraph_simulator import gameDisplay


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
                gameDisplay,
                color1,
                (edge.p1.x, edge.p1.y),
                (edge.p2.x, edge.p2.y),
                size,
            )
        elif edge.side == -1:
            pygame.draw.line(
                gameDisplay,
                color2,
                (edge.p1.x, edge.p1.y),
                (edge.p2.x, edge.p2.y),
                size,
            )
        else:
            raise Exception(f"Edge side should be -1 or 1, not {edge.side}")


def draw_vertices(points, color, size):
    global gameDisplay
    for p in points:
        pygame.draw.circle(gameDisplay, color, (p.x, p.y), size)


def draw_star(screen, color, point, size):
    global gameDisplay
    """
    Draws a 5-point star centered at 'center' with a given 'size' and 'color' on 'screen'.
    - screen: pygame.Surface where the star will be drawn.
    - center: Tuple (x, y) coordinates for the center of the star.
    - size: The radius of the circle in which the star fits.
    - color: The color of the star.
    """
    x, y = point
    points = []
    # Loop to calculate the points for both the outer and inner vertices
    for i in range(10):
        radius = size if i % 2 == 0 else size / 2
        # 36 degrees between each point, starting facing upwards
        angle = math.radians(i * 36 - 90)
        point_x = x + math.cos(angle) * radius
        point_y = y + math.sin(angle) * radius
        points.append((point_x, point_y))
    pygame.draw.polygon(screen, color, points)


def draw_gap_sensor(robot):
    global gameDisplay
    center = array((220, 250))
    radius = 150
    pygame.draw.circle(gameDisplay, black, center, radius, 3)
    pygame.draw.circle(gameDisplay, black, center, 10)
    if robot:
        for gap in robot.gaps:
            dir = gap.dir
            start = center + radius * dir
            end = center + (radius + 6) * dir
            text_center = center + (radius + 16) * dir - array([5, 5])
            if gap.side == vg.CCW:
                pygame.draw.line(gameDisplay, red, start, end, 3)
                draw_text(str(gap.id), red, 25, text_center[0], text_center[1])
            elif gap.side == vg.CW:
                pygame.draw.line(gameDisplay, blue, start, end, 3)
                draw_text(str(gap.id), blue, 25, text_center[0], text_center[1])
            else:
                pygame.draw.line(gameDisplay, black, start, end, 3)
                draw_text(str(gap.id), black, 25, text_center[0], text_center[1])


def draw_text(mode_txt, color, size, x, y):
    global gameDisplay
    font = pygame.font.SysFont(None, size)
    text = font.render(mode_txt, True, color)
    gameDisplay.blit(text, (x, y))