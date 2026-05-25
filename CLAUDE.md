# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

NARS is a simulator implementing the **Gap Navigation Tree (GNT)** algorithm from:

> Tovar, Murrieta-Cid, LaValle — *"Distance-Optimal Navigation in an Unknown Environment Without Sensing Distances"*, IEEE Transactions on Robotics, 2007.

A point robot moves in an unknown polygonal environment, sensing only **gaps** — depth discontinuities at convex boundary vertices tangent to the robot's line of sight. No distances, angles, or coordinates are available to the robot. As the robot moves, it builds a GNT data structure that encodes distance-optimal paths from the current position to any reachable point.

## Environment Setup

```bash
conda env create -f environment.yml   # first time
conda activate NARS
```

Dependencies: Python 3.12, numpy, pygame 2.5.2, tqdm 4.66.2.

## Running the Simulator

```bash
python main.py
```

A Pygame window opens (1600×900). The help screen appears on launch; press H to toggle it.

### Keyboard Controls

| Key | Mode | Action |
|-----|------|--------|
| Q / Esc | any | Quit |
| H | any | Toggle help screen |
| D | any | Toggle draw mode |
| P | any | Toggle path mode |
| S | any | Save map to `./environments/<timestamp>.json` |
| U | draw | Undo last polygon point |
| C | draw | Clear all |
| G | draw | Toggle visibility graph overlay |
| L | draw | Load most recent map from `./environments/` |
| L | path | Load path from `path.csv` (hold Enter to step through) |

Left-click to place polygon points; right-click to close a polygon. In path mode, left-click to add waypoints; the `Robot` is instantiated at the first waypoint.

## Algorithm Background

### Gap sensor and critical events

Gaps are the convex boundary vertices of obstacles that are bitangent to the robot's position (i.e., the endpoints of visibility rays that graze the boundary). As the robot moves along a path, the gap sequence G(τ(t)) changes only at **critical events**, which are determined by three geometric structures of the environment boundary ∂R:

| Event | Geometric trigger | Graph attribute |
|-------|------------------|-----------------|
| **A** — gap appears | Robot crosses an **inflection ray** | `env.inflection` |
| **D** — gap disappears | Robot crosses an **inflection ray** | `env.inflection` |
| **S** — gap splits into two | Robot crosses a **bitangent complement** | `env.bitangent_comp` |
| **M** — two gaps merge | Robot crosses a **bitangent complement** | `env.bitangent_comp` |
| **N** — gap vertex advances to next polygon point | Robot crosses an **extension line** | `env.extension` |
| **P** — gap vertex retreats to previous polygon point | Robot crosses an **extension line** | `env.extension` |

N and P are gap-tracking events (the gap persists, its vertex just shifts along the boundary). A, D, S, M are topological events that update the GNT. `is_tracking_event()` in `gap.py` distinguishes the two kinds; `GNT.__call__` is only invoked for A/D/S/M.

### GNT structure

The GNT is a rooted tree where:
- The **root** corresponds to the robot's current position.
- Each **non-root vertex** is a gap in G(τ(s)) for some past s.
- **Children** of a vertex v are the gaps that merged to form v.
- **Leaf vertices** that have permanently disappeared are **primitive** (fully explored branches).
- **Non-primitive leaves** have the potential to split further.

The GNT encodes the shortest path from the robot's current position to any reachable point: chasing the sequence of gaps from root to a target vertex traces the optimal path (Theorem 1 in the paper, valid for simply connected environments).

## Architecture

### Backend / Frontend split

The codebase is split into a pygame-free backend (importable as a library) and a pygame frontend.

```python
from backend import Environment, Robot

env = Environment()
env.build([[Point(x, y), ...], ...])   # build all geometric structures
robot = Robot(env, start_pos)          # initialize gap sensor at start_pos
robot.move(Edge(start_pos, next_pos))  # process all gap events along edge
gaps = robot.gaps                      # list of Gap objects
```

### Directory layout

```
main.py               Entry point — calls frontend.simulator.game_loop()
gap.py                Shared data types: Gap, GapEvent, GapEventType, EventInfo
utils.py              Color constants for display

backend/
  environment.py      Environment class: builds VisGraph, owns gap_events_along()
  robot.py            Robot class: gap detection and event dispatch
  gnt.py              GNT class: DoublyLinkedList-based gap navigation tree algorithm

frontend/
  simulator.py        Simulator class + game_loop(): pygame event/render loop
  display.py          All pygame rendering functions

pyvisgraph/
  classes.py          Point, Edge, Chain primitives
  graph.py            Graph, PolygonGraph, ChainGraph
  visible_vertices.py Geometric algorithms (sweep, ray cast, intersections)
  vis_graph.py        VisGraph: builds all six geometric graphs
  shortest_path.py    Dijkstra shortest path
```

### Data flow

```
Polygons (user-drawn or loaded from JSON)
  └─► Environment.build()
        └─► VisGraph.build()
              ├─ polygon_graph    (PolygonGraph)   directed boundary edges
              ├─ visibility_graph (Graph)           bitangent edges
              ├─ convex_chains    (ChainGraph)      maximal convex chains
              ├─ bitangent_comp   (Graph)           complement rays → S/M events
              ├─ inflection       (Graph)           inflection rays → A/D events
              └─ extension        (Graph)           extension rays  → N/P events
                   └─► Robot.move(path_edge)
                         ├─ env.gap_events_along()  intersect path with all three graphs
                         └─► GNT.__call__(event)    update DoublyLinkedList per gap
```

### Key modules

**`backend/environment.py`** — `Environment` is the main backend API. `build()` wraps `VisGraph.build()`. `gap_events_along(edge)` intersects the path edge with all three critical-event graphs and returns a distance-sorted list of `GapEvent` objects. Properties (`polygon_graph`, `visibility_graph`, `convex_chains`, `bitangent_comp`, `inflection`, `extension`) expose every geometric structure for display or export. `save()`/`load()` use JSON.

**`backend/robot.py`** — `Robot` owns the live gap list. `move(path_edge)` calls `env.gap_events_along()`, dispatches N/P tracking events (vertex update only) and A/D/S/M topological events (calls `self.gnt`), then updates all gap direction vectors.

**`backend/gnt.py`** — `GNT` implements the gap navigation tree update (Section IV-A of the paper). It maintains a `DoublyLinkedList` per gap that encodes the compressed sensor history. The `star_pointer` tracks the gap's current position in its history; `pointers` dict stores branch points from past splits/merges. `gap_id_map` stores label remapping after merge/split to avoid re-registration.

**`gap.py`** — Shared data types: `Gap` (id, vertex, side, dir), `GapEventType` (A/D/S/M/N/P enum), `GapEvent` (pos, edge, etype), `EventInfo` (etype, gap1_id, gap2_id), `is_tracking_event()`.

**`frontend/simulator.py`** — `Simulator` manages UI state (polygons being drawn, mode flags, path, robot). `game_loop()` is the pygame event/render loop. Path CSV helpers are module-level functions.

**`frontend/display.py`** — All pygame rendering. `draw_gap_sensor(robot)` renders the circular HUD. `draw_invisible_areas(robot, graph)` renders shadow polygons behind each gap using a ray-cast + boundary-walk approach.

**`pyvisgraph/`** — Extended fork of the pyvisgraph library.
- `visible_vertices.py`: `bitangent_lines()` is the angular sweep for visibility; `convex_chain()` identifies maximal convex runs; `bitangent_complement()` computes complement rays (S/M triggers); `inflection_lines()` shoots rays from chain start/end (A/D triggers); `extension_lines()` shoots rays from every internal convex-chain edge (N/P triggers).
- `graph.py`: `PolygonGraph` stores boundary with edge direction convention: **the infeasible region is always on the right-hand side** of an edge (p1→p2). Polygon 0 is the outer wall. `ChainGraph` stores convex chains.
- `classes.py`: `Point` (supports arithmetic, hashing), `Edge` (with `side` field for signed half-plane of critical events, and `dual` field linking paired bitangent complement rays), `Chain`.

**`app/display.py`** — All Pygame rendering. `draw_gap_sensor()` renders the circular HUD: each gap is drawn as a tick mark at its angular direction, red for CCW-side gaps, blue for CW-side gaps.

### Polygon conventions

The first drawn polygon is the **wall** (pid=0, the feasible region boundary). All subsequent polygons are **obstacles** (pid≥1). `Environment.point_valid()` returns true only for points inside the wall and outside all obstacles.

### Map persistence

Maps are saved as JSON to `./environments/<YYYY-MM-DD_HH-MM-SS>.json`. Load picks the most recently created matching file. Paths are written/read as plain CSV to `path.csv`.

### Critical-event classification

In `Environment.gap_events_along()`, crossing direction is determined by `_approach_side(path_edge, event_edge)` which computes `ccw(event_edge.p1, event_edge.p2, path_edge.p1)` (falling back to `path_edge.p2` if collinear). The product `side * edge.side` determines event type:

- `bitcomp` edges: product `+1` → Merge, product `-1` → Split
- `inflection` edges: product `+1` → Appear, product `-1` → Disappear
- `extension` edges: `side == -1` → Proceed (N), `side == +1` → Retreat (P)
