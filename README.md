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

State = tuple[str, int]
LinkKey = tuple[str, str]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph = graph
        self.time_horizon = time_horizon

        # {(hub_name, turn): nb_drones}
        self.hub_occupancy: dict[State, int] = {}

        # {((hub_a, hub_b), turn): nb_drones}
        self.link_occupancy: dict[tuple[LinkKey, int], int] = {}

    def dijkstra_mapf(self, start: str, end: str) -> list[State]:
        if self.graph.is_blocked(start) or self.graph.is_blocked(end):
            return []

        start_state: State = (start, 0)

        # (turn, preference_cost, hub_name)
        pq: list[tuple[int, float, str]] = [(0, 0.0, start)]

        best_cost: dict[State, float] = {start_state: 0.0}
        parent: dict[State, State | None] = {start_state: None}

        while pq:
            turn, cost, hub_name = heappop(pq)
            state: State = (hub_name, turn)

            if cost > best_cost.get(state, float("inf")):
                continue

            if hub_name == end:
                return self._reconstruct_path(parent, state)

            if turn >= self.time_horizon:
                continue

            # 1. Wait action
            wait_turn = turn + 1
            wait_state: State = (hub_name, wait_turn)

            if wait_turn <= self.time_horizon and self._can_wait(
                hub_name,
                turn,
            ):
                if cost < best_cost.get(wait_state, float("inf")):
                    best_cost[wait_state] = cost
                    parent[wait_state] = state
                    heappush(pq, (wait_turn, cost, hub_name))

            # 2. Move actions
            for neighbor_name, connection in self.graph.neighbors(hub_name):
                if self.graph.is_blocked(neighbor_name):
                    continue

                duration = self._move_duration(neighbor_name)
                next_turn = turn + duration
                next_state: State = (neighbor_name, next_turn)

                if next_turn > self.time_horizon:
                    continue

                if not self._can_move(
                    hub_name,
                    neighbor_name,
                    connection,
                    turn,
                ):
                    continue

                next_cost = cost + self.graph.move_cost(neighbor_name)

                if next_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = next_cost
                    parent[next_state] = state
                    heappush(pq, (next_turn, next_cost, neighbor_name))

        return []

    def commit_reservation(self, path: list[State]) -> None:
        for prev_state, curr_state in zip(path, path[1:]):
            prev_hub, prev_turn = prev_state
            curr_hub, curr_turn = curr_state

            # Drone waited
            if prev_hub == curr_hub:
                self._reserve_hub(curr_hub, curr_turn)
                continue

            duration = curr_turn - prev_turn

            # Normal move: reserve link at prev_turn
            self._reserve_link(prev_hub, curr_hub, prev_turn)

            # Restricted move: also reserve link at prev_turn + 1
            if duration == 2:
                self._reserve_link(prev_hub, curr_hub, prev_turn + 1)

            # Reserve arrival hub
            self._reserve_hub(curr_hub, curr_turn)

    def plan_all(
        self,
        drone_requests: list[tuple[int, str, str]],
    ) -> dict[int, list[State]]:
        plans: dict[int, list[State]] = {}

        for drone_id, start, end in drone_requests:
            path = self.dijkstra_mapf(start, end)

            if not path:
                raise ValueError(f"No path found for drone {drone_id}")

            self.commit_reservation(path)
            plans[drone_id] = path

        return plans

    def _reconstruct_path(
        self,
        parent: dict[State, State | None],
        end_state: State,
    ) -> list[State]:
        path: list[State] = []
        curr: State | None = end_state

        while curr is not None:
            path.append(curr)
            curr = parent[curr]

        return path[::-1]

    def _can_wait(self, hub_name: str, turn: int) -> bool:
        return self._hub_has_capacity(hub_name, turn + 1)

    def _can_move(
        self,
        source: str,
        target: str,
        connection: Connection,
        turn: int,
    ) -> bool:
        duration = self._move_duration(target)

        if not self._link_has_capacity(
            source,
            target,
            turn,
            connection.max_link_capacity,
        ):
            return False

        if duration == 2:
            if not self._link_has_capacity(
                source,
                target,
                turn + 1,
                connection.max_link_capacity,
            ):
                return False

        arrival_turn = turn + duration
        return self._hub_has_capacity(target, arrival_turn)

    def _hub_has_capacity(self, hub_name: str, turn: int) -> bool:
        if self._is_unlimited_hub(hub_name):
            return True

        hub = self.graph.get_hub(hub_name)
        used = self.hub_occupancy.get((hub_name, turn), 0)

        return used < hub.max_drones

    def _link_has_capacity(
        self,
        source: str,
        target: str,
        turn: int,
        max_capacity: int,
    ) -> bool:
        key = (self._link_key(source, target), turn)
        used = self.link_occupancy.get(key, 0)

        return used < max_capacity

    def _reserve_hub(self, hub_name: str, turn: int) -> None:
        if self._is_unlimited_hub(hub_name):
            return

        key = (hub_name, turn)
        self.hub_occupancy[key] = self.hub_occupancy.get(key, 0) + 1

    def _reserve_link(self, source: str, target: str, turn: int) -> None:
        key = (self._link_key(source, target), turn)
        self.link_occupancy[key] = self.link_occupancy.get(key, 0) + 1

    def _move_duration(self, target_hub_name: str) -> int:
        hub = self.graph.get_hub(target_hub_name)

        if hub.zone == "restricted":
            return 2

        return 1

    def _is_unlimited_hub(self, hub_name: str) -> bool:
        hub = self.graph.get_hub(hub_name)
        return hub.type in {"start_hub", "end_hub"}

    def _link_key(self, source: str, target: str) -> LinkKey:
        return (source, target) if source < target else (target, source)
```
