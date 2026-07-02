from queue import PriorityQueue

from graph import Graph


State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = time_horizon

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]:
        start, end = self.graph.get_route_endpoints()
        routes: dict[int, list[State]] = {}

        for drone_id in range(1, nb_drones + 1):
            path = self._dijkstra(start, end)
            if not path:
                raise ValueError(f"No path found for drone {drone_id}")
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

            for neighbor, _ in self.graph.neighbors(hub_name):
                if self.graph.is_blocked(neighbor):
                    continue

                dur = (
                    2
                    if self.graph.get_hub(neighbor).zone == "restricted"
                    else 1
                )
                next_turn = turn + dur
                next_cost = cost + self.graph.move_cost(neighbor)
                if next_cost < best_cost.get(
                    (neighbor, next_turn), float("inf")
                ):
                    priority_queue.put((next_turn, next_cost, neighbor))
                    best_cost[(neighbor, next_turn)] = next_cost
                    came_from[(neighbor, next_turn)] = (hub_name, turn)

        return []

    def _rebuild(
        self, came_from: dict[State, State | None], end_state: State
    ) -> list[State]:
        path: list[State] = []
        node: State | None = end_state
        while node is not None:
            path.append(node)
            node = came_from[node]
        return path[::-1]
