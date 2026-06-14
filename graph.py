from models import Connection, Hub, MapConfig


class Graph:
    ZONE_COSTS: dict[str, float] = {
        "normal": 1.0,
        "blocked": float("inf"),
        "restricted": 2.0,
        "priority": 1.0,
    }

    def __init__(self, config: MapConfig) -> None:
        self._hubs: dict[str, Hub] = config.hubs
        self._adj: dict[str, list[tuple[str, Connection]]] = {
            name: [] for name in config.hubs
        }

        for conn in config.connections:
            self._adj[conn.source].append((conn.target, conn))
            self._adj[conn.target].append((conn.source, conn))

    def get_hub(self, name: str) -> Hub:
        return self._hubs[name]

    def get_route_endpoints(self) -> tuple[Hub, Hub]:
        start_hub = next(
            hub for hub in self._hubs.values() if hub.type == "start_hub"
        )
        end_hub = next(
            hub for hub in self._hubs.values() if hub.type == "end_hub"
        )
        return start_hub, end_hub

    def neighbors(self, hub: str) -> list[tuple[str, Connection]]:
        return self._adj.get(hub, [])

    def move_cost(self, target: str) -> float:
        hub = self._hubs[target]
        return Graph.ZONE_COSTS[hub.zone]

    def is_blocked(self, name: str) -> bool:
        return self._hubs[name].zone == "blocked"

    def is_priority(self, name: str) -> bool:
        return self._hubs[name].zone == "priority"
