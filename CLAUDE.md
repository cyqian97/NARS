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
python visgraph_simulator.py
```

A Pygame window opens (1600×900). The help screen appears on launch; press H to toggle it.

### Keyboard Controls

| Key | Mode | Action |
|-----|------|--------|
| Q / Esc | any | Quit |
| H | any | Toggle help screen |
| D | any | Toggle draw mode |
| P | any | Toggle path mode |
| S | any | Save map to `./environments/<timestamp>` |
| U | draw | Undo last polygon point |
| C | draw | Clear all |
| G | draw | Toggle visibility graph overlay |
| L | draw | Load most recent map from `./environments/` |
| L | path | Load path from `path.csv` (hold Enter to step through) |

Left-click to place polygon points; right-click to close a polygon. In path mode, left-click to add waypoints; the `Robot` is instantiated at the first waypoint.

## Algorithm Background

### Gap sensor and critical events

Gaps are the convex boundary vertices of obstacles that are bitangent to the robot's position (i.e., the endpoints of visibility rays that graze the boundary). As the robot moves along a path, the gap sequence G(τ(t)) changes only at **critical events**, which are determined by three geometric structures of the environment boundary ∂R:

| Event | Geometric trigger | Code graph |
|-------|------------------|------------|
| **A** — gap appears | Robot crosses an **inflection ray** | `inflx` |
| **D** — gap disappears | Robot crosses an **inflection ray** | `inflx` |
| **S** — gap splits into two | Robot crosses a **bitangent complement** | `bitcomp` |
| **M** — two gaps merge | Robot crosses a **bitangent complement** | `bitcomp` |
| **N** — gap vertex advances to next polygon point | Robot crosses an **extension line** | `extlines` |
| **P** — gap vertex retreats to previous polygon point | Robot crosses an **extension line** | `extlines` |

N and P are gap-tracking events (the gap persists, its vertex just shifts along the boundary). A, D, S, M are topological events that update the GNT. `is_tracking_events()` in `gap_classes.py` distinguishes the two kinds; `algorithm_1` is only called for A/D/S/M.

### GNT structure

The GNT is a rooted tree where:
- The **root** corresponds to the robot's current position.
- Each **non-root vertex** is a gap in G(τ(s)) for some past s.
- **Children** of a vertex v are the gaps that merged to form v.
- **Leaf vertices** that have permanently disappeared are **primitive** (fully explored branches).
- **Non-primitive leaves** have the potential to split further.

The GNT encodes the shortest path from the robot's current position to any reachable point: chasing the sequence of gaps from root to a target vertex traces the optimal path (Theorem 1 in the paper, valid for simply connected environments).

## Architecture

### Data flow

```
Polygons (user-drawn)
  └─► VisGraph.build()                     # pyvisgraph/vis_graph.py
        ├─ graph (PolygonGraph)             # raw polygon edges, CCW/CW oriented
        ├─ visgraph                         # bitangent lines (visibility graph)
        ├─ conv_chains (ChainGraph)         # maximal convex chains of boundary vertices
        ├─ bitcomp                          # bitangent complement rays  → S/M events
        ├─ inflx                            # inflection rays            → A/D events
        └─ extlines                         # extension rays             → N/P events
             └─► Robot.move(path_edge)      # robot.py
                   ├─ gap_events()          # intersect path_edge with bitcomp/inflx/extlines
                   └─► algorithm_1(event)   # algorithm.py — GNT update
```

### Key modules

**`visgraph_simulator.py`** — Entry point. `Simulator` manages scene state (polygons, path, robot). `game_loop()` is the Pygame event/render loop.

**`robot.py`** — `Robot` owns the live gap list. `move(path_edge)` intersects the path edge against all three geometric graphs, sorts the resulting `GapEvent`s by distance, updates gap vertices for N/P events, then calls `algorithm_1` for each A/D/S/M event.

**`algorithm.py`** — `algorithm_1` implements the GNT update. It maintains a `DoublyLinkedList` per gap that encodes the compressed sensor history (Section IV-A of the paper). The `star_pointer` tracks the gap's current position in its history; `prev`/`next` nodes point to predecessor/successor gaps for reconstruction after split/merge. `vis_gaps` is the set of currently visible gaps. `gap_id_map` stores the label remapping after merge/split to avoid re-registration (per the paper's convention of reusing the earlier gap's label).

**`gap_classes.py`** — Core data types: `Gap` (id, vertex, side, dir), `GapEventType` (A/D/S/M/N/P enum), `GapEvent` (pos, edge, etype), `EventInfo` (etype, gap1_id, gap2_id).

**`pyvisgraph/`** — Extended fork of the pyvisgraph library.
- `visible_vertices.py`: `bitangent_lines()` is the angular sweep for visibility; `convex_chain()` identifies maximal convex runs of boundary vertices; `bitangent_complement()` computes the two rays from each bitangent endpoint toward the opposite boundary (the S/M triggers); `inflection_lines()` shoots rays from the start/end of each convex chain (A/D triggers); `extention_lines()` shoots rays from every internal convex-chain edge in both directions (N/P triggers).
- `graph.py`: `PolygonGraph` stores the boundary with edge direction convention: **the infeasible region is always on the right-hand side** of an edge (p1→p2). Polygon 0 is the outer wall (edges are flipped relative to obstacles so the exterior is infeasible). `ChainGraph` stores convex chains with their start/end endpoints.
- `classes.py`: `Point` (supports arithmetic, hashing), `Edge` (with `side` field used for the signed half-plane of critical events, and `dual` field linking paired bitangent complement rays), `Chain`.

**`app/display.py`** — All Pygame rendering. `draw_gap_sensor()` renders the circular HUD: each gap is drawn as a tick mark at its angular direction, red for CCW-side gaps, blue for CW-side gaps.

**`utils.py`** — Color constants only.

### Polygon conventions

The first drawn polygon is the **wall** (pid=0, the feasible region boundary). All subsequent polygons are **obstacles** (pid≥1). `point_valid()` returns true only for points inside the wall and outside all obstacles.

### Map persistence

Maps are pickled to `./environments/<YYYY-MM-DD_HH-MM-SS>` (saves `graph`, `visgraph`, `input`, `conv_chains`, `bitcomp`). Load picks the most recently created matching file. Paths are written/read as plain CSV to `path.csv`.
