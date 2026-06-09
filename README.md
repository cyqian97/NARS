# NARS

Simulator for the Gap Navigation Tree (GNT) algorithm — a point robot navigates an unknown polygonal environment using only a gap sensor (depth discontinuities), with no distance or coordinate information.

## Setup

```bash
conda env create -f environment.yml
conda activate NARS
```

## Running

```bash
python main.py
```

A 1600×900 window opens with a help screen. Press **H** to toggle it at any time.

## Usage

**1. Draw the environment**

The simulator starts in Draw mode.

- The **first polygon** you draw is the **outer wall** (boundary of the navigable area). Draw it by left-clicking to place vertices, then right-click to close.
- Each **subsequent polygon** is an **obstacle** (interior is infeasible). Same controls.
- **U** — undo last point
- **C** — clear everything
- **S** — save the current map to `./environments/`
- **L** — load the most recently saved map

**2. Run the algorithm**

Press **P** to enter Path mode (requires at least one closed polygon).

- **Left-click** to place the robot's starting position. This initializes the gap sensor and the GNT.
- **Left-click** again to move the robot along a straight-line segment to a new waypoint. Each move detects gap events (appear, disappear, split, merge) along the path and updates the GNT accordingly.
- The circular **gap sensor HUD** (top-left) shows the currently detected gaps as tick marks: red = CCW-side gap, blue = CW-side gap.
- The console prints each gap event and the current GNT state after every move.

**Other controls**

- **G** (Draw mode) — toggle visibility graph overlay
- **L** (Path mode) — load a path from `path.csv` and replay it step by step (hold Enter to advance)
- **Q** / **Esc** — quit

## Codebase Structure

The codebase is split into a pygame-free **backend** (importable as a library) and a **frontend** that handles the interactive simulator.

```
main.py                     Entry point
generate_frames.py          Offline per-frame visualization pipeline (SVG + TikZ)
generate_cylinder_frames.py S^1×[0,T] cylinder animation of gap direction histories
generate_vgm_lift.py        VGM lift: 3D smooth-curve lift with robot gap markers

backend/
  gap.py              Shared data types (Gap, GapEvent, GapEventType, is_tracking_event)
  environment.py      Environment — builds geometric graphs, exposes gap event API
  robot.py            Robot — gap detection and event dispatch
  vgmm.py             VGMM — Gap Navigation Tree algorithm (DoublyLinkedList)
  sensors.py          Work-in-progress HGNT and CyclicList structures

frontend/
  simulator.py        Simulator class + game_loop() pygame event/render loop
  display.py          All pygame rendering functions

utils/
  utils.py                  Color constants
  svg_utils.py              SVG parsing, shadow computation, frame/sensor SVG generation
  tex_utils.py              LaTeX/TikZ standalone sensor-HUD figure generation
  video_utils.py            SVG/PNG frame folder → MP4 conversion
  svg_curve_to_function.py  SVG Bézier parser and tangent sampler
  vgm_lift.py               VGM lift core functions and gap-to-curve mapping

pyvisgraph/
  vis_graph.py        VisGraph — orchestrates building all six geometric graphs
  visible_vertices.py Geometric algorithms: angular sweep, ray cast, intersections
  graph.py            Graph, PolygonGraph, ChainGraph data structures
  classes.py          Point, Edge, Chain primitives
  shortest_path.py    Dijkstra shortest path
```

### Geometric graphs built at startup

When a polygon environment is loaded, six graphs are computed and stored on the `Environment` object:

| Property | Type | Purpose |
|---|---|---|
| `env.polygon_graph` | `PolygonGraph` | Directed boundary edges; infeasible region is always on the right-hand side |
| `env.visibility_graph` | `Graph` | Bitangent (visibility) edges between polygon vertices |
| `env.convex_chains` | `ChainGraph` | Maximal convex vertex chains along each polygon |
| `env.bitangent_comp` | `Graph` | Bitangent complement rays — trigger **Split / Merge** events |
| `env.inflection` | `Graph` | Inflection rays from chain endpoints — trigger **Appear / Disappear** events |
| `env.extension` | `Graph` | Extension rays from chain interior edges — trigger **Proceed / Retreat** events |

## Backend API

The backend can be used independently of pygame, e.g. to run the algorithm programmatically or generate figures.

### Building an environment

```python
from pyvisgraph.classes import Point
from backend import Environment, Robot

# Define polygons as ordered lists of Points.
# First polygon = outer wall, remaining = obstacles.
wall = [Point(0, 0), Point(800, 0), Point(800, 600), Point(0, 600)]
obstacle = [Point(300, 200), Point(500, 200), Point(500, 400), Point(300, 400)]

env = Environment()
env.build([wall, obstacle])
```

### Querying the environment

```python
# Check whether a point is in the free space
env.point_valid(Point(100, 100))   # True
env.point_valid(Point(400, 300))   # False (inside obstacle)

# Find all gap (bitangent) vertices visible from a position
gaps = env.find_visible_vertices(Point(100, 100))

# Compute the shortest collision-free path between two points
path = env.shortest_path(Point(50, 50), Point(750, 550))

# Access raw geometric graphs for export or visualization
for edge in env.bitangent_comp.get_edges():
    print(edge.p1, edge.p2, edge.side)
```

### Running the robot

```python
from pyvisgraph.classes import Edge

start = Point(100, 100)
robot = Robot(env, start)

# Move along a straight-line segment; all gap events are processed internally
robot.move(Edge(start, Point(400, 100)))

# Inspect current gaps
for gap in robot.gaps:
    print(f"vertex={gap.vertex}, side={gap.side}, dir={gap.dir}")
```

### VGM lift plot

`generate_vgm_lift.py` produces a 3D matplotlib plot of the **VGM lift** — each point on the smooth boundary curve is lifted to (x, y, θ) ∈ R²×S¹, where θ is the boundary tangent direction. Robot-detected gaps are overlaid as scatter markers, coloured by step index along the path.

The input SVG must contain:
- `id="curve"` — smooth Bézier boundary (the curve to lift)
- `id="env"` — polygon approximation (used to build the `Environment` for gap detection)
- `id="path"` — robot trajectory (replayed during simulation)

```bash
python generate_vgm_lift.py environments/env_1_smooth.svg
# writes environments/env_1_smooth_vgm_lift.svg

# options
python generate_vgm_lift.py environments/env_1_smooth.svg \
    --n-arrows 2000 \   # tangent samples on the smooth curve
    --n-fine   5000 \   # dense samples for angle-spacing lookup
    --n-steps  200  \   # robot steps along the path
    --angle-tol 0.15    # max angle difference (rad) for a gap candidate match
```

The forward tangent lift is drawn in **red**, the backward (opposite) in **green**. Wrap-around discontinuities at the 0/2π seam are bridged with ▼/▲ markers. The floor projection of the smooth curve is drawn in steel blue.

### Save and load maps

```python
env.save("environments/my_map.json")

env2 = Environment()
env2.load("environments/my_map.json")

# Find the most recently saved file
path = Environment.latest_save()   # returns None if no saves exist
```