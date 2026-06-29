from queue import PriorityQueue

from graph import Graph


State = tuple[str, int]


class Algo:
    def __init__(self, graph: Graph, time_horizon: int = 200) -> None:
        self.graph: Graph = graph
        self.time_horizon: int = time_horizon

        self.start_hub_name, self.end_hub_name = (
            self.graph.get_route_endpoints()
        )

    def dijkstra(self) -> list[str]:
        priority_queue: PriorityQueue[tuple[int, float, str]] = PriorityQueue()
        priority_queue.put((0, 0.0, self.start_hub_name))

        parent: dict[State, str | None] = {(self.start_hub_name, 0): None}
        best_cost: dict[State, float] = {(self.start_hub_name, 0): 0.0}

        while not priority_queue.empty():
            turn, cost, hub_name = priority_queue.get()
            state: State = (hub_name, turn)

            if cost > best_cost[state]:
                continue

            if hub_name == self.end_hub_name:
                break

            for neighbor, _ in self.graph.neighbors(hub_name):
                if self.graph.is_blocked(neighbor):
                    continue

                ...

        return []
