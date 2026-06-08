from typing import Any

from models import Connection, MapConfig, Hub


class ConfigSyntaxError(Exception):
    def __init__(
        self,
        line: int,
        file_name: str,
        source: str,
        message: str,
        hint: str | None = None,
    ) -> None:
        self.line: int = line
        self.file_name: str = file_name
        self.source: str = source
        self.message: str = message
        self.hint: str | None = hint

        super().__init__(message)

    def __str__(self) -> str:
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

    @staticmethod
    def _loads_file(path: str) -> list[str]:
        with open(path) as config_file:
            return config_file.readlines()

    @staticmethod
    def _parse_meta_attrs(keyword: str, meta_attrs: str) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
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
            attrs[key] = val

        return attrs

    def _split_attrs(
        self, keyword: str, attrs: str
    ) -> tuple[str, dict[str, Any]]:
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
        return attrs, self._parse_meta_attrs(
            keyword, meta_attrs.lstrip("[").rstrip("]")
        )

    def parse(self, path: str = "maps/easy/01_linear_path.txt") -> MapConfig:
        config = MapConfig()
        used_hubs: set[str] = set()

        for lineno, raw in enumerate(self._loads_file(path), start=1):
            line = raw.split("#")[0].strip()
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
                        config.connections.append(
                            Connection(
                                source=name1,
                                target=name2,
                                max_link_capacity=int(
                                    meta_attrs.get("max_link_capacity", 1)
                                ),
                            )
                        )
                    else:
                        if len(parts) != 3:
                            raise ValueError(
                                "Invalid zone definition",
                                "Expected format: '<hub type>: <name> <x> <y>"
                                + " [metadata]' (metadata is optional)",
                            )
                        if not parts[0].isalnum():
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
                        if int(x) < 0 or int(y) < 0:
                            raise ValueError(
                                "Each zone must have a valid coordinates"
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
                        hub = Hub(
                            name=name,
                            x=int(x),
                            y=int(y),
                            type=keyword,
                            color=meta_attrs.get("color", "none"),
                            zone=meta_attrs.get("zone", "normal"),
                            max_drones=int(meta_attrs.get("max_drones", 1)),
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

        return config
