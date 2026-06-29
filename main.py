from config_parser import ConfigParser, ConfigSyntaxError
from graph import Graph


if __name__ == "__main__":
    try:
        config = ConfigParser().parse("./maps/easy/01_linear_path.txt")
    except FileNotFoundError as e:
        print(f"[ERROR]: File not found — {e.filename}")
        exit(1)
    except PermissionError as e:
        print(f"[ERROR]: Permission denied reading '{e.filename}'")
        exit(1)
    except ConfigSyntaxError as e:
        print(f"[ERROR]: {e}")
        exit(1)

    graph = Graph(config)


# def dijkstra(graph: Graph, start: str, goal: str) -> list[str]:
#     priority_queue: PriorityQueue[tuple[float, str]] = PriorityQueue()
#     priority_queue.put((0.0, start))
#
#     parent: dict[str, str | None] = {start: None}
#     best_cost: dict[str, float] = {start: 0.0}
#
#     while not priority_queue.empty():
#         curr_cost, curr = priority_queue.get()
#
#         if curr_cost > best_cost[curr]:
#             continue
#
#         if curr == goal:
#             break
#
#         for neighbor, _ in graph.neighbors(curr):
#             if graph.is_blocked(neighbor):
#                 continue
#
#             next_cost = curr_cost + graph.move_cost(neighbor)
#             if next_cost < best_cost.get(neighbor, float("inf")):
#                 best_cost[neighbor] = next_cost
#                 parent[neighbor] = curr
#                 priority_queue.put((next_cost, neighbor))
#
#     if goal not in parent:
#         return []
#
#     path: list[str] = []
#
#     curr_hub: str | None = goal
#     while curr_hub:
#         path.append(curr_hub)
#         curr_hub = parent[curr_hub]
#
#     return path[::-1]
