from dataclasses import dataclass, field


@dataclass
class Hub:
    """One zone of the drone network, as parsed from a map file.

    Attributes:
        name: Unique zone identifier.
        x: Map x coordinate (not a screen pixel — Simulation remaps it).
        y: Map y coordinate.
        type: 'start_hub', 'end_hub' or plain 'hub'.
        color: Optional color name, purely for the visualization.
        max_drones: Simultaneous occupancy limit. start_hub/end_hub
            ignore this — they're always unlimited.
        zone: Movement behaviour: 'normal', 'blocked', 'restricted' or
            'priority'. Drives both pathfinding cost and duration.
    """

    name: str
    x: int
    y: int
    type: str
    color: str | None = None
    max_drones: int = 1
    zone: str = "normal"


@dataclass
class Connection:
    """A link between two zones — bidirectional despite the naming.

    Attributes:
        source: One endpoint's zone name.
        target: The other endpoint's zone name.
        max_link_capacity: Drones allowed to cross it in the same turn.
    """

    source: str
    target: str
    max_link_capacity: int = 1


@dataclass
class MapConfig:
    """Everything ConfigParser extracts from one map file.

    Attributes:
        nb_drones: How many drones need routing, start to end.
        hubs: Every zone, keyed by name for O(1) lookup.
        connections: Every declared link, in file order.
    """

    nb_drones: int = 0
    hubs: dict[str, Hub] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
