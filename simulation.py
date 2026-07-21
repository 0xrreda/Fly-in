import warnings

import arcade
import webcolors
from arcade.exceptions import PerformanceWarning

from algo import State
from models import Hub, MapConfig

warnings.filterwarnings("ignore", category=PerformanceWarning)


class Simulation(arcade.Window):
    WIDTH: int = 1800
    HEIGHT: int = 780
    MARGIN: int = 64
    SPEED: float = 1

    def __init__(
        self, map_config: MapConfig, routes: dict[int, list[State]]
    ) -> None:
        super().__init__(Simulation.WIDTH, Simulation.HEIGHT, "Fly-in")
        self.background_color = (36, 39, 58)

        self.map_config: MapConfig = map_config

        self.layout: dict[str, tuple[float, float]] = self._build_layout(
            self.map_config.hubs
        )
        self.simulation_time: float = 0.0
        self.playing: bool = True

        self.routes: dict[int, list[State]] = routes
        self.total_turns: int = max(
            path[-1][1] for path in self.routes.values()
        )

        self.simulation_output()

    def on_update(self, delta_time: float) -> None:
        if self.playing:
            self.simulation_time += Simulation.SPEED * delta_time

    def on_draw(self) -> None:
        self.clear()
        self._draw_connections()
        self._draw_hubs()
        self._draw_drones()
        self._draw_counter()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.R:
            self.simulation_time = 0.0

        if symbol == arcade.key.SPACE:
            self.playing = not self.playing

        if symbol in (arcade.key.ESCAPE, arcade.key.Q):
            self.close()

    def _draw_connections(self) -> None:
        for conn in self.map_config.connections:
            arcade.draw_line(
                *self.layout[conn.source],
                *self.layout[conn.target],
                (244, 219, 214),
                2,
            )

    def _draw_hubs(self) -> None:
        for idx, (name, (x, y)) in enumerate(self.layout.items()):
            add_by = -40 if idx % 2 == 0 else 40

            hub_color = (145, 215, 227)
            if self.map_config.hubs[name].color in webcolors.names():
                hub_color = webcolors.name_to_rgb(
                    str(self.map_config.hubs[name].color)
                )

            arcade.draw_circle_filled(x, y, 24, hub_color)
            arcade.draw_circle_outline(x, y, 24, (244, 219, 214), 2)
            arcade.draw_text(
                name,
                x,
                y + add_by,
                (202, 211, 245),
                10,
                bold=True,
                anchor_x="center",
            )

    def _draw_drones(self) -> None:
        for drone_id, path in self.routes.items():
            x, y = self._drone_position(path)

            arcade.draw_circle_filled(
                x,
                y,
                12,
                (24, 25, 38),
            )
            arcade.draw_text(
                str(drone_id),
                x,
                y,
                (202, 211, 245),
                8,
                anchor_x="center",
                anchor_y="center",
            )

    def _draw_counter(self) -> None:
        turn = min(int(self.simulation_time), self.total_turns)
        arcade.draw_text(
            f"Turn {turn} / {self.total_turns}",
            Simulation.MARGIN,
            Simulation.HEIGHT - Simulation.MARGIN,
            (202, 211, 245),
            16,
            bold=True,
        )

    def _drone_position(self, path: list[State]) -> tuple[float, float]:
        if self.simulation_time >= path[-1][1]:
            return self.layout[path[-1][0]]

        for (prev_hub, prev_turn), (hub, turn) in zip(path, path[1:]):
            if prev_turn <= self.simulation_time <= turn:
                xa, ya = self.layout[prev_hub]
                xb, yb = self.layout[hub]

                return (
                    self._remap(self.simulation_time, prev_turn, turn, xa, xb),
                    self._remap(self.simulation_time, prev_turn, turn, ya, yb),
                )

        return self.layout[path[0][0]]

    @staticmethod
    def _build_layout(
        hubs: dict[str, Hub],
    ) -> dict[str, tuple[float, float]]:
        xs = [hub.x for hub in hubs.values()]
        ys = [hub.y for hub in hubs.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        layout: dict[str, tuple[float, float]] = {}
        for name, hub in hubs.items():
            layout[name] = (
                Simulation._remap(
                    hub.x,
                    min_x,
                    max_x,
                    Simulation.MARGIN,
                    Simulation.WIDTH - Simulation.MARGIN,
                ),
                Simulation._remap(
                    hub.y,
                    min_y,
                    max_y,
                    Simulation.HEIGHT - Simulation.MARGIN,
                    Simulation.MARGIN,
                ),
            )
        return layout

    @staticmethod
    def _remap(
        value: float,
        in_min: float,
        in_max: float,
        out_min: float,
        out_max: float,
    ) -> float:
        if in_min == in_max:
            return (out_max + out_min) / 2
        frac = (value - in_min) / (in_max - in_min)
        return out_min + frac * (out_max - out_min)

    def simulation_output(self) -> None:
        moves_by_turn: dict[int, list[str]] = {}

        for drone_id, route in self.routes.items():
            for (prev_hub, prev_turn), (hub, turn) in zip(route, route[1:]):
                if prev_hub == hub:
                    continue

                if turn - prev_turn == 2:
                    moves_by_turn.setdefault(turn - 1, []).append(
                        f"D{drone_id}-{prev_hub}-{hub}"
                    )
                moves_by_turn.setdefault(turn, []).append(f"D{drone_id}-{hub}")

        for turn in range(1, self.total_turns + 1):
            print(" ".join(moves_by_turn.get(turn, [])))
