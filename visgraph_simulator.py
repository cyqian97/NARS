"""
The MIT License (MIT)

Copyright (c) 2016 Christian August Reksten-Monsen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import pyvisgraph as vg
from robot import Robot
from numpy import array
import pygame
import datetime
import glob
import os
import re
import math
from utils import *
from app.display import *

pygame.init()
gameDisplay = init_game_display()

LEFT = 1
RIGHT = 3


# flags = pygame.OPENGL | pygame.FULLSCREEN
# gameDisplay = pygame.display.set_mode((1920, 1080), flags, vsync=1)
pygame.display.set_caption("NARS Simulator")
clock = pygame.time.Clock()


def help_screen():
    helping = True
    while helping:
        draw_help_screen()
        for event in pygame.event.get():
            quit_event(event)
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_h:
                    helping = False
                elif event.key == pygame.K_d:
                    helping = False
        pygame.display.update()
        clock.tick(10)


def quit_event(event):
    if event.type == pygame.QUIT:
        pygame.quit()
        quit()
    elif event.type == pygame.KEYUP and (
        event.key == pygame.K_q or event.key == pygame.K_ESCAPE
    ):
        pygame.quit()
        quit()


class Simulator:

    def __init__(self):
        self.polygons = []
        self.work_polygon = []
        self.mouse_point = None
        self.mouse_vertices = []
        self.start_point = None
        self.end_point = None
        self.path = []

        self.vis_graph = vg.VisGraph()
        self.built = False
        self.show_static_visgraph = True
        self.show_mouse_visgraph = False
        self.mode_draw = True
        self.mode_path = False

        self.robot = None

    def build(self):
        self.vis_graph.build(self.polygons, status=False)
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
        if len(self.work_polygon) >= 1:
            if not self.is_edge_intersect(
                vg.Edge(self.work_polygon[-1], self.work_polygon[0]), close_edge=True
            ):
                self.polygons.append(self.work_polygon)
                self.work_polygon = []
                self.build()
                self.polygons = self.vis_graph.graph.polygons
            else:
                print("ERROR: Edge cross!")

    def draw_point_undo(self):
        if len(self.work_polygon) > 0:
            self.work_polygon.pop()
        elif len(self.polygons) > 0:
            self.polygons.pop()
            self.build()

    def clear_all(self):
        self.__init__()

    def _clear_path(self):
        self.path = []
        self.start_point = []
        self.end_point = []

    def is_edge_intersect(self, edge, close_edge=False):
        for polygon in self.polygons:
            _l = len(polygon)
            for i, _point in enumerate(polygon):
                _edge = vg.Edge(_point, polygon[(i + 1) % _l])
                if vg.edge_cross_point(edge, _edge):
                    return True
        if len(self.work_polygon) > 2:
            for i in range(len(self.work_polygon) - 2):
                _edge = vg.Edge(self.work_polygon[i], self.work_polygon[i + 1])
                _crose = vg.edge_cross_point(edge, _edge)
                if not close_edge:
                    if _crose:
                        return True
                elif _crose and _crose != edge.p2:
                    return True
        return False

    def save_map(self):
        # Prompt the user for input
        file_name = ""  # input("Enter file name: ")
        if not file_name:
            # Use the current time as the file name
            # Format the time as a string suitable for a file name
            file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Check if 'environments' is a folder under the current directory
        if not os.path.isdir("environments"):
            # Create 'environments' if it doesn't exist
            os.makedirs("environments")
        self.vis_graph.save(
            os.path.join("environments", file_name)
        )  # Check if the input is empty
        print(f"File saved: {file_name}")

    def load_map(self):
        # Directory where the files are located
        directory = "./environments"  # Adjust this path to your directory

        # Pattern to match the files with datetime format "YYYY-MM-DD_HH-MM-SS"
        pattern = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}"

        # List all files in the directory
        files = glob.glob(os.path.join(directory, "*"))

        # Filter files that match the pattern
        filtered_files = [f for f in files if re.search(pattern, os.path.basename(f))]

        # Find the most recently created file among the filtered files
        if filtered_files:
            latest_file = max(filtered_files, key=os.path.getctime)
            print(f"Loading the latest file: {latest_file}")
            self.vis_graph.load(latest_file)
            self.polygons = self.vis_graph.input
            self.build()
        else:
            print("No files found matching the pattern.")


def read_path():
    with open("path.csv", "r") as file:
        for line in file:
            parts = line.strip().split(",")
            yield vg.Point(int(parts[0]), int(parts[1]))


def game_loop():
    sim = Simulator()
    
    gameExit = False
    cursor_pos = None
    path_reader = None

    is_reading_path = False
    keep_reading_path = False
    is_display_update = True

    while not gameExit:
        # Event loop
        for event in pygame.event.get():
            # Check if we should quit the app
            quit_event(event)
            
            # Get current mouse position
            pos = pygame.mouse.get_pos()
            
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_h:
                    help_screen()
                elif event.key == pygame.K_p:
                    sim.toggle_path_mode()
                elif event.key == pygame.K_d:
                    sim.toggle_draw_mode()
                elif event.key == pygame.K_s:
                    sim.save_map()
                #     sim.toggle_path_mode()

            if sim.mode_draw:
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_u:
                        sim.draw_point_undo()
                    elif event.key == pygame.K_c:
                        sim.clear_all()
                    elif event.key == pygame.K_g:
                        sim.show_static_visgraph = not sim.show_static_visgraph
                    elif event.key == pygame.K_l:
                        sim.load_map()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == LEFT:
                        _point = vg.Point(pos[0], pos[1])
                        _is_edge_intersect = False
                        if len(sim.work_polygon) > 0:
                            _is_edge_intersect = sim.is_edge_intersect(
                                vg.Edge(_point, sim.work_polygon[-1])
                            )
                        if not _is_edge_intersect:
                            if len(sim.polygons):
                                if sim.vis_graph.point_valid(_point):
                                    sim.work_polygon.append(_point)
                                else:
                                    print("ERROR: Point invalid!")
                            else:
                                sim.work_polygon.append(_point)
                        else:
                            print("ERROR: Edge cross!")
                    elif event.button == RIGHT:
                        sim.close_polygon()

            if event.type == pygame.MOUSEMOTION:
                cursor_pos = pos

            if sim.mode_path and sim.built:
                if not is_reading_path:
                    if event.type == pygame.MOUSEBUTTONUP:
                        _p = vg.Point(pos[0], pos[1])
                        if event.button == LEFT and sim.vis_graph.point_valid(_p):
                            if len(sim.path) > 0:
                                if not sim.is_edge_intersect(vg.Edge(sim.path[-1], _p)):
                                    sim.path.append(_p)
                                    with open("path.csv", "a") as file:
                                        file.write(f"{pos[0]},{pos[1]}\n")
                                    sim.robot.move(vg.Edge(sim.path[-2], sim.path[-1]))
                                else:
                                    print("ERROR: Edge cross!")
                            else:
                                sim.path.append(_p)
                                with open("path.csv", "w") as file:
                                    file.write(f"{pos[0]},{pos[1]}\n")
                                sim.robot = Robot(sim.vis_graph, _p)
                    elif event.type == pygame.KEYUP:
                        if event.key == pygame.K_l:
                            is_reading_path = True
                            print("Press Enter to continue...")
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    keep_reading_path = True
                elif event.type == pygame.KEYUP and event.key == pygame.K_RETURN:
                    keep_reading_path = False

            if sim.show_mouse_visgraph and sim.built:
                if event.type == pygame.MOUSEMOTION:
                    if sim.vis_graph.point_valid(vg.Point(pos[0], pos[1])):
                        sim.mouse_point = vg.Point(pos[0], pos[1])
                        sim.mouse_vertices = sim.vis_graph.find_bitangent(
                            sim.mouse_point
                        )

        if keep_reading_path and is_display_update:
            if path_reader is None:
                path_reader = read_path()
            try:
                _p = next(path_reader)
                if len(sim.path) > 0:
                    sim.path.append(_p)
                    sim.robot.move(vg.Edge(sim.path[-2], sim.path[-1]))
                else:
                    sim.path.append(_p)
                    sim.robot = Robot(sim.vis_graph, _p)
            except StopIteration:
                is_reading_path = False
                keep_reading_path = False
                print("Path reading complete")
            is_display_update = False

            # if sim.mode_path and sim.built:
            #     if event.type == pygame.MOUSEBUTTONUP or any(
            #         pygame.mouse.get_pressed()
            #     ):
            #         if pygame.mouse.get_pressed()[LEFT - 1] or event.button == LEFT:
            #             sim.start_point = vg.Point(pos[0], pos[1])
            #         elif pygame.mouse.get_pressed()[RIGHT - 1] or event.button == RIGHT:
            #             sim.end_point = vg.Point(pos[0], pos[1])
            #         if sim.start_point and sim.end_point:
            #             sim.path = sim.vis_graph.path(
            #                 sim.start_point, sim.end_point
            #             )

        # Display loop
        gameDisplay.fill(white)
        if cursor_pos:
            draw_text(
                f"{cursor_pos[0]}, {cursor_pos[1]}",
                black,
                30,
                10,
                40,
            )

        if len(sim.work_polygon) > 1:
            draw_polygon(sim.work_polygon, gray, 3, complete=False)

        if len(sim.polygons) > 0:
            polygon = sim.polygons[0]
            polygon.append(polygon[0])
            draw_polygon(polygon, gray, 3, complete=False)
            if len(sim.polygons) > 1:
                for polygon in sim.polygons[1:]:
                    draw_polygon(polygon, gray, 3)

        if sim.built and sim.show_static_visgraph:
            draw_edges_side(
                sim.vis_graph.bitcomp.get_edges(), c_matlab[0], c_matlab[1], 2
            )
            draw_edges_side(sim.vis_graph.extlines.get_edges(), lightblue, lightred, 1)
            draw_edges(sim.vis_graph.visgraph.get_edges(), lightgreen, 1)
            draw_vertices(sim.vis_graph.conv_chains.get_points(), green, 3)
            draw_edges(sim.vis_graph.conv_chains.get_edges(), green, 2)
            for key, value in sim.vis_graph.conv_chains.chains.items():
                p = value.start
                if p:
                    pygame.draw.circle(gameDisplay, green, (p.x, p.y), 6)
                p = value.end
                if p:
                    pygame.draw.circle(gameDisplay, red, (p.x, p.y), 6)
            draw_edges_side(
                sim.vis_graph.inflx.get_edges(), c_matlab[2], c_matlab[3], 2
            )

        if sim.built and sim.show_mouse_visgraph and len(sim.mouse_vertices) > 0:
            for point in sim.mouse_vertices:
                pygame.draw.line(
                    gameDisplay,
                    gray,
                    (sim.mouse_point.x, sim.mouse_point.y),
                    (point.x, point.y),
                    1,
                )

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


if __name__ == "__main__":
    gameDisplay.fill(white)
    help_screen()
    game_loop()
    pygame.quit()
    quit()
