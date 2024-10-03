import argparse

from unicode_rbnf import RbnfEngine, RulesetName


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--language",
        choices=RbnfEngine.get_supported_languages(),
        required=True,
        help="Language code",
    )
    parser.add_argument(
        "--rule",
        choices=[v.value for v in RulesetName],
        help="Ruleset name",
    )
    parser.add_argument("number", nargs="+", help="Number(s) to turn into words")
    args = parser.parse_args()

    engine = RbnfEngine.for_language(args.language)
    for number_str in args.number:
        words = engine.format_number(number_str, ruleset_name=args.rule)
        print(words)


if __name__ == "__main__":
    main()
