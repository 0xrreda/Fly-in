from dataclasses import dataclass, field


@dataclass
class Hub:
    name: str
    x: int
    y: int
    type: str
    color: str | None = None
    max_drones: int = 1
    zone: str = "normal"


@dataclass
class Connection:
    source: str
    target: str
    max_link_capacity: int = 1


@dataclass
class MapConfig:
    nb_drones: int = 0
    hubs: dict[str, Hub] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
