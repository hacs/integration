"""CLI tool for sampling sentences from a template."""

import argparse
import logging

from .parse_expression import parse_sentence
from .sample import sample_expression

_LOGGER = logging.getLogger("hassil.sample_template")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("sentence", help="Sentence template")
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to the console"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)
    _LOGGER.debug(args)

    sentence = parse_sentence(args.sentence)
    for text in sample_expression(sentence):
        print(text)


if __name__ == "__main__":
    main()
