from typing import Any

from models import Connection, Hub, MapConfig


class ConfigSyntaxError(Exception):
    """A map file could not be parsed.

    Carries the offending line so the message can point at the exact
    place the error came from.

    Attributes:
        line: Number of the line that failed, starting at 1.
        file_name: Path of the map file being read.
        source: Raw text of the offending line.
        message: Short description of what went wrong.
        hint: Optional longer explanation of the expected format.
    """

    def __init__(
        self,
        line: int,
        file_name: str,
        source: str,
        message: str,
        hint: str | None = None,
    ) -> None:
        """Record where and why parsing failed.

        Args:
            line: Number of the line that failed, starting at 1.
            file_name: Path of the map file being read.
            source: Raw text of the offending line.
            message: Short description of what went wrong.
            hint: Optional longer explanation of the expected format.
        """
        self.line: int = line
        self.file_name: str = file_name
        self.source: str = source
        self.message: str = message
        self.hint: str | None = hint

        super().__init__(message)

    def __str__(self) -> str:
        """Render the error with the guilty line and an optional hint.

        Returns:
            A multi line message showing the file, the line number and
            the source line the error was found on.
        """
        message = self.args[0]

        parts = [
            f"{message}",
            f" --> {self.file_name}",
            f"  {self.line - 1}|",
            f" {self.line} | {self.source.rstrip()}",
            f"  {self.line + 1}|",
        ]
        if self.hint:
            parts.append(f"  = hint: {self.hint}")

        return "\n".join(parts)


class ConfigParser:
    """Reads a map file and validates it into a MapConfig.

    The file is read line by line. Every zone must be declared before a
    connection may reference it, and any syntax or validation problem is
    reported as a ConfigSyntaxError naming the offending line.

    Attributes:
        VALID_METADATA_KEYS: Metadata keys accepted for zones and for
            connections.
        VALID_ZONE_NAMES: The four accepted zone types.
    """

    VALID_METADATA_KEYS: dict[str, frozenset[str]] = {
        "hub": frozenset(
            {
                "zone",
                "color",
                "max_drones",
            }
        ),
        "connection": frozenset({"max_link_capacity"}),
    }
    VALID_ZONE_NAMES: frozenset[str] = frozenset(
        {"normal", "blocked", "restricted", "priority"}
    )

    def __init__(self) -> None:
        """Create a parser with an empty set of seen connections."""
        self.used_connections: set[tuple[str, str]] = set()

    @staticmethod
    def _loads_file(path: str) -> list[str]:
        """Read every line of a map file.

        Args:
            path: Path of the map file to read.

        Returns:
            The lines of the file, newline characters included.

        Raises:
            OSError: If the file cannot be opened or read.
        """
        with open(path) as config_file:
            return config_file.readlines()

    @staticmethod
    def _parse_meta_attrs(keyword: str, meta_attrs: str) -> dict[str, Any]:
        """Parse the 'key=value' pairs of a metadata block.

        Keys are checked against the ones the keyword accepts, and a key
        may not be repeated on the same line. Tags may appear in any
        order.

        Args:
            keyword: Keyword the metadata belongs to, used to pick the
                accepted key set.
            meta_attrs: Content of the brackets, without the brackets.

        Returns:
            The parsed pairs, values kept as strings.

        Raises:
            ValueError: If a pair is malformed, uses an unknown key, has
                an invalid value or repeats a key.
        """
        attrs: dict[str, Any] = {}
        used_attrs: set[str] = set()

        for pair in meta_attrs.split():
            key, _, val = pair.partition("=")
            if not key or not val:
                raise ValueError(
                    "Invalid metadata format",
                    "Expected format: 'key=value'",
                )
            keyword_type = "hub" if "hub" in keyword else "connection"
            validate_metadata_keys = ConfigParser.VALID_METADATA_KEYS[
                keyword_type
            ]
            if key not in validate_metadata_keys:
                raise ValueError(
                    f"Invalid metadata key for {keyword_type}",
                    "Expected one of: "
                    + ", ".join(f"'{key}'" for key in validate_metadata_keys)
                    + f", got '{key}'",
                )
            if not val.isalnum():
                raise ValueError(
                    "Invalid value in metadata",
                    f"Expected a valid string or number, got '{val}'",
                )
            if key in used_attrs:
                raise ValueError(
                    "Duplicate metadata key",
                    f"Key '{key}' appears more than once.",
                )
            else:
                used_attrs.add(key)
            attrs[key] = val

        return attrs

    def _split_attrs(
        self, keyword: str, attrs: str
    ) -> tuple[str, dict[str, Any]]:
        """Split a line body into its plain part and its metadata.

        Args:
            keyword: Keyword the line starts with.
            attrs: Everything written after the keyword's colon.

        Returns:
            A tuple with the text before the brackets and the parsed
            metadata, the metadata being empty when no block is present.

        Raises:
            ValueError: If a metadata block is opened but never closed.
        """
        if "[" not in attrs:
            return attrs, {}

        attrs, meta_attrs = attrs.split("[", 1)
        if not meta_attrs.endswith("]"):
            raise ValueError(
                "Invalid definition:\n",
                "Expected formats:\n"
                + "\t\tzone:       '<hub type>: <name> <x> <y> [metadata]'\n"
                + "\t\tconnection: 'connection: <name1>-<name2> [metadata]'"
                + " (metadata is optional in both)",
            )
        return attrs, self._parse_meta_attrs(keyword, meta_attrs[:-1])

    def parse(self, path: str = "maps/easy/01_linear_path.txt") -> MapConfig:
        """Read a map file and validate it into a MapConfig.

        Comments and blank lines are skipped. The drone count must come
        before any zone or connection, zone names must be unique, and a
        connection may only reference zones already declared.

        Args:
            path: Path of the map file to parse.

        Returns:
            The validated map configuration.

        Raises:
            ConfigSyntaxError: If a line is malformed or invalid.
            ValueError: If the map has no start or no end zone.
            OSError: If the file cannot be opened or read.
        """
        config = MapConfig()
        used_hubs: set[str] = set()
        used_coordinates: set[tuple[int, int]] = set()

        for lineno, raw in enumerate(self._loads_file(path), start=1):
            if raw.startswith("#"):
                continue
            line = raw.split(" #")[0].strip()
            if not line:
                continue

            keyword, _, attrs = line.partition(":")
            keyword = keyword.strip()
            attrs = attrs.strip()

            try:
                if keyword == "nb_drones":
                    try:
                        config.nb_drones = int(attrs)
                        if config.nb_drones <= 0:
                            raise ValueError("Invalid value for 'nb_drones'")
                    except ValueError:
                        raise ValueError(
                            "Invalid value for 'nb_drones'",
                            f"Expected an positive integer, got '{attrs}'",
                        )

                elif keyword in {"start_hub", "end_hub", "hub", "connection"}:
                    if config.nb_drones == 0:
                        raise ValueError(
                            "Missing 'nb_drones'",
                            "Expected the number of drones to be on the first"
                            + " line: 'nb_drones: <positive_integer>'",
                        )
                    attrs, meta_attrs = self._split_attrs(keyword, attrs)
                    parts = attrs.split()
                    if keyword == "connection":
                        try:
                            (connection_name,) = parts
                        except ValueError:
                            raise ValueError(
                                "Invalid connection definition",
                                "Expected format: 'connection: <name1>-<name2>"
                                + " [metadata]' (metadata is optional)",
                            )
                        if connection_name.count("-") != 1:
                            raise ValueError(
                                "Invalid connection name",
                                "Expected a name of this format"
                                + f" <name1>-<name2>, got {connection_name}",
                            )

                        name1, name2 = connection_name.split("-")
                        if name1 not in config.hubs:
                            raise ValueError(
                                f"Unknown hub '{name1}' in connection",
                                "Connections can only link previously defined"
                                + " hubs define the hub before referencing it",
                            )
                        if name2 not in config.hubs:
                            raise ValueError(
                                f"Unknown hub '{name2}' in connection",
                                "Connections can only link previously defined"
                                + " hubs define the hub before referencing it",
                            )

                        if self.used_connection(name1, name2):
                            raise ValueError(
                                "Duplicate connection",
                                f"'{name1}-{name2}' is already defined "
                                + "(direction doesn't matter: 'a-b' and 'b-a'"
                                + " are the same link)",
                            )

                        max_link_capacity = int(
                            meta_attrs.get("max_link_capacity", 1)
                        )
                        if max_link_capacity <= 0:
                            raise ValueError(
                                "Invalid capacity value",
                                "'max_link_capacity' must be a positive"
                                + f" integer, got '{max_link_capacity}'",
                            )
                        config.connections.append(
                            Connection(
                                source=name1,
                                target=name2,
                                max_link_capacity=max_link_capacity,
                            )
                        )
                    else:
                        if len(parts) != 3:
                            raise ValueError(
                                "Invalid zone definition",
                                "Expected format: '<hub type>: <name> <x> <y>"
                                + " [metadata]' (metadata is optional)",
                            )
                        if "-" in parts[0]:
                            raise ValueError(
                                "Invalid zone name",
                                "Expected a valid alphanumeric string"
                                + f", got '{parts[0]}'",
                            )

                        if keyword in {"start_hub", "end_hub"}:
                            if keyword in used_hubs:
                                raise ValueError(
                                    "There must be exactly one 'start_hub'"
                                    + " and one 'end_hub'"
                                )
                            else:
                                used_hubs.add(keyword)

                        name, x, y = parts

                        if name in config.hubs:
                            raise ValueError(
                                "Each zone must have a unique name "
                            )

                        if (
                            meta_attrs.get("zone")
                            and meta_attrs.get("zone")
                            not in ConfigParser.VALID_ZONE_NAMES
                        ):
                            raise ValueError(
                                "Invalid zone type",
                                "Expected one of: "
                                + ", ".join(
                                    f"'{name}'"
                                    for name in ConfigParser.VALID_ZONE_NAMES
                                )
                                + f", got '{meta_attrs['zone']}'",
                            )

                        coor = (int(x), int(y))
                        if coor in used_coordinates:
                            raise ValueError(
                                "Duplicate coordinates",
                                f"Zone '{name}' reuses coordinates {coor} "
                                + "already assigned to another zone",
                            )
                        else:
                            used_coordinates.add(coor)

                        max_drones = int(meta_attrs.get("max_drones", 1))
                        if keyword == "hub" and max_drones <= 0:
                            raise ValueError(
                                "Invalid capacity value",
                                "'max_drones' must be a positive integer"
                                + f", got '{max_drones}'",
                            )

                        hub = Hub(
                            name=name,
                            x=coor[0],
                            y=coor[1],
                            type=keyword,
                            color=meta_attrs.get("color"),
                            zone=meta_attrs.get("zone", "normal"),
                            max_drones=max_drones,
                        )
                        config.hubs[hub.name] = hub

                else:
                    raise ValueError(
                        "Invalid keyword",
                        "Expected one of: 'start_hub', 'end_hub', "
                        + "'hub', 'nb_drones', 'connection'"
                        + f", got '{keyword}'",
                    )

            except (ValueError, IndexError) as e:
                raise ConfigSyntaxError(
                    lineno,
                    path,
                    raw,
                    e.args[0],
                    e.args[1] if len(e.args) > 1 else None,
                )

        missing = {"start_hub", "end_hub"} - {
            hub.type for hub in config.hubs.values()
        }
        if missing:
            raise ValueError(f"Missing {', '.join(missing)}")

        self.used_connections = set()
        return config

    def used_connection(self, source: str, target: str) -> bool:
        """Tell whether a link was already declared, and record it.

        Links are bidirectional, so 'a-b' and 'b-a' count as the same
        connection and the names are sorted before being stored.

        Args:
            source: Name of one end of the link.
            target: Name of the other end of the link.

        Returns:
            True if the link had already been seen, False otherwise. In
            the second case the link is remembered for later calls.
        """
        conn = (source, target) if source < target else (target, source)
        if conn in self.used_connections:
            return True
        self.used_connections.add(conn)
        return False
