# NARS

Simulator for the Gap Navigation Tree (GNT) algorithm — a point robot navigates an unknown polygonal environment using only a gap sensor (depth discontinuities), with no distance or coordinate information.

## Setup

```bash
conda env create -f environment.yml
conda activate NARS
```

## Running

```bash
python visgraph_simulator.py
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