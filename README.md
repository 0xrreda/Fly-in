# Fly-in

```py
from queue import PriorityQueue

from graph import Graph

State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = time_horizon

        self.hub_occupancy: dict[State, int] = {}
        self.connection_occupancy: dict[tuple[tuple[str, str], int], int] = {}

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]:
        start, end = self.graph.get_route_endpoints()
        routes: dict[int, list[State]] = {}

        for drone_id in range(1, nb_drones + 1):
            path = self._dijkstra(start, end)
            if not path:
                raise ValueError(f"No path found for drone {drone_id}")

            self._reserve_path(path)
            routes[drone_id] = path

        return routes

    def _dijkstra(self, start: str, end: str) -> list[State]:
        priority_queue: PriorityQueue[tuple[int, float, str]] = PriorityQueue()
        priority_queue.put((0, 0.0, start))

        came_from: dict[State, State | None] = {(start, 0): None}
        best_cost: dict[State, float] = {(start, 0): 0.0}

        while not priority_queue.empty():
            turn, cost, hub_name = priority_queue.get()
            state: State = (hub_name, turn)

            if cost > best_cost.get(state, float("inf")):
                continue

            if hub_name == end:
                return self._rebuild(came_from, state)

            if turn >= self.time_horizon:
                continue

            for neighbor, conn in self.graph.neighbors(hub_name):
                if self.graph.is_blocked(neighbor):
                    continue

                duration = self._movement_duration(neighbor)
                next_turn = turn + duration

                if not self._hub_available(neighbor, next_turn):
                    continue
                if not self._connection_available(
                    hub_name,
                    neighbor,
                    turn,
                    next_turn,
                    conn.max_link_capacity,
                ):
                    continue

                next_cost = cost + self.graph.move_cost(neighbor)
                if next_cost < best_cost.get(
                    (neighbor, next_turn), float("inf")
                ):
                    priority_queue.put((next_turn, next_cost, neighbor))
                    best_cost[(neighbor, next_turn)] = next_cost
                    came_from[(neighbor, next_turn)] = (hub_name, turn)

            wait_turn = turn + 1
            if self._hub_available(hub_name, wait_turn):
                if cost < best_cost.get((hub_name, wait_turn), float("inf")):
                    priority_queue.put((wait_turn, cost, hub_name))
                    best_cost[(hub_name, wait_turn)] = cost
                    came_from[(hub_name, wait_turn)] = (hub_name, turn)

        return []

    def _hub_available(self, hub_name: str, turn: int) -> bool:
        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return True
        return self.hub_occupancy.get((hub_name, turn), 0) < hub.max_drones

    def _connection_available(
        self,
        a: str,
        b: str,
        depart_turn: int,
        arrive_turn: int,
        capacity: int,
    ) -> bool:
        key = self._connection_key(a, b)
        return all(
            self.connection_occupancy.get((key, t), 0) < capacity
            for t in range(depart_turn + 1, arrive_turn + 1)
        )

    def _connection_key(self, a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def _reserve_path(self, path: list[State]) -> None:
        for (prev_hub, prev_turn), (hub, turn) in zip(path, path[1:]):
            hub_obj = self.graph.get_hub(hub)
            if hub_obj.type not in ("start_hub", "end_hub"):
                self.hub_occupancy[(hub, turn)] = (
                    self.hub_occupancy.get((hub, turn), 0) + 1
                )
            if prev_hub == hub:
                continue
            key = self._connection_key(prev_hub, hub)
            for t in range(prev_turn + 1, turn + 1):
                self.connection_occupancy[(key, t)] = (
                    self.connection_occupancy.get((key, t), 0) + 1
                )

    def _movement_duration(self, neighbor: str) -> int:
        return 2 if self.graph.get_hub(neighbor).zone == "restricted" else 1

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
