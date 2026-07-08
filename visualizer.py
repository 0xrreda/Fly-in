"""Simple pygame visualizer for the drone routing algorithm.

Usage:
    uv run visualizer.py [map_file]

Controls:
    SPACE        play / pause
    R            restart from turn 0
    UP / DOWN    faster / slower
    LEFT / RIGHT step one turn back / forward (auto-pauses)
    ESC / close  quit
"""

import sys

import pygame

from algo import Algo
from config_parser import ConfigParser, ConfigSyntaxError
from graph import Graph
from models import Hub

State = tuple[str, int]

# --- window ---------------------------------------------------------------
WIDTH, HEIGHT = 1000, 700
MARGIN = 90
HUB_RADIUS = 26
DRONE_RADIUS = 11
FPS = 60

# --- colours --------------------------------------------------------------
BG = (13, 17, 23)
PANEL = (22, 27, 34)
LINE = (48, 54, 61)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)

ZONE_COLORS: dict[str, tuple[int, int, int]] = {
    "normal": (48, 54, 61),
    "restricted": (210, 153, 34),
    "blocked": (72, 79, 88),
    "priority": (137, 87, 229),
}
START_COLOR = (63, 185, 80)
END_COLOR = (248, 81, 73)

# distinct colours cycled across drones
DRONE_COLORS: list[tuple[int, int, int]] = [
    (88, 166, 255),
    (255, 123, 114),
    (63, 185, 80),
    (255, 196, 61),
    (210, 168, 255),
    (121, 192, 255),
    (255, 148, 112),
    (86, 211, 194),
]


def hub_zone_color(hub: Hub) -> tuple[int, int, int]:
    if hub.type == "start_hub":
        return START_COLOR
    if hub.type == "end_hub":
        return END_COLOR
    return ZONE_COLORS.get(hub.zone, ZONE_COLORS["normal"])


def build_layout(
    hubs: dict[str, Hub],
) -> dict[str, tuple[float, float]]:
    """Map grid (x, y) coordinates to screen pixels, auto-fitted."""
    xs = [h.x for h in hubs.values()]
    ys = [h.y for h in hubs.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x or 1
    span_y = max_y - min_y or 1

    usable_w = WIDTH - 2 * MARGIN
    usable_h = HEIGHT - 2 * MARGIN - 40  # leave room for the HUD strip

    layout: dict[str, tuple[float, float]] = {}
    for name, hub in hubs.items():
        fx = (hub.x - min_x) / span_x if max_x != min_x else 0.5
        fy = (hub.y - min_y) / span_y if max_y != min_y else 0.5
        px = MARGIN + fx * usable_w
        py = MARGIN + 40 + fy * usable_h
        layout[name] = (px, py)
    return layout


def drone_position(
    path: list[State],
    layout: dict[str, tuple[float, float]],
    t: float,
) -> tuple[float, float] | None:
    """Interpolated pixel position of a drone at (fractional) turn ``t``."""
    if not path:
        return None
    if t <= path[0][1]:
        return layout[path[0][0]]
    if t >= path[-1][1]:
        return layout[path[-1][0]]

    for (hub_a, turn_a), (hub_b, turn_b) in zip(path, path[1:]):
        if turn_a <= t <= turn_b:
            frac = (t - turn_a) / (turn_b - turn_a) if turn_b > turn_a else 1.0
            ax, ay = layout[hub_a]
            bx, by = layout[hub_b]
            return (ax + (bx - ax) * frac, ay + (by - ay) * frac)
    return layout[path[-1][0]]


class Visualizer:
    def __init__(self, map_file: str) -> None:
        config = ConfigParser().parse(map_file)
        self.graph = Graph(config)
        self.routes: dict[int, list[State]] = Algo(self.graph).generate_routes(
            config.nb_drones
        )
        self.map_file = map_file

        self.layout = build_layout(self.graph._hubs)
        self.max_turn = max(
            (path[-1][1] for path in self.routes.values() if path),
            default=0,
        )

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"Fly-in — {map_file}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 16)
        self.font_small = pygame.font.SysFont("monospace", 13)
        self.font_big = pygame.font.SysFont("monospace", 20, bold=True)

        self.t = 0.0
        self.speed = 1.5  # turns per second
        self.playing = True

    # -- drawing -----------------------------------------------------------
    def draw_connections(self) -> None:
        drawn: set[tuple[str, str]] = set()
        for name in self.graph._hubs:
            for neighbor, _ in self.graph.neighbors(name):
                key = (name, neighbor) if name < neighbor else (neighbor, name)
                if key in drawn:
                    continue
                drawn.add(key)
                pygame.draw.line(
                    self.screen, LINE, self.layout[name],
                    self.layout[neighbor], 3,
                )

    def draw_hubs(self) -> None:
        for name, hub in self.graph._hubs.items():
            pos = self.layout[name]
            ipos = (int(pos[0]), int(pos[1]))
            color = hub_zone_color(hub)
            pygame.draw.circle(self.screen, color, ipos, HUB_RADIUS)
            pygame.draw.circle(self.screen, TEXT, ipos, HUB_RADIUS, 2)

            label = self.font_big.render(name, True, TEXT)
            self.screen.blit(
                label, label.get_rect(center=ipos)
            )

            # capacity / zone caption under the hub
            caption = f"cap {hub.max_drones}"
            if hub.zone != "normal":
                caption = f"{hub.zone[:4]} · {caption}"
            cap = self.font_small.render(caption, True, MUTED)
            self.screen.blit(
                cap, cap.get_rect(center=(ipos[0], ipos[1] + HUB_RADIUS + 12))
            )

    def draw_drones(self) -> None:
        for drone_id, path in self.routes.items():
            pos = drone_position(path, self.layout, self.t)
            if pos is None:
                continue
            color = DRONE_COLORS[(drone_id - 1) % len(DRONE_COLORS)]
            ipos = (int(pos[0]), int(pos[1]))

            arrived = self.t >= path[-1][1]
            radius = DRONE_RADIUS + (0 if arrived else 1)
            pygame.draw.circle(self.screen, color, ipos, radius)
            pygame.draw.circle(self.screen, BG, ipos, radius, 2)

            tag = self.font_small.render(str(drone_id), True, BG)
            self.screen.blit(tag, tag.get_rect(center=ipos))

    def draw_hud(self) -> None:
        # top strip: turn + status
        turn = min(self.t, self.max_turn)
        arrived = sum(
            1 for p in self.routes.values() if p and self.t >= p[-1][1]
        )
        status = "PLAYING" if self.playing else "PAUSED"
        header = (
            f"turn {turn:5.1f} / {self.max_turn}   "
            f"speed x{self.speed:.1f}   "
            f"arrived {arrived}/{len(self.routes)}   [{status}]"
        )
        self.screen.blit(self.font.render(header, True, TEXT), (MARGIN, 22))

        # bottom strip: per-drone legend + controls
        y = HEIGHT - 46
        x = MARGIN
        for drone_id, path in self.routes.items():
            color = DRONE_COLORS[(drone_id - 1) % len(DRONE_COLORS)]
            pygame.draw.circle(self.screen, color, (x + 6, y + 6), 6)
            info = f"D{drone_id}: {path[-1][1]}t"
            surf = self.font_small.render(info, True, MUTED)
            self.screen.blit(surf, (x + 18, y))
            x += 22 + surf.get_width() + 16
            if x > WIDTH - 160:
                x = MARGIN
                y += 20

        controls = "SPACE play/pause   R restart   UP/DOWN speed   " \
            "LEFT/RIGHT step   ESC quit"
        surf = self.font_small.render(controls, True, MUTED)
        self.screen.blit(surf, (MARGIN, HEIGHT - 22))

    # -- loop --------------------------------------------------------------
    def step(self, delta: int) -> None:
        self.playing = False
        self.t = max(0.0, min(float(round(self.t) + delta), self.max_turn))

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if self.t >= self.max_turn:
                            self.t = 0.0
                        self.playing = not self.playing
                    elif event.key == pygame.K_r:
                        self.t = 0.0
                        self.playing = True
                    elif event.key == pygame.K_UP:
                        self.speed = min(self.speed + 0.5, 10.0)
                    elif event.key == pygame.K_DOWN:
                        self.speed = max(self.speed - 0.5, 0.5)
                    elif event.key == pygame.K_RIGHT:
                        self.step(1)
                    elif event.key == pygame.K_LEFT:
                        self.step(-1)

            if self.playing:
                self.t += self.speed * dt
                if self.t >= self.max_turn:
                    self.t = self.max_turn
                    self.playing = False

            self.screen.fill(BG)
            self.draw_connections()
            self.draw_hubs()
            self.draw_drones()
            self.draw_hud()
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    map_file = sys.argv[1] if len(sys.argv) > 1 else "./map.txt"
    try:
        Visualizer(map_file).run()
    except FileNotFoundError as e:
        print(f"[ERROR]: File not found — {e.filename}")
        sys.exit(1)
    except ConfigSyntaxError as e:
        print(f"[ERROR]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
