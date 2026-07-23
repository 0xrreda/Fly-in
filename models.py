from dataclasses import dataclass, field


@dataclass
class Hub:
    """A single zone of the drone network.

    Attributes:
        name: Unique zone identifier.
        x: Integer x coordinate, used to lay the zone out on screen.
        y: Integer y coordinate, used to lay the zone out on screen.
        type: Role of the zone: 'start_hub', 'end_hub' or 'hub'.
        color: Optional color name used by the visualization.
        max_drones: How many drones may occupy the zone at once. It is
            ignored on the start and end hubs, which are unlimited.
        zone: Movement type of the zone: 'normal', 'blocked',
            'restricted' or 'priority'.
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
    """A bidirectional link between two zones.

    Attributes:
        source: Name of the first linked zone.
        target: Name of the second linked zone.
        max_link_capacity: How many drones may traverse the link at the
            same turn.
    """

    source: str
    target: str
    max_link_capacity: int = 1


@dataclass
class MapConfig:
    """The full content of a parsed map file.

    Attributes:
        nb_drones: Number of drones to route from start to end.
        hubs: Every zone of the map, keyed by zone name.
        connections: Every link declared between two zones.
    """

    nb_drones: int = 0
    hubs: dict[str, Hub] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
