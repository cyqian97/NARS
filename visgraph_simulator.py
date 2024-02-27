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
import pygame
import datetime
import glob
import os
import re

pygame.init()

display_width = 1600
display_height = 900

black = (0, 0, 0)
white = (255, 255, 255)
red = (237, 41, 57)
darkred = (120, 0, 0)
lightred = (255, 220, 220)
gray = (100, 100, 100)
lightgray = (225, 225, 225)
green = (0, 128, 0)
blue = (17, 0, 187)
lightblue = (220, 220, 255)

LEFT = 1
RIGHT = 3

gameDisplay = pygame.display.set_mode((display_width, display_height))
# flags = pygame.OPENGL | pygame.FULLSCREEN
# gameDisplay = pygame.display.set_mode((1920, 1080), flags, vsync=1)
pygame.display.set_caption("NARS Simulator")
clock = pygame.time.Clock()


def draw_polygon(polygon, color, size, complete=True):
    if complete:
        polygon.append(polygon[0])
        pygame.draw.polygon(gameDisplay, color, [point() for point in polygon])
    else:
        p1 = polygon[0]
        for p2 in polygon[1:]:
            pygame.draw.line(gameDisplay, color,
                             (p1.x, p1.y), (p2.x, p2.y), size)
            p1 = p2


def draw_edges(edges, color, size):
    for edge in edges:
        pygame.draw.line(
            gameDisplay, color, (edge.p1.x,
                                 edge.p1.y), (edge.p2.x, edge.p2.y), size
        )


def draw_edges_side(edges, color1, color2, size):
    for edge in edges:
        if edge.side == 1:
            pygame.draw.line(
                gameDisplay, color1, (edge.p1.x,
                                      edge.p1.y), (edge.p2.x, edge.p2.y), size
            )
        elif edge.side == -1:
            pygame.draw.line(
                gameDisplay, color2, (edge.p1.x,
                                      edge.p1.y), (edge.p2.x, edge.p2.y), size
            )
        else:
            raise Exception(f"Edge side should be -1 or 1, not {edge.side}")


def draw_vertices(points, color, size):
    for p in points:
        pygame.draw.circle(gameDisplay, color, (p.x, p.y), size)


def draw_visible_mouse_vertices(pos, points, color, size):
    for point in points:
        pygame.draw.line(gameDisplay, color, (pos.x, pos.y),
                         (point.x, point.y), size)


def draw_text(mode_txt, color, size, x, y):
    font = pygame.font.SysFont(None, size)
    text = font.render(mode_txt, True, color)
    gameDisplay.blit(text, (x, y))


def help_screen():
    rectw = 550
    recth = 500
    rectwi = rectw - 10
    recthi = recth - 10
    startx = display_width * 0.5 - rectw / 2
    starty = display_height * 0.5 - recth / 2
    startxi = display_width * 0.5 - rectwi / 2
    startyi = display_height * 0.5 - recthi / 2

    helping = True
    while helping:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_h:
                    helping = False

        pygame.draw.rect(gameDisplay, black, (startx, starty, rectw, recth))
        pygame.draw.rect(gameDisplay, white,
                         (startxi, startyi, rectwi, recthi))

        draw_text(
            "-- VISIBILITY GRAPH SIMULATOR --", black, 30, startxi + 90, startyi + 10
        )
        draw_text(
            "H - TOGGLE HELP SCREEN (THIS SCREEN)",
            black,
            25,
            startxi + 10,
            startyi + 80,
        )
        draw_text("D - TOGGLE DRAW MODE", black,
                  25, startxi + 10, startyi + 115)
        draw_text(
            "    Draw polygons by left clicking to set a point of the",
            black,
            25,
            startxi + 10,
            startyi + 150,
        )
        draw_text(
            "    polygon. Right click to close and finish the polygon.",
            black,
            25,
            startxi + 10,
            startyi + 180,
        )
        draw_text(
            "    U - UNDO LAST POLYGON POINT PLACEMENT",
            black,
            25,
            startxi + 10,
            startyi + 215,
        )
        draw_text("    C - CLEAR THE SCREEN", black,
                  25, startxi + 10, startyi + 250)
        # draw_text("S - TOGGLE SHORTEST PATH MODE", black, 25, startxi+10, startyi+285)
        # draw_text("    Left click to set start point, right click to set end point.", black, 25, startxi+10, startyi+320)
        # draw_text("    Hold left/right mouse button down to drag start/end point.", black, 25, startxi+10, startyi+355)
        draw_text(
            "P - TOGGLE PATH MODE",
            black,
            25,
            startxi + 10,
            startyi + 285,
        )
        draw_text("S - SAVE MAP", black, 25, startxi + 10, startyi + 355)
        draw_text("L - LOAD MAP", black, 25, startxi + 10, startyi + 390)
        # draw_text("G - TOGGLE POLYGON VISIBILITY GRAPH", black, 25, startxi+10, startyi+425)
        # draw_text("© Christian August Reksten-Monsen", black, 20, startxi+140, startyi+470)

        pygame.display.update()
        clock.tick(10)


class Simulator:

    def __init__(self):
        self.polygons = []
        self.work_polygon = []
        self.mouse_point = None
        self.mouse_vertices = []
        # self.start_point = None
        # self.end_point = None
        self.path = []

        self.vis_graph = vg.VisGraph()
        self.built = False
        self.show_static_visgraph = True
        self.show_mouse_visgraph = False
        self.mode_draw = True
        self.mode_path = False

    def toggle_draw_mode(self):
        self.mode_draw = not self.mode_draw
        self._clear_path()
        self.mode_path = False

    def close_polygon(self):
        if len(self.work_polygon) > 1:
            self.polygons.append(self.work_polygon)
            self.work_polygon = []
            self.vis_graph.build(self.polygons, status=False)
            self.built = True

    def draw_point_undo(self):
        if len(self.work_polygon) > 0:
            self.work_polygon.pop()

    def toggle_path_mode(self):
        if self.mode_path:
            self._clear_path()
        self.mode_path = not self.mode_path
        self.mode_draw = False

    def clear_all(self):
        self.__init__()

    def _clear_path(self):
        self.path = []
        # self.start_point = []
        # self.end_point = []

    def save_map(self):
        # Prompt the user for input
        file_name = ""  # input("Enter file name: ")
        if not file_name:
            # Use the current time as the file name
            # Format the time as a string suitable for a file name
            file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Check if 'environments' is a folder under the current directory
        if not os.path.isdir('environments'):
            # Create 'environments' if it doesn't exist
            os.makedirs('environments')
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
        filtered_files = [f for f in files if re.search(
            pattern, os.path.basename(f))]

        # Find the most recently created file among the filtered files
        if filtered_files:
            latest_file = max(filtered_files, key=os.path.getctime)
            print(f"Loading the latest file: {latest_file}")
            self.vis_graph.load(latest_file)
            self.polygons = self.vis_graph.input
            self.vis_graph.build(self.polygons, status=False)
            self.built = True
        else:
            print("No files found matching the pattern.")


def game_loop():
    sim = Simulator()
    gameExit = False

    cursor_pos = None

    while not gameExit:
        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            pos = pygame.mouse.get_pos()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_h:
                    help_screen()
                # elif event.key == pygame.K_g:
                #     sim.show_static_visgraph = not sim.show_static_visgraph
                elif event.key == pygame.K_d:
                    sim.toggle_draw_mode()
                elif event.key == pygame.K_s:
                    sim.save_map()
                elif event.key == pygame.K_l:
                    sim.load_map()
                elif event.key == pygame.K_p:
                    sim.show_mouse_visgraph = not sim.show_mouse_visgraph
                    sim.toggle_path_mode()

            if sim.mode_draw:
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_u:
                        sim.draw_point_undo()
                    elif event.key == pygame.K_c:
                        sim.clear_all()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == LEFT:
                        if len(sim.polygons) > 0:
                            if sim.vis_graph.point_valid(vg.Point(pos[0], pos[1])):
                                print(f"({pos[0]}, {pos[1]})")
                                sim.work_polygon.append(
                                    vg.Point(pos[0], pos[1]))
                        else:
                            sim.work_polygon.append(vg.Point(pos[0], pos[1]))
                    elif event.button == RIGHT:
                        sim.close_polygon()

            if event.type == pygame.MOUSEMOTION:
                cursor_pos = pos
            if sim.mode_path and sim.built:
                if event.type == pygame.MOUSEBUTTONUP and event.button == LEFT:
                    p = vg.Point(pos[0], pos[1])
                    if sim.vis_graph.point_valid(p):
                        sim.path.append(p)
                # if event.type == pygame.MOUSEBUTTONUP or any(
                #     pygame.mouse.get_pressed()
                # ):
                #     if pygame.mouse.get_pressed()[LEFT - 1] or event.button == LEFT:
                #         sim.start_point = vg.Point(pos[0], pos[1])
                #     elif pygame.mouse.get_pressed()[RIGHT - 1] or event.button == RIGHT:
                #         sim.end_point = vg.Point(pos[0], pos[1])
                #     if sim.start_point and sim.end_point:
                #         sim.path = sim.vis_graph.path(
                #             sim.start_point, sim.end_point
                #         )

            if sim.show_mouse_visgraph and sim.built:
                if event.type == pygame.MOUSEMOTION:
                    if sim.vis_graph.point_valid(vg.Point(pos[0], pos[1])):
                        sim.mouse_point = vg.Point(pos[0], pos[1])
                        sim.mouse_vertices = sim.vis_graph.find_visible(
                            sim.mouse_point)

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
            draw_edges_side(sim.vis_graph.bitcomp.get_edges(),
                            lightred, lightblue, 2)
            draw_vertices(sim.vis_graph.conv_chains.get_points(), green, 3)
            draw_edges(sim.vis_graph.conv_chains.get_edges(), green, 2)
            for key, value in sim.vis_graph.conv_chains.chains.items():
                p = value.start
                if p:
                    pygame.draw.circle(gameDisplay, green, (p.x, p.y), 6)
                p = value.end
                if p:
                    pygame.draw.circle(gameDisplay, red, (p.x, p.y), 6)
            draw_edges(sim.vis_graph.inflx.get_edges(), lightgray, 2)

        if sim.built and sim.show_mouse_visgraph and len(sim.mouse_vertices) > 0:
            draw_visible_mouse_vertices(
                sim.mouse_point, sim.mouse_vertices, black, 1)

        if len(sim.path) > 1:
            draw_polygon(sim.path, red, 3, complete=False)

        if sim.mode_draw:
            draw_text("-- DRAW MODE --", black, 25, 5, 5)
        elif sim.mode_path:
            draw_text("-- SHORTEST PATH MODE --", black, 25, 5, 5)
        else:
            draw_text("-- VIEW MODE --", black, 25, 5, 5)

        pygame.display.update()
        clock.tick(20)


if __name__ == "__main__":
    gameDisplay.fill(white)
    help_screen()
    game_loop()
    pygame.quit()
    quit()
