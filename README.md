# Fly-in

## Algo

```py
from modelsV2 import Graph, Hub, Connection, Drone
from heapq import heappush, heappop


# A position in both space (hub) and time (turn)
SpaceTime = tuple[Hub, int]


class Algo:
    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        # {(hub,turn) : nb_drone}
        self.hub_occupancy: dict[SpaceTime, int] = {}
        self.conn_occupancy: dict[tuple[Connection, int], int] = {}
        self.drones: list[Drone] = [Drone(i) for i in range(self.graph.nb_drones)]

    def dijkstra_mapf(self) -> list[SpaceTime]:
        start: str = self.graph.start_hub.name
        end: str = self.graph.end_hub.name
        visited: set[str] = {start}
        pq = [(0.0, start, 0)]  # (cost, hub_name, turn)
        min_cost: dict[tuple[str, int], float] = {(start, 0): 0}
        parent: dict[SpaceTime, SpaceTime] = {}

        while pq:
            current_cost, hub_name, turn = heappop(pq)
            hub: Hub = self.graph.hubs[hub_name]
            if hub_name == end:
                return self._path_reconstruction(parent, turn)
            for neighbor in self.graph.neighbors[hub_name]:
                if neighbor.zone == "blocked":
                    continue
                next_cost = current_cost + neighbor.cost
                next_turn = turn + (1 if neighbor.cost == 0.5
                                    else int(neighbor.cost))
                conn: Connection = self.graph.get_connection(hub, neighbor)
                if self._is_over_capacity(neighbor, conn, next_turn, turn):
                    next_cost = current_cost + 1
                    next_turn = turn + 1
                    if next_cost < min_cost.get((hub_name, next_turn), float('inf')):
                        heappush(pq, (next_cost, hub_name, next_turn))
                        min_cost[(hub_name, next_turn)] = next_cost
                        parent[(hub, next_turn)] = (hub, turn)
                    continue
                if neighbor.name in visited:
                    continue
                visited.add(neighbor.name)
                if next_cost < min_cost.get((neighbor.name, next_turn), float('inf')):
                    heappush(pq, (next_cost, neighbor.name, next_turn))
                    min_cost[(neighbor.name, next_turn)] = next_cost
                    parent[(neighbor, next_turn)] = (hub, turn)
        raise ValueError("No path found")

    def _path_reconstruction(
            self,
            parent: dict[SpaceTime, SpaceTime],
            final_turn: int
    ) -> list[SpaceTime]:
        end: SpaceTime = (self.graph.end_hub, final_turn)
        prev: SpaceTime = parent[end]
        path: list[SpaceTime] = [end]
        while prev != (self.graph.start_hub, 0):
            path.append(prev)
            prev = parent[prev]
        path.append(prev)
        return path[::-1]

    def _is_over_capacity(
            self, neighbor: Hub, conn: Connection, next_turn: int, turn: int
    ) -> bool:
        cap: int = min(neighbor.max_drones, conn.max_link_cap)
        conn_full: bool = self.conn_occupancy.get((conn, turn), 0) >= cap
        hub_full: bool = self.hub_occupancy.get(
            (neighbor, next_turn), 0) >= neighbor.max_drones
        return conn_full or hub_full

    def commit_reservation(self, path: list[SpaceTime]) -> None:
        for step in path:
            self.hub_occupancy[step] = self.hub_occupancy.get(step, 0) + 1
        for i in range(1, len(path)):
            hub, _ = path[i]
            prev_hub, prev_turn = path[i - 1]
            if hub == prev_hub:  # drone waited, no connection used
                continue
            key: tuple[Connection, int] = (
                self.graph.get_connection(hub, prev_hub),
                prev_turn
            )
            self.conn_occupancy[key] = self.conn_occupancy.get(key, 0) + 1

    def move_all_drones(self) -> None:
        for drone in self.drones:
            drone.path = self.dijkstra_mapf()
            self.commit_reservation(drone.path)
```

## Simulation

```py
from algoV2 import Algo
from modelsV2 import Drone
from visualizationV2 import Visualization


class Simulation:
    def __init__(self, algo) -> None:
        self.algo: Algo = algo
        self.visual: Visualization = Visualization(algo)

    def run(self) -> None:
        self.algo.move_all_drones()
        turn: int = 0
        while not self._all_arrived(turn):
            movements: list[str] = self._all_movements_by_turn(turn)
            print(" ".join(movements))
            self.visual.draw_animated(turn, steps=120)
            turn += 1
        self.visual.stop()

    def _all_movements_by_turn(self, turn: int) -> list[str]:
        all_moves: list[str] = []
        for drone in self.algo.drones:
            move: str = self._get_drone_move(turn, drone)
            if move:
                all_moves.append(move)
        return all_moves

    def _get_drone_move(self, turn: int, drone: Drone) -> str:
        move: str = ""
        for i, step in enumerate(drone.path):
            hub, current_turn = step
            if turn == current_turn:
                if hub.name == self.algo.graph.start_hub.name:
                    break
                move = f"D{drone.id}-{hub.name}"
            elif turn == current_turn - 1 and i > 0:
                prev_hub, _ = drone.path[i - 1]
                move = f"D{drone.id}-{prev_hub.name}->{hub.name}"
        return move

    def _all_arrived(self, turn: int) -> bool:
        return all(turn > drone.path[-1][1] for drone in self.algo.drones)
```


## All

```py
from __future__ import annotations

from heapq import heappop, heappush

# A timed position: which hub, at which turn.
State = tuple[str, int]
# A link, stored order-independent so (A,B) == (B,A).
LinkKey = tuple[str, str]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph = graph
        self.time_horizon = time_horizon

        # How many drones occupy a hub at a given turn.
        self.hub_usage: dict[State, int] = {}
        # How many drones occupy a link at a given turn.
        self.link_usage: dict[tuple[LinkKey, int], int] = {}

    # ------------------------------------------------------------------ #
    # Planning                                                           #
    # ------------------------------------------------------------------ #

    def plan_all(
        self, requests: list[tuple[int, str, str]]
    ) -> dict[int, list[State]]:
        """Plan every drone one by one; each new plan respects earlier ones."""
        plans: dict[int, list[State]] = {}

        for drone_id, start, end in requests:
            path = self.find_path(start, end)
            if not path:
                raise ValueError(f"No path found for drone {drone_id}")
            self.reserve(path)
            plans[drone_id] = path

        return plans

    def find_path(self, start: str, end: str) -> list[State]:
        """Space-time Dijkstra. Returns a list of (hub, turn) states."""
        if self.graph.is_blocked(start) or self.graph.is_blocked(end):
            return []

        start_state: State = (start, 0)

        # Queue entries are (turn, pref_cost, hub).
        # Sorted by turn first -> earliest arrival wins.
        queue: list[tuple[int, float, str]] = [(0, 0.0, start)]
        best_cost: dict[State, float] = {start_state: 0.0}
        came_from: dict[State, State | None] = {start_state: None}

        while queue:
            turn, cost, hub = heappop(queue)
            state: State = (hub, turn)

            # Skip outdated queue entries (we found something better since).
            if cost > best_cost.get(state, float("inf")):
                continue

            # First time we pop the goal, it's optimal -> done.
            if hub == end:
                return self._rebuild(came_from, state)

            # Don't explore past the time ceiling.
            if turn >= self.time_horizon:
                continue

            for next_state, next_cost in self._successors(state, cost):
                if next_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = next_cost
                    came_from[next_state] = state
                    next_hub, next_turn = next_state
                    heappush(queue, (next_turn, next_cost, next_hub))

        return []

    def _successors(self, state: State, cost: float):
        """Yield (next_state, next_cost) for waiting and for each legal move."""
        hub, turn = state

        # 1. Wait: same hub, +1 turn, no extra preference cost.
        wait_turn = turn + 1
        if wait_turn <= self.time_horizon and self._can_wait(hub, turn):
            yield (hub, wait_turn), cost

        # 2. Move: go to a neighbor if reservations allow it.
        for neighbor, connection in self.graph.neighbors(hub):
            if self.graph.is_blocked(neighbor):
                continue

            duration = self._move_duration(neighbor)
            arrival = turn + duration
            if arrival > self.time_horizon:
                continue
            if not self._can_move(hub, neighbor, connection, turn):
                continue

            yield (neighbor, arrival), cost + self.graph.move_cost(neighbor)

    # ------------------------------------------------------------------ #
    # Reservations                                                       #
    # ------------------------------------------------------------------ #

    def reserve(self, path: list[State]) -> None:
        """Mark a committed path so later drones avoid collisions."""
        for (prev_hub, prev_turn), (hub, turn) in zip(path, path[1:]):
            if prev_hub == hub:  # the drone waited
                self._reserve_hub(hub, turn)
                continue

            # Occupy the link for the whole duration of the move.
            duration = turn - prev_turn
            for t in range(prev_turn, prev_turn + duration):
                self._reserve_link(prev_hub, hub, t)

            self._reserve_hub(hub, turn)

    # ------------------------------------------------------------------ #
    # Capacity checks                                                    #
    # ------------------------------------------------------------------ #

    def _can_wait(self, hub: str, turn: int) -> bool:
        # Can the drone still be in this hub next turn?
        return self._hub_free(hub, turn + 1)

    def _can_move(
        self, source: str, target: str, connection: Connection, turn: int
    ) -> bool:
        duration = self._move_duration(target)

        # The link must be free for every turn the move spans.
        for t in range(turn, turn + duration):
            if not self._link_free(source, target, t,
                                   connection.max_link_capacity):
                return False

        # And the destination hub must be free on arrival.
        return self._hub_free(target, turn + duration)

    def _hub_free(self, hub: str, turn: int) -> bool:
        if self._is_unlimited(hub):
            return True
        used = self.hub_usage.get((hub, turn), 0)
        return used < self.graph.get_hub(hub).max_drones

    def _link_free(self, source: str, target: str, turn: int,
                   capacity: int) -> bool:
        used = self.link_usage.get((self._link_key(source, target), turn), 0)
        return used < capacity

    def _reserve_hub(self, hub: str, turn: int) -> None:
        if self._is_unlimited(hub):
            return
        key = (hub, turn)
        self.hub_usage[key] = self.hub_usage.get(key, 0) + 1

    def _reserve_link(self, source: str, target: str, turn: int) -> None:
        key = (self._link_key(source, target), turn)
        self.link_usage[key] = self.link_usage.get(key, 0) + 1

    # ------------------------------------------------------------------ #
    # Small helpers                                                      #
    # ------------------------------------------------------------------ #

    def _move_duration(self, target: str) -> int:
        # Restricted zones take 2 turns to traverse; everything else takes 1.
        return 2 if self.graph.get_hub(target).zone == "restricted" else 1

    def _is_unlimited(self, hub: str) -> bool:
        return self.graph.get_hub(hub).type in {"start_hub", "end_hub"}

    def _link_key(self, source: str, target: str) -> LinkKey:
        return (source, target) if source < target else (target, source)

    def _rebuild(
        self, came_from: dict[State, State | None], end_state: State
    ) -> list[State]:
        path: list[State] = []
        node: State | None = end_state
        while node is not None:
            path.append(node)
            node = came_from[node]
        return path[::-1]
```
