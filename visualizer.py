"""Minimal Arcade visualizer — watch drones move between hubs.

Usage:
    uv run visualizer.py [map_file]

Controls:
    SPACE: Pause or resume
    R: Restart
    Q or ESCAPE: Quit
"""

import sys

import arcade

from algo import Algo
from config_parser import ConfigParser
from graph import Graph

WIDTH = 1800
HEIGHT = 800
MARGIN = 80
SPEED = 1.5  # Turns per second


def build_layout(hubs):
    """Convert grid coordinates into screen coordinates."""
    xs = [hub.x for hub in hubs.values()]
    ys = [hub.y for hub in hubs.values()]

    min_x = min(xs)
    min_y = min(ys)

    scale_x = (max(xs) - min_x) or 1
    scale_y = (max(ys) - min_y) or 1

    layout = {}

    for name, hub in hubs.items():
        pixel_x = MARGIN + (hub.x - min_x) / scale_x * (WIDTH - 2 * MARGIN)
        pixel_y = MARGIN + (hub.y - min_y) / scale_y * (HEIGHT - 2 * MARGIN)

        # Flip the y-coordinate so that up matches the map.
        layout[name] = (pixel_x, HEIGHT - pixel_y)

    return layout


def drone_pos(path, layout, current_time):
    """Return the interpolated position of a drone."""
    if current_time <= path[0][1]:
        first_hub = path[0][0]
        return layout[first_hub]

    if current_time >= path[-1][1]:
        last_hub = path[-1][0]
        return layout[last_hub]

    for (start_hub, start_time), (end_hub, end_time) in zip(
        path,
        path[1:],
    ):
        if start_time <= current_time <= end_time:
            if end_time > start_time:
                fraction = (current_time - start_time) / (
                    end_time - start_time
                )
            else:
                fraction = 1.0

            start_x, start_y = layout[start_hub]
            end_x, end_y = layout[end_hub]

            x = start_x + (end_x - start_x) * fraction
            y = start_y + (end_y - start_y) * fraction

            return x, y

    last_hub = path[-1][0]
    return layout[last_hub]


class Visualizer(arcade.Window):
    """Window that displays hubs, connections, and moving drones."""

    def __init__(self, map_file):
        super().__init__(
            WIDTH,
            HEIGHT,
            f"Fly-in — {map_file}",
        )

        config = ConfigParser().parse(map_file)

        self.graph = Graph(config)
        self.routes = Algo(self.graph).generate_routes(config.nb_drones)
        self.layout = build_layout(self.graph._hubs)

        self.max_turn = max(
            path[-1][1] for path in self.routes.values() if path
        )

        self.current_time = 0.0
        self.playing = True

        arcade.set_background_color((13, 17, 23))

    def on_update(self, delta_time):
        """Update the simulation time."""
        if self.playing:
            self.current_time = min(
                self.current_time + SPEED * delta_time,
                self.max_turn,
            )

    def on_draw(self):
        """Draw the graph and drones."""
        self.clear()

        self.draw_connections()
        self.draw_hubs()
        self.draw_drones()
        self.draw_status()

    def draw_connections(self):
        """Draw connections between neighboring hubs."""
        for name in self.graph._hubs:
            for neighbor, _distance in self.graph.neighbors(name):
                # Prevent each undirected connection from being drawn twice.
                if name < neighbor:
                    start_x, start_y = self.layout[name]
                    end_x, end_y = self.layout[neighbor]

                    arcade.draw_line(
                        start_x,
                        start_y,
                        end_x,
                        end_y,
                        (48, 54, 61),
                        2,
                    )

    def draw_hubs(self):
        """Draw every hub and its name."""
        for name, position in self.layout.items():
            x, y = position

            arcade.draw_circle_filled(
                x,
                y,
                22,
                (48, 54, 61),
            )
            arcade.draw_circle_outline(
                x,
                y,
                22,
                (230, 237, 243),
                2,
            )
            arcade.draw_text(
                name,
                x,
                y - 36,
                (230, 237, 243),
                8,
                anchor_x="center",
                anchor_y="center",
            )

    def draw_drones(self):
        """Draw every drone at its current position."""
        for drone_id, path in self.routes.items():
            if not path:
                continue

            x, y = drone_pos(
                path,
                self.layout,
                self.current_time,
            )

            arcade.draw_circle_filled(
                x,
                y,
                10,
                (88, 166, 255),
            )
            arcade.draw_text(
                str(drone_id),
                x,
                y,
                (13, 17, 23),
                12,
                anchor_x="center",
                anchor_y="center",
            )

    def draw_status(self):
        """Draw the current simulation turn."""
        arcade.draw_text(
            f"Turn {self.current_time:.1f} / {self.max_turn}",
            MARGIN,
            HEIGHT - 30,
            (230, 237, 243),
            16,
        )

    def on_key_press(self, key, _modifiers):
        """Handle keyboard controls."""
        if key == arcade.key.SPACE:
            self.playing = not self.playing

        elif key == arcade.key.R:
            self.current_time = 0.0
            self.playing = True

        elif key in (arcade.key.ESCAPE, arcade.key.Q):
            self.close()


def main():
    """Load the map and start the visualizer."""
    if len(sys.argv) > 1:
        map_file = sys.argv[1]
    else:
        map_file = "./map.txt"

    Visualizer(map_file)
    arcade.run()


if __name__ == "__main__":
    main()
