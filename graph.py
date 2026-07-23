from models import Connection, Hub, MapConfig


class Graph:
    """Undirected graph of zones backed by an adjacency list.

    The structure is built by hand, without any external graph library.
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
        """Return the zone registered under a given name.

        Args:
            name: Name of the zone to look up.

        Returns:
            The matching Hub.

        Raises:
            KeyError: If no zone uses that name.
        """
        return self._hubs[name]

    def get_route_endpoints(self) -> tuple[str, str]:
        """Return the names of the start and end zones.

        Returns:
            A tuple with the start zone name and the end zone name.

        Raises:
            StopIteration: If the map has no start or no end zone.
        """
        start_hub = next(
            hub for hub in self._hubs.values() if hub.type == "start_hub"
        )
        end_hub = next(
            hub for hub in self._hubs.values() if hub.type == "end_hub"
        )
        return start_hub.name, end_hub.name

    def neighbors(self, hub: str) -> list[tuple[str, Connection]]:
        """Return the zones directly reachable from a given zone.

        Args:
            hub: Name of the zone whose neighbours are wanted.

        Returns:
            A list of (neighbour name, connection used) pairs, empty if
            the zone is unknown or isolated.
        """
        return self._adj.get(hub, [])

    def move_cost(self, target: str) -> float:
        """Return the pathfinding weight of entering a zone.

        This is the cost used to rank paths, not the number of turns the
        move takes.

        Args:
            target: Name of the destination zone.

        Returns:
            The weight of the destination zone type.
        """
        hub = self._hubs[target]
        return Graph.ZONE_COSTS[hub.zone]

    def is_blocked(self, name: str) -> bool:
        """Tell whether a zone may never be entered.

        Args:
            name: Name of the zone to test.

        Returns:
            True if the zone type is 'blocked'.
        """
        return self._hubs[name].zone == "blocked"
