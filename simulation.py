import arcade

from algo import State
from models import Hub, MapConfig


class Simulation(arcade.Window):
    WIDTH: int = 1800
    HEIGHT: int = 780
    MARGIN: int = 64
    SPEED: float = 1

    def __init__(
        self, map_config: MapConfig, routes: dict[int, list[State]]
    ) -> None:
        super().__init__(Simulation.WIDTH, Simulation.HEIGHT, "Fly-in")
        self.background_color = 30, 30, 46

        self.map_config: MapConfig = map_config

        self.layout: dict[str, tuple[float, float]] = self.build_layout(
            self.map_config.hubs
        )
        self.simulation_time: float = 0.0
        self.playing: bool = True

        self.routes: dict[int, list[State]] = routes
        self.total_turns: int = max(
            path[-1][1] for path in self.routes.values()
        )

    def on_update(self, delta_time: float) -> None:
        if self.playing:
            self.simulation_time += Simulation.SPEED * delta_time

    def on_draw(self) -> None:
        self.clear()
        self.draw_connections()
        self.draw_hubs()
        self.draw_drones()
        self.draw_counter()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.R:
            self.simulation_time = 0.0

        if symbol == arcade.key.SPACE:
            self.playing = not self.playing

        if symbol in (arcade.key.ESCAPE, arcade.key.Q):
            self.close()

    def draw_connections(self) -> None:
        for conn in self.map_config.connections:
            arcade.draw_line(
                *self.layout[conn.source],
                *self.layout[conn.target],
                (205, 214, 244),
                2,
            )

    def draw_hubs(self) -> None:
        for idx, (name, (x, y)) in enumerate(self.layout.items()):
            add_by = -40 if idx % 2 == 0 else 40

            arcade.draw_circle_filled(x, y, 24, (137, 180, 250))
            arcade.draw_circle_outline(x, y, 24, (205, 214, 244), 2)
            arcade.draw_text(
                name,
                x,
                y + add_by,
                (186, 194, 222),
                10,
                bold=True,
                anchor_x="center",
            )

    def draw_drones(self) -> None:
        for drone_id, path in self.routes.items():
            x, y = self.drone_position(path)

            arcade.draw_circle_filled(
                x,
                y,
                12,
                (250, 179, 135),
            )
            arcade.draw_text(
                str(drone_id),
                x,
                y,
                (49, 50, 68),
                8,
                anchor_x="center",
                anchor_y="center",
            )

    def draw_counter(self) -> None:
        turn = min(int(self.simulation_time), self.total_turns)
        arcade.draw_text(
            f"Turn {turn} / {self.total_turns}",
            Simulation.WIDTH - Simulation.MARGIN * 2,
            Simulation.HEIGHT - Simulation.MARGIN,
            (186, 194, 222),
            16,
            bold=True,
            anchor_x="center",
        )

    def drone_position(self, path: list[State]) -> tuple[float, float]:
        if self.simulation_time <= path[0][1]:
            first_hub = path[0][0]
            return self.layout[first_hub]

        if self.simulation_time >= path[-1][1]:
            last_hub = path[-1][0]
            return self.layout[last_hub]

        for (start_hub, start_turn), (end_hub, end_turn) in zip(
            path, path[1:]
        ):
            if start_turn <= self.simulation_time <= end_turn:
                x_a, y_a = self.layout[start_hub]
                x_b, y_b = self.layout[end_hub]
                x = Simulation.remap(
                    self.simulation_time, start_turn, end_turn, x_a, x_b
                )
                y = Simulation.remap(
                    self.simulation_time, start_turn, end_turn, y_a, y_b
                )
                return (x, y)

        return self.layout[path[0][0]]

    @staticmethod
    def build_layout(
        hubs: dict[str, Hub],
    ) -> dict[str, tuple[float, float]]:
        xs = [hub.x for hub in hubs.values()]
        ys = [hub.y for hub in hubs.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        layout: dict[str, tuple[float, float]] = {}
        for name, hub in hubs.items():
            layout[name] = (
                Simulation.remap(
                    hub.x,
                    min_x,
                    max_x,
                    Simulation.MARGIN,
                    Simulation.WIDTH - Simulation.MARGIN,
                ),
                Simulation.remap(
                    hub.y,
                    min_y,
                    max_y,
                    Simulation.HEIGHT - Simulation.MARGIN,
                    Simulation.MARGIN,
                ),
            )
        return layout

    @staticmethod
    def remap(
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
