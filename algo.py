from queue import PriorityQueue
from graph import Graph
from models import Connection

State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = time_horizon

        self.hub_occupancy: dict[State, int] = {}
        self.connection_occupancy: dict[tuple[tuple[str, str], int], int] = {}

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]: ...

    def _reserve_path(self, path: list[State]) -> None: ...

    def _dijkstra(self, start: str, end: str) -> list[State]: ...

    @staticmethod
    def _connection_key(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    def _is_over_capacity(
        self,
        hub_name: str,
        conn: Connection,
        depart_turn: int,
        arrive_turn: int,
    ) -> bool: ...

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
