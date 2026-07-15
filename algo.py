from queue import PriorityQueue
from graph import Graph
from models import Connection

State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = 0

        self.hub_occupancy: dict[State, int] = {}
        self.connection_occupancy: dict[tuple[tuple[str, str], int], int] = {}

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]:
        self.time_horizon = self.graph.hub_count * 2 * nb_drones

        routes: dict[int, list[State]] = {}
        for drone_idx in range(1, nb_drones + 1):
            route = self._dijkstra(*self.graph.get_route_endpoints())
            if not route:
                raise ValueError(f"No path found for drone {drone_idx}!")

            routes[drone_idx] = route
            self._reserve_route(route)
        return routes

    def _reserve_route(self, route: list[State]) -> None:
        for (curr_hub, curr_turn), (next_hub, next_turn) in zip(
            route, route[1:]
        ):
            next_hub_obj = self.graph.get_hub(next_hub)
            if next_hub_obj.type not in ("start_hub", "end_hub"):
                self.hub_occupancy[(next_hub, next_turn)] = (
                    self.hub_occupancy.get((next_hub, next_turn), 0) + 1
                )

            if curr_hub == next_hub:
                continue

            connection_key = self._connection_key(curr_hub, next_hub)
            for turn in range(curr_turn + 1, next_turn + 1):
                self.connection_occupancy[(connection_key, turn)] = (
                    self.connection_occupancy.get((connection_key, turn), 0)
                    + 1
                )

    def _dijkstra(self, start: str, end: str) -> list[State]:
        priority_queue: PriorityQueue[tuple[int, float, str]] = PriorityQueue()
        priority_queue.put((0, 0.0, start))

        best_cost: dict[State, float] = {(start, 0): 0}
        came_from: dict[State, State | None] = {(start, 0): None}

        while not priority_queue.empty():
            print(priority_queue.queue)
            turn, cost, hub = priority_queue.get()

            if hub == end:
                return self._rebuild_route(came_from, (hub, turn))

            if turn >= self.time_horizon:
                continue

            for next_hub, conn in self.graph.neighbors(hub):
                if self.graph.is_blocked(next_hub):
                    continue

                duration = (
                    2
                    if self.graph.get_hub(next_hub).zone == "restricted"
                    else 1
                )
                next_turn = turn + duration
                if self._is_over_capacity(next_hub, conn, turn, next_turn):
                    continue

                next_cost = cost + self.graph.move_cost(next_hub)
                if next_cost < best_cost.get(
                    (next_hub, next_turn), float("inf")
                ):
                    priority_queue.put((next_turn, next_cost, next_hub))
                    best_cost[(next_hub, next_turn)] = next_cost
                    came_from[(next_hub, next_turn)] = (hub, turn)

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
        for turn in range(depart_turn + 1, arrive_turn + 1):
            if (
                self.connection_occupancy.get(
                    (self._connection_key(conn.source, conn.target), turn), 0
                )
                >= conn.max_link_capacity
            ):
                return True

        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return False

        return (
            self.hub_occupancy.get((hub_name, arrive_turn), 0)
            >= hub.max_drones
        )

    def _hub_full(self, hub_name: str, turn: int) -> bool:
        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return False

        return self.hub_occupancy.get((hub_name, turn), 0) >= hub.max_drones

    @staticmethod
    def _connection_key(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    @staticmethod
    def _rebuild_route(
        came_from: dict[State, State | None], end_state: State
    ) -> list[State]:
        route: list[State] = []

        curr: State | None = end_state
        while curr:
            route.append(curr)
            curr = came_from[curr]

        return route[::-1]
