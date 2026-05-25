import datetime
import os

import pygame

import pyvisgraph as vg
from backend import Environment, Robot
from frontend.display import (
    init_game_display, draw_polygon, draw_edges, draw_edges_side,
    draw_vertices, draw_gap_sensor, draw_text, draw_invisible_areas,
    draw_help_screen,
)
from utils.utils import *

LEFT = 1
RIGHT = 3


class Simulator:
    """Manages scene state for the interactive Pygame app."""

    def __init__(self):
        self.env = Environment()
        self.polygons = []        # list of closed polygon point-lists
        self.work_polygon = []    # polygon currently being drawn
        self.path = []            # list of path waypoints
        self.robot = None

        self.built = False
        self.show_static_visgraph = True
        self.show_mouse_visgraph = False
        self.mode_draw = True
        self.mode_path = False

        self.mouse_point = None
        self.mouse_vertices = []

    def build(self):
        self.env.build(self.polygons, status=False)
        self.polygons = self.env.polygon_graph.polygons
        self.built = True

    def toggle_draw_mode(self):
        self.mode_draw = not self.mode_draw
        self._clear_path()
        self.mode_path = False

    def toggle_path_mode(self):
        if self.mode_path:
            self._clear_path()
        self.mode_path = not self.mode_path
        self.mode_draw = False
        self.show_mouse_visgraph = self.mode_path

    def close_polygon(self):
        if len(self.work_polygon) < 1:
            return
        close_edge = vg.Edge(self.work_polygon[-1], self.work_polygon[0])
        if not self._edge_crosses_existing(close_edge, close_edge=True):
            self.polygons.append(self.work_polygon)
            self.work_polygon = []
            self.build()
        else:
            print("ERROR: Edge cross!")

    def undo(self):
        if self.work_polygon:
            self.work_polygon.pop()
        elif self.polygons:
            self.polygons.pop()
            self.build()

    def clear_all(self):
        self.__init__()

    def save_map(self):
        if not os.path.isdir("environments"):
            os.makedirs("environments")
        filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        path = os.path.join("environments", filename)
        self.env.save(path)
        print(f"Map saved: {path}")

    def load_map(self):
        path = Environment.latest_save()
        if path:
            print(f"Loading: {path}")
            self.env.load(path)
            self.polygons = self.env.polygon_graph.polygons
            self.built = True
        else:
            print("No saved map found.")

    def add_path_point(self, point):
        """Add a waypoint; create or advance the robot."""
        if self.path:
            edge = vg.Edge(self.path[-1], point)
            if self._edge_crosses_existing(edge):
                print("ERROR: Edge cross!")
                return
            self.path.append(point)
            _append_path_csv(point)
            self.robot.move(edge)
        else:
            self.path.append(point)
            _write_path_csv(point)
            self.robot = Robot(self.env, point)

    def _clear_path(self):
        self.path = []
        self.robot = None

    def _edge_crosses_existing(self, edge, close_edge=False):
        for polygon in self.polygons:
            _l = len(polygon)
            for i, pt in enumerate(polygon):
                if vg.edge_cross_point(edge, vg.Edge(pt, polygon[(i + 1) % _l])):
                    return True
        if len(self.work_polygon) > 2:
            for i in range(len(self.work_polygon) - 2):
                seg = vg.Edge(self.work_polygon[i], self.work_polygon[i + 1])
                cross = vg.edge_cross_point(edge, seg)
                if not close_edge:
                    if cross:
                        return True
                elif cross and cross != edge.p2:
                    return True
        return False


def _write_path_csv(point):
    with open("path.csv", "w") as f:
        f.write(f"{int(point.x)},{int(point.y)}\n")


def _append_path_csv(point):
    with open("path.csv", "a") as f:
        f.write(f"{int(point.x)},{int(point.y)}\n")


def _read_path():
    with open("path.csv", "r") as f:
        for line in f:
            parts = line.strip().split(",")
            yield vg.Point(int(parts[0]), int(parts[1]))


def _quit_event(event):
    if event.type == pygame.QUIT:
        pygame.quit()
        quit()
    if event.type == pygame.KEYUP and event.key in (pygame.K_q, pygame.K_ESCAPE):
        pygame.quit()
        quit()


def _help_screen(clock, gameDisplay):
    helping = True
    while helping:
        draw_help_screen()
        for event in pygame.event.get():
            _quit_event(event)
            if event.type == pygame.KEYUP and event.key in (pygame.K_h, pygame.K_d):
                helping = False
        pygame.display.update()
        clock.tick(10)


def game_loop():
    pygame.init()
    gameDisplay = init_game_display()
    pygame.display.set_caption("NARS Simulator")
    clock = pygame.time.Clock()

    sim = Simulator()
    cursor_pos = None
    path_reader = None
    is_reading_path = False
    keep_reading_path = False
    is_display_update = True

    gameDisplay.fill(white)
    _help_screen(clock, gameDisplay)

    while True:
        for event in pygame.event.get():
            _quit_event(event)
            pos = pygame.mouse.get_pos()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_h:
                    _help_screen(clock, gameDisplay)
                elif event.key == pygame.K_p:
                    sim.toggle_path_mode()
                elif event.key == pygame.K_d:
                    sim.toggle_draw_mode()
                elif event.key == pygame.K_s:
                    sim.save_map()

            if sim.mode_draw:
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_u:
                        sim.undo()
                    elif event.key == pygame.K_c:
                        sim.clear_all()
                    elif event.key == pygame.K_g:
                        sim.show_static_visgraph = not sim.show_static_visgraph
                    elif event.key == pygame.K_l:
                        sim.load_map()
                elif event.type == pygame.MOUSEBUTTONUP:
                    pt = vg.Point(pos[0], pos[1])
                    if event.button == LEFT:
                        if sim.work_polygon:
                            if sim._edge_crosses_existing(vg.Edge(pt, sim.work_polygon[-1])):
                                print("ERROR: Edge cross!")
                                continue
                        if sim.polygons and not sim.env.point_valid(pt):
                            print("ERROR: Point invalid!")
                            continue
                        sim.work_polygon.append(pt)
                    elif event.button == RIGHT:
                        sim.close_polygon()

            if event.type == pygame.MOUSEMOTION:
                cursor_pos = pos

            if sim.mode_path and sim.built and not is_reading_path:
                if event.type == pygame.MOUSEBUTTONUP and event.button == LEFT:
                    pt = vg.Point(pos[0], pos[1])
                    if sim.env.point_valid(pt):
                        sim.add_path_point(pt)
                elif event.type == pygame.KEYUP and event.key == pygame.K_l:
                    is_reading_path = True
                    print("Press Enter to step through path...")
            elif is_reading_path:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    keep_reading_path = True
                elif event.type == pygame.KEYUP and event.key == pygame.K_RETURN:
                    keep_reading_path = False

            if sim.show_mouse_visgraph and sim.built and event.type == pygame.MOUSEMOTION:
                pt = vg.Point(pos[0], pos[1])
                if sim.env.point_valid(pt):
                    sim.mouse_point = pt
                    sim.mouse_vertices = sim.env.find_visible_vertices(pt)

        if keep_reading_path and is_display_update:
            if path_reader is None:
                path_reader = _read_path()
            try:
                pt = next(path_reader)
                sim.add_path_point(pt)
            except StopIteration:
                is_reading_path = False
                keep_reading_path = False
                print("Path reading complete.")
            is_display_update = False

        # --- Render ---
        gameDisplay.fill(white)

        if cursor_pos:
            draw_text(f"{cursor_pos[0]}, {cursor_pos[1]}", black, 30, 10, 40)

        if len(sim.work_polygon) > 1:
            draw_polygon(sim.work_polygon, gray, 3, complete=False)

        if sim.polygons:
            wall = sim.polygons[0]
            wall.append(wall[0])
            draw_polygon(wall, gray, 3, complete=False)
            for poly in sim.polygons[1:]:
                draw_polygon(poly, gray, 3)

        if sim.built and sim.show_static_visgraph:
            draw_edges_side(sim.env.bitangent_comp.get_edges(), c_matlab[0], c_matlab[1], 2)
            draw_edges_side(sim.env.extension.get_edges(), lightblue, lightred, 1)
            draw_edges(sim.env.visibility_graph.get_edges(), lightgreen, 1)
            draw_vertices(sim.env.convex_chains.get_points(), green, 3)
            draw_edges(sim.env.convex_chains.get_edges(), green, 2)
            for chain in sim.env.convex_chains.chains.values():
                if chain.start:
                    pygame.draw.circle(gameDisplay, green, (chain.start.x, chain.start.y), 6)
                if chain.end:
                    pygame.draw.circle(gameDisplay, red, (chain.end.x, chain.end.y), 6)
            draw_edges_side(sim.env.inflection.get_edges(), c_matlab[2], c_matlab[3], 2)

        if sim.built and sim.show_mouse_visgraph and sim.mouse_vertices:
            for pt in sim.mouse_vertices:
                pygame.draw.line(
                    gameDisplay, gray,
                    (sim.mouse_point.x, sim.mouse_point.y),
                    (pt.x, pt.y), 1,
                )

        if sim.robot and sim.built:
            draw_invisible_areas(sim.robot, sim.env.polygon_graph)

        draw_gap_sensor(sim.robot)

        if len(sim.path) > 1:
            draw_polygon(sim.path, brown, 3, complete=False)

        if sim.mode_draw:
            draw_text("-- DRAW MODE --", black, 25, 5, 5)
        elif sim.mode_path:
            draw_text("-- PATH MODE --", black, 25, 5, 5)
        else:
            draw_text("-- VIEW MODE --", black, 25, 5, 5)

        pygame.display.update()
        is_display_update = True
        clock.tick(20)
