import heapq

from graph import Graph
from models import Connection

State = tuple[str, int]


class Algo:
    """Routes drones from the start zone to the end zone.

    Attributes:
        graph: The network the drones move through.
        time_horizon: Upper bound on the turn a search may explore. The
            (zone, turn) space is infinite because a drone can always
            wait, so this bound is what guarantees the search ends.
        hub_occupancy: Number of drones booked in a zone at a turn.
        connection_occupancy: Number of drones booked on a link at a
            turn, keyed by a direction independent link key.
    """

    def __init__(self, graph: Graph) -> None:
        """Create a router for a given graph.

        Args:
            graph: The network the drones will be routed through.
        """
        self.graph: Graph = graph
        self.time_horizon: int = 0

        self.hub_occupancy: dict[State, int] = {}
        self.connection_occupancy: dict[tuple[tuple[str, str], int], int] = {}

    def generate_routes(self, nb_drones: int) -> dict[int, list[State]]:
        """Compute one route per drone, reserving capacity as it goes.

        Args:
            nb_drones: How many drones must reach the end zone.

        Returns:
            A mapping of drone id (starting at 1) to its route, each
            route being a list of (zone, turn) states.

        Raises:
            ValueError: If a drone cannot be routed, which happens when
                the end zone is unreachable or when no schedule fits
                inside the time horizon.
        """
        unreachable = self.graph.unreachable_hubs()
        if unreachable:
            raise ValueError(
                "Disconnected graph — the following zones are not "
                + "reachable from the start zone: "
                + ", ".join(unreachable)
            )
        if not self.graph.is_end_reachable():
            raise ValueError(
                "End zone unreachable (blocked by a blocked zone)"
            )

        self.time_horizon = self.graph.hub_count * 2 * nb_drones
        start, end = self.graph.get_route_endpoints()

        routes: dict[int, list[State]] = {}
        for drone_idx in range(1, nb_drones + 1):
            route = self._dijkstra(start, end)
            if not route:
                raise ValueError(f"No path found for drone {drone_idx}!")

            routes[drone_idx] = route
            self._reserve_route(route)
        return routes

    def _reserve_route(self, route: list[State]) -> None:
        """Book the zones and links a route uses, turn by turn.

        Args:
            route: The accepted route, as (zone, turn) states.
        """
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
        """Search the cheapest route for one drone.

        States are (zone, turn) pairs and are popped by increasing turn
        first, so the first time the end zone comes out of the queue it
        is reached as early as possible. From a state the drone may move
        to a free neighbour, or wait one turn in place when the zone
        still has room.

        Args:
            start: Name of the zone the drone starts from.
            end: Name of the zone the drone must reach.

        Returns:
            The route as (zone, turn) states, or an empty list when the
            end zone cannot be reached within the time horizon.
        """
        priority_queue: list[tuple[int, float, str]] = [(0, 0.0, start)]

        best_cost: dict[State, float] = {(start, 0): 0}
        came_from: dict[State, State | None] = {(start, 0): None}

        while priority_queue:
            turn, cost, hub = heapq.heappop(priority_queue)

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
                    heapq.heappush(
                        priority_queue, (next_turn, next_cost, next_hub)
                    )
                    best_cost[(next_hub, next_turn)] = next_cost
                    came_from[(next_hub, next_turn)] = (hub, turn)

            wait_turn = turn + 1
            if not self._hub_full(hub, wait_turn):
                heapq.heappush(priority_queue, (wait_turn, cost, hub))
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
        """Tell whether a move would break a capacity rule.

        Both the link, for every turn of the crossing, and the
        destination zone, on arrival, are checked. The start and end
        zones have no capacity limit.

        Args:
            hub_name: Name of the destination zone.
            conn: Connection the drone would travel on.
            depart_turn: Turn the drone leaves its current zone.
            arrive_turn: Turn the drone would reach the destination.

        Returns:
            True if the move must be rejected.
        """
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
        """Check if waiting in this zone at this turn would overbook it.

        Only gates the "stay in place" move — start_hub and end_hub are
        exempt since their capacity is unlimited.

        Args:
            hub_name: Zone the drone would wait in.
            turn: Turn it would occupy that zone.

        Returns:
            True if there's no room left there at that turn.
        """
        hub = self.graph.get_hub(hub_name)
        if hub.type in ("start_hub", "end_hub"):
            return False

        return self.hub_occupancy.get((hub_name, turn), 0) >= hub.max_drones

    @staticmethod
    def _connection_key(a: str, b: str) -> tuple[str, str]:
        """Normalize a link's two endpoints into one direction-free key.

        A link is bidirectional, so a drone going a→b must book the
        same slot as one going b→a. Sorting the pair guarantees both
        directions hash to the same key.

        Args:
            a: One end of the link.
            b: The other end of the link.

        Returns:
            (a, b) if a comes first alphabetically, (b, a) otherwise.
        """
        return (a, b) if a < b else (b, a)

    @staticmethod
    def _rebuild_route(
        came_from: dict[State, State | None], end_state: State
    ) -> list[State]:
        """Retrace came_from from the goal back to the start state.

        Args:
            came_from: Maps each visited state to whatever state led to
                it (None for the start).
            end_state: The (zone, turn) the search stopped on.

        Returns:
            The path from start to end_state, in travel order — the
            walk itself goes backward, hence the final reverse.
        """
        route: list[State] = []

        curr: State | None = end_state
        while curr:
            route.append(curr)
            curr = came_from[curr]
        return route[::-1]
