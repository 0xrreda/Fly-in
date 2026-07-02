from algo import Algo
from config_parser import ConfigParser, ConfigSyntaxError
from graph import Graph


if __name__ == "__main__":
    try:
        config = ConfigParser().parse(
            "./maps/challenger/01_the_impossible_dream.txt"
        )
    except FileNotFoundError as e:
        print(f"[ERROR]: File not found — {e.filename}")
        exit(1)
    except PermissionError as e:
        print(f"[ERROR]: Permission denied reading '{e.filename}'")
        exit(1)
    except ConfigSyntaxError as e:
        print(f"[ERROR]: {e}")
        exit(1)

    graph = Graph(config)

    routes = Algo(graph).generate_routes(config.nb_drones)

    for drone_id, route in routes.items():
        print(f"{drone_id}: {route}\n")
