from queue import PriorityQueue
from graph import Graph
from models import Connection

State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = 1000

        self.hub_occupancy: dict[State, int] = {}
        self.connection_occupancy: dict[tuple[tuple[str, str], int], int] = {}

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]:
        self.time_horizon = 2 * self.graph.hub_count * nb_drones

        start, end = self.graph.get_route_endpoints()

        paths: dict[int, list[State]] = {}
        for drone_id in range(1, nb_drones + 1):
            path = self._dijkstra(start, end)
            if not path:
                raise ValueError(f"No path found for drone {drone_id}")

            paths[drone_id] = path
            self._reserve_path(path)

        return paths

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

    def _dijkstra(self, start: str, end: str) -> list[State]:
        priority_queue: PriorityQueue[tuple[int, float, str]] = PriorityQueue()
        priority_queue.put((0, 0.0, start))

        best_cost: dict[State, float] = {(start, 0): 0}
        came_from: dict[State, State | None] = {(start, 0): None}

        while not priority_queue.empty():
            turn, cost, hub = priority_queue.get()

            if hub == end:
                return self._rebuild(came_from, (hub, turn))

            if turn > self.time_horizon:
                continue

            for neighbor, conn in self.graph.neighbors(hub):
                if self.graph.is_blocked(neighbor):
                    continue

                duration = (
                    2
                    if self.graph.get_hub(neighbor).zone == "restricted"
                    else 1
                )
                next_turn = turn + duration
                if self._is_over_capacity(neighbor, conn, turn, next_turn):
                    continue

                next_cost = cost + self.graph.move_cost(neighbor)
                if next_cost < best_cost.get(
                    (neighbor, next_turn), float("inf")
                ):
                    priority_queue.put((next_turn, next_cost, neighbor))
                    best_cost[(neighbor, next_turn)] = next_cost
                    came_from[(neighbor, next_turn)] = (hub, turn)

            wait_turn = turn + 1
            if not self._hub_full(hub, wait_turn):
                priority_queue.put((wait_turn, cost, hub))
                best_cost[(hub, wait_turn)] = cost
                came_from[(hub, wait_turn)] = (hub, turn)

        return []

    def _is_over_capacity(
        self,
        hub_name: str,
        conn: Connection,
        depart_turn: int,
        arrive_turn: int,
    ) -> bool:
        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return False

        conn_key = self._connection_key(conn.source, conn.target)
        for t in range(depart_turn + 1, arrive_turn + 1):
            if (
                self.connection_occupancy.get((conn_key, t), 0)
                >= conn.max_link_capacity
            ):
                return True

        return (
            self.hub_occupancy.get((hub_name, arrive_turn), 0)
            >= hub.max_drones
        )

    @staticmethod
    def _connection_key(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def _hub_full(self, hub_name: str, turn: int) -> bool:
        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return False

        return self.hub_occupancy.get((hub_name, turn), 0) >= hub.max_drones

    @staticmethod
    def _rebuild(
        came_from: dict[State, State | None], end_state: State
    ) -> list[State]:
        path: list[State] = []
        curr: State | None = end_state
        while curr is not None:
            path.append(curr)
            curr = came_from[curr]
        return path[::-1]
