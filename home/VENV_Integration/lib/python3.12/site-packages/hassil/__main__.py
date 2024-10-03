"""Command-line interface to hassil."""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from .intents import Intents, TextSlotList
from .recognize import recognize
from .util import merge_dict

_LOGGER = logging.getLogger("hassil")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", nargs="+", help="YAML files or directories")
    parser.add_argument(
        "--areas",
        nargs="+",
        help="Area names",
        default=[],
    )
    parser.add_argument("--names", nargs="+", default=[], help="Device/entity names")
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to the console"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)
    _LOGGER.debug(args)

    slot_lists = {
        "area": TextSlotList.from_strings(args.areas),
        "name": TextSlotList.from_strings(args.names),
    }

    input_dict = {"intents": {}}
    for yaml_path_str in args.yaml:
        yaml_path = Path(yaml_path_str)
        if yaml_path.is_dir():
            yaml_file_paths = yaml_path.glob("*.yaml")
        else:
            yaml_file_paths = [yaml_path]

        for yaml_file_path in yaml_file_paths:
            _LOGGER.debug("Loading file: %s", yaml_file_path)
            with open(yaml_file_path, "r", encoding="utf-8") as yaml_file:
                merge_dict(input_dict, yaml.safe_load(yaml_file))

    assert input_dict, "No intent YAML files loaded"
    intents = Intents.from_dict(input_dict)

    _LOGGER.info("Area names: %s", args.areas)
    _LOGGER.info("Device/Entity names: %s", args.names)

    if os.isatty(sys.stdout.fileno()):
        print("Reading sentences from stdin...", file=sys.stderr)

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                result = recognize(line, intents, slot_lists=slot_lists)
                if result is not None:
                    print(
                        {
                            "intent": result.intent.name,
                            **{e.name: e.value for e in result.entities_list},
                        }
                    )
                else:
                    print("<no match>")
            except Exception:
                _LOGGER.exception(line)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
