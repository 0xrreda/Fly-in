import sys

import arcade

from algo import Algo
from config_parser import ConfigParser
from graph import Graph
from models import MapConfig
from simulation import Simulation


class App:
    """Wires the map, the router and the visualizer together.

    Attributes:
        map_config: The parsed map being run.
        graph: The map's zones and links, ready for pathfinding.
        algo: The router that computes the drones' routes.
    """

    def __init__(self, filename: str) -> None:
        """Parse the map and prepare the graph and router.

        Args:
            filename: Path to the map file to load.

        Raises:
            FileNotFoundError: If the map file doesn't exist.
            PermissionError: If the map file can't be read.
        """
        try:
            self.map_config: MapConfig = ConfigParser().parse(filename)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found — {e.filename}")
        except PermissionError as e:
            raise PermissionError(f"Permission denied reading '{e.filename}'")

        self.graph: Graph = Graph(self.map_config)
        self.algo: Algo = Algo(self.graph)

    def run(self) -> None:
        """Open the animated replay window and start the event loop."""
        _ = Simulation(
            self.map_config,
            self.algo.generate_routes(self.map_config.nb_drones),
        )

        arcade.run()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "[USAGE]: uv run main <map_path>",
            "   or    make FILE=<map_path>",
            sep="\n",
        )
        exit(1)

    try:
        App(sys.argv[1]).run()
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:
        print(f"[ERROR]: {e}")
        exit(1)
