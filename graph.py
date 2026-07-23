from models import Connection, Hub, MapConfig


class Graph:
    """Undirected graph of zones backed by an adjacency list.

    For every zone it stores the neighbouring zones together with the
    connection used to reach them, so the pathfinder can check link
    capacity while it explores.

    Attributes:
        ZONE_COSTS: Pathfinding weight of each zone type. 'priority' is
            slightly cheaper than 'normal' so it gets preferred, and
            'blocked' is infinite so it is never chosen.
        hub_count: Total number of zones in the graph.
    """

    ZONE_COSTS: dict[str, float] = {
        "normal": 1.0,
        "blocked": float("inf"),
        "restricted": 2.0,
        "priority": 0.9,
    }

    def __init__(self, config: MapConfig) -> None:
        """Build the adjacency list from a parsed configuration.

        Each connection is registered in both directions, since links
        are bidirectional.

        Args:
            config: Parsed map holding the zones and the connections.
        """
        self._hubs: dict[str, Hub] = dict(config.hubs)
        self.hub_count: int = len(config.hubs)

        self._adj: dict[str, list[tuple[str, Connection]]] = {
            name: [] for name in config.hubs
        }

        for conn in config.connections:
            self._adj[conn.source].append((conn.target, conn))
            self._adj[conn.target].append((conn.source, conn))

    def get_hub(self, name: str) -> Hub:
        """Look up a zone by its name.

        Args:
            name: Zone name to look up.

        Returns:
            The Hub registered under that name.

        Raises:
            KeyError: If no zone uses that name.
        """
        return self._hubs[name]

    def get_route_endpoints(self) -> tuple[str, str]:
        """Find the zones marked as start_hub and end_hub.

        Returns:
            (start zone name, end zone name).

        Raises:
            StopIteration: If either one is missing from the map.
        """
        start_hub = next(
            hub for hub in self._hubs.values() if hub.type == "start_hub"
        )
        end_hub = next(
            hub for hub in self._hubs.values() if hub.type == "end_hub"
        )
        return start_hub.name, end_hub.name

    def neighbors(self, hub: str) -> list[tuple[str, Connection]]:
        """List the zones one hop away from a given zone.

        Args:
            hub: Name of the zone to look around.

        Returns:
            (neighbour name, connection) pairs. Empty for an unknown or
            isolated zone — there's no neighbour to report either way.
        """
        return self._adj.get(hub, [])

    def move_cost(self, target: str) -> float:
        """Give the Dijkstra weight for stepping into a zone.

        Args:
            target: Name of the zone being entered.

        Returns:
            ZONE_COSTS[zone type] for that zone.
        """
        hub = self._hubs[target]
        return Graph.ZONE_COSTS[hub.zone]

    def is_blocked(self, name: str) -> bool:
        """Check whether a zone is off-limits entirely.

        Args:
            name: Zone to test.

        Returns:
            True when the zone's type is 'blocked'.
        """
        return self._hubs[name].zone == "blocked"

    def unreachable_hubs(self) -> set[str]:
        """Find zones that have no path back to the start zone at all.

        Returns:
           Every zone name that start can't reach.
        """
        hubs_names: set[str] = set(self._hubs)
        start, _ = self.get_route_endpoints()

        visited: set[str] = set()
        stack: list[str] = [start]
        while stack:
            hub = stack.pop()
            if hub in visited:
                continue
            visited.add(hub)

            for neighbor, _ in self.neighbors(hub):
                if neighbor not in visited:
                    stack.append(neighbor)

        return hubs_names - visited

    def is_end_reachable(self) -> bool:
        """Check that a blocked-avoiding path from start to end exists.

        Returns:
            True if such a path exists.
        """
        start, end = self.get_route_endpoints()

        visited: set[str] = set()
        stack: list[str] = [start]
        while stack:
            hub = stack.pop()
            if hub == end:
                return True

            if hub in visited:
                continue
            visited.add(hub)

            for neighbor, _ in self.neighbors(hub):
                if neighbor not in visited and not self.is_blocked(neighbor):
                    stack.append(neighbor)

        return False
