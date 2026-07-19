import sys

import arcade

from algo import Algo
from config_parser import ConfigParser, ConfigSyntaxError
from graph import Graph
from simulation import Simulation

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "[USAGE]: uv run main <map_path>",
            "   or    make FILE=<map_path>",
            sep="\n",
        )
        exit(1)

    try:
        map_config = ConfigParser().parse(sys.argv[1] or "")
    except FileNotFoundError as e:
        print(f"[ERROR]: File not found — {e.filename}")
        exit(1)
    except PermissionError as e:
        print(f"[ERROR]: Permission denied reading '{e.filename}'")
        exit(1)
    except ConfigSyntaxError as e:
        print(f"[ERROR]: {e}")
        exit(1)

    graph = Graph(map_config)

    try:
        routes = Algo(graph).generate_routes(map_config.nb_drones)
    except ValueError as e:
        print(f"[ERROR]: {e}")
        exit(1)

    try:
        _ = Simulation(map_config, routes)
        arcade.run()
    except (KeyboardInterrupt, EOFError):
        pass
