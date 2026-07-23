import warnings

import arcade
import webcolors
from arcade.exceptions import PerformanceWarning

from algo import State
from models import Hub, MapConfig

warnings.filterwarnings("ignore", category=PerformanceWarning)


class Simulation(arcade.Window):
    """Animated window replaying the routes, plus the text output.

    Zone coordinates are remapped to screen, then drones are
    drawn, so the animation stays smooth between two turns.

    Attributes:
        WIDTH: Window width in pixels.
        HEIGHT: Window height in pixels.
        MARGIN: Free space kept around the drawn network, in pixels.
        SPEED: How many simulation turns pass per real second.
    """

    WIDTH: int = 1800
    HEIGHT: int = 780
    MARGIN: int = 64
    SPEED: float = 1

    def __init__(
        self, map_config: MapConfig, routes: dict[int, list[State]]
    ) -> None:
        """Prepare the window and print the simulation output.

        Args:
            map_config: The parsed map being replayed.
            routes: One route per drone, as (zone, turn) states.
        """
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
        """Tick the simulation clock forward, unless paused.

        Args:
            delta_time: Real seconds since the last frame — arcade
                measures this, it isn't a fixed 1/60.
        """
        if self.playing:
            self.simulation_time += Simulation.SPEED * delta_time

    def on_draw(self) -> None:
        """Redraw the frame: network, drones, then the turn counter."""
        self.clear()
        self._draw_connections()
        self._draw_hubs()
        self._draw_drones()
        self._draw_counter()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Route the playback shortcuts.

        R rewinds to turn zero, SPACE toggles play/pause, and Q or
        ESCAPE quits.

        Args:
            symbol: Key that triggered the event.
            modifiers: Held modifier keys — unused, arcade requires the
                parameter regardless.
        """
        if symbol == arcade.key.R:
            self.simulation_time = 0.0

        if symbol == arcade.key.SPACE:
            self.playing = not self.playing

        if symbol in (arcade.key.ESCAPE, arcade.key.Q):
            self.close()

    def _draw_connections(self) -> None:
        """Draw one line per link in the network."""
        for conn in self.map_config.connections:
            arcade.draw_line(
                *self.layout[conn.source],
                *self.layout[conn.target],
                (244, 219, 214),
                2,
            )

    def _draw_hubs(self) -> None:
        """Draw every zone as a labelled circle.

        A zone with a recognized color name gets filled with it, so the
        map's own metadata shows up on screen instead of a flat
        placeholder. Labels alternate above/below each circle so
        neighbouring labels don't stack on top of each other.
        """
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
        """Draw each drone as a numbered dot at its current position."""
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
        """Draw 'Turn X / N' in the corner, clamped once playback ends."""
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
        """Compute where a drone is at the current simulation time.

        The position is interpolated between the two zones surrounding
        the current time, which also places drones halfway along a link
        while they cross toward a restricted zone.

        Args:
            path: The drone's route, as (zone, turn) states.

        Returns:
            The drone's (x, y) position in screen coordinates.
        """
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
        """Scale the map coordinates to fit the window.

        The y axis is flipped, because map coordinates grow upward while
        screen coordinates grow downward.

        Args:
            hubs: Every zone of the map, keyed by zone name.

        Returns:
            The (x, y) screen position of each zone, keyed by name.
        """
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
        """Rescale a value from one range to another.

        Args:
            value: The value to rescale.
            in_min: Lower bound of the source range.
            in_max: Upper bound of the source range.
            out_min: Lower bound of the target range.
            out_max: Upper bound of the target range.

        Returns:
            The rescaled value, or the middle of the target range when
            the source range is empty.
        """
        if in_min == in_max:
            return (out_max + out_min) / 2
        frac = (value - in_min) / (in_max - in_min)
        return out_min + frac * (out_max - out_min)

    def simulation_output(self) -> None:
        """Print the routes using the subject's output format.

        One line per turn, listing that turn's movements as
        'D<id>-<zone>' tokens. While a drone crosses toward a restricted
        zone the intermediate turn is reported as 'D<id>-<from>-<to>',
        the link being named after the two zones it joins. Drones that
        stay in place are left out, and a drone that reached the end
        zone is no longer reported.
        """
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
