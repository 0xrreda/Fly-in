# *This project has been created as part of the 42 curriculum by reda.*

## Description

**Fly-in** is a drone routing system. Given a network of connected zones and a fleet of drones, it moves every drone from a single **start** zone to a single **end** zone in as few simulation turns as possible, while respecting a set of movement and capacity constraints.

The problem is a scheduling problem on top of a pathfinding one: drones move simultaneously, zones and connections have limited capacity, some zones cost more turns to enter, and drones sometimes have to wait so they don't collide. The goal is to minimise the **total number of turns** needed to deliver the whole fleet.

The project reads a map file, builds the graph by hand, computes a route for every drone, prints the turn-by-turn movements in the required output format, and replays the whole thing in an animated window.

## Instructions

### Requirements

- Python 3.10 or later
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for dependency management

### Installation

```bash
make install        # runs `uv sync`
```

### Running the program

The program takes a single argument: the path to a map file.

```bash
# via the Makefile
make run FILE=maps/easy/01_linear_path.txt

# or directly
uv run main.py maps/easy/01_linear_path.txt
```

This prints the turn-by-turn simulation output to the terminal **and** opens an animated window replaying the routes.

### Playback controls (animation window)

| Key             | Action                     |
|-----------------|----------------------------|
| `Space`         | Pause / resume playback    |
| `R`             | Restart the replay         |
| `Q` / `Esc`     | Close the window           |

### Makefile targets

| Target          | Description                                                        |
|-----------------|-------------------------------------------------------------------|
| `make install`  | Install dependencies via `uv sync`                                |
| `make run`      | Run the program on `FILE=<map_path>`                              |
| `make debug`    | Run the program under Python's debugger (`pdb`)                   |
| `make clean`    | Remove `__pycache__`, `.mypy_cache`, and other caches            |
| `make lint`     | Run `flake8` and `mypy` with the mandated flags                  |
| `make format`   | Format the code with `ruff`                                       |

## Map file format

A map is a plain-text file. The first line sets the number of drones, then each line declares a zone or a connection. Comments start with `#` and are ignored.

```text
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

- `start_hub: <name> <x> <y> [metadata]` — the unique start zone.
- `end_hub: <name> <x> <y> [metadata]` — the unique end zone.
- `hub: <name> <x> <y> [metadata]` — a regular zone.
- `connection: <name1>-<name2> [metadata]` — a bidirectional link.
- Zone metadata: `zone=<type>` (default `normal`), `color=<value>`, `max_drones=<n>` (default `1`).
- Connection metadata: `max_link_capacity=<n>` (default `1`).
- Zone names may use any characters except dashes and spaces (a dash separates the two ends of a connection).

Sample maps are provided under `maps/` in `easy/`, `medium/`, `hard/`, and `challenger/` difficulty tiers.

## Usage example

### Input

`maps/easy/01_linear_path.txt` (a linear path with 2 drones — see above).

### Output

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

Each line is one simulation turn; each token `D<id>-<zone>` is a drone moving into a zone that turn. Notice how drone 2 waits one turn on the start zone so it never shares a single-capacity waypoint with drone 1 — a total of 4 turns. Drones crossing toward a restricted zone are reported mid-flight as `D<id>-<from>-<to>` on the intermediate turn.

## Algorithm and implementation strategy

### Time-expanded state space

The core idea is to search over **`(zone, turn)`** states rather than plain zones. A drone's route is therefore a list of `(zone, turn)` pairs, which naturally encodes both *where* the drone is and *when* — including turns spent waiting in place. Because a drone can always wait, this state space is infinite; a **time horizon** (`hub_count * 2 * nb_drones`) bounds the search so it always terminates while staying large enough to admit a valid schedule.

### Per-drone Dijkstra with capacity reservation

Drones are routed **one at a time**. For each drone:

1. `Algo._dijkstra` finds its cheapest route through the current state space. The priority queue is ordered by **turn first**, so the first time the end zone is popped it has been reached as early as possible. From any state a drone may move to a free neighbour, or wait one turn if its zone still has room.
2. `Algo._reserve_route` then **books** every zone and link the accepted route uses, per turn, in `hub_occupancy` and `connection_occupancy`.

The next drone's search reads those reservations through `_is_over_capacity` and `_hub_full`, so it automatically routes around zones and links that are already
full at a given turn. They emerge from the reservations rather than from special-case code.

### Cost model vs. turn model

Two distinct notions of "distance" are kept separate on purpose:

- **Turn cost** — how many turns a move takes (`restricted` = 2, everything else = 1). This drives the primary ordering of the search and the final score.
- **Path weight** — `Graph.ZONE_COSTS`, used only to *rank* equal-turn options. `priority` zones are given a slightly lower weight (`0.9`) than `normal` (`1.0`), so they are preferred as the subject requires, while `blocked` is infinite so it is never chosen.

### Capacity and restricted-transit handling

- Links are bidirectional, so `_connection_key` sorts the two zone names to give `a-b` and `b-a` a single shared reservation key.
- Entering a restricted zone costs 2 turns; the crossing reserves the link for every intermediate turn, matching the rule that the drone occupies the connection during transit and must arrive on the next turn.
- The start and end zones are explicitly exempt from all capacity checks.

### Error handling

Every stage is wrapped so the program never crashes on bad input. The parser raises a `ConfigSyntaxError` that points at the exact offending line with a hint; `main.py` catches file, permission, syntax, and routing errors and prints a clear `[ERROR]` message instead of a traceback. The whole project is type-checked with
`mypy` and linted with `flake8`, and uses context managers for file handling.

## Visual representation

The program provides visual feedback in **two** complementary ways.

### terminal output

The simulation prints the mandated turn-by-turn format — one line per turn, listing that turn's `D<id>-<zone>` movements (or `D<id>-<from>-<to>` for drones in flight toward a restricted zone). Drones that don't move are omitted; drones that reached the end zone are no longer reported.

### Animated graphical replay (`arcade`)

`Simulation` is an `arcade.Window` that replays the routes:

- Zones are drawn as labelled circles laid out from their map coordinates (`_build_layout` rescales them to the window and flips the y-axis). A zone that declares a known `color` name is filled with it, so the map metadata is visible at a glance.
- Connections are drawn as lines between the zones they link.
- Drones are numbered circles whose positions are between consecutive `(zone, turn)` states (`_drone_position` / `_remap`).
- A `Turn X / Total` counter tracks progress.

## Resources

- [How Dijkstra's Algorithm Works](https://youtu.be/EFg3u_E6eHU?si=d9jgPWXOiWD83MGY).
- [Shortest Path Algorithms Explained (Dijkstra's & Bellman-Ford)](https://youtu.be/j0OUwduDOS0?si=nkHIb66Fgt0s87pc).
- [Dijkstra's Algorithm - A step by step analysis, with sample Python code](https://youtu.be/_B5cx-WD5EA?si=S7-M7-PyS2fIK_YL).
- Multi-agent path finding (MAPF) — the general problem family this project is a simplified instance of (reservation-based conflict avoidance).
- [`uv` documentation](https://docs.astral.sh/uv/) — dependency and environment management.

### AI usage

AI was used in the following ways during this project:

- **Edge cases and validation**: brainstorming malformed-map cases (duplicate connections, unknown zone types, bad capacities) to harden the parser's error messages.
- **Explaining `arcade`**: AI helped explain the [`arcade`](https://api.arcade.academy/) 2D game library used for the visualisation — how the `Window` lifecycle works (`on_update` advances the clock, `on_draw` redraws each frame, `on_key_press` handles input), and how to draw and place the zones and drones on screen.
- **README drafting**: this README was drafted with AI assistance.

