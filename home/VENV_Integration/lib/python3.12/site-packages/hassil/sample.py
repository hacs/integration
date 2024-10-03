"""CLI tool for sampling sentences from intents."""

import argparse
import itertools
import json
import logging
import sys
from functools import partial
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

import yaml
from unicode_rbnf import RbnfEngine

from .expression import (
    Expression,
    ListReference,
    RuleReference,
    Sentence,
    Sequence,
    SequenceType,
    TextChunk,
)
from .intents import Intents, RangeSlotList, SlotList, TextSlotList, WildcardSlotList
from .recognize import MissingListError, MissingRuleError
from .util import merge_dict, normalize_whitespace

_LOGGER = logging.getLogger("hassil.sample")

# lang -> engine
_ENGINE_CACHE: Dict[str, RbnfEngine] = {}


def sample_intents(
    intents: Intents,
    slot_lists: Optional[Dict[str, SlotList]] = None,
    expansion_rules: Optional[Dict[str, Sentence]] = None,
    max_sentences_per_intent: Optional[int] = None,
    intent_names: Optional[Set[str]] = None,
    language: Optional[str] = None,
    exclude_sentences_with_wildcards: bool = True,
    expand_ranges: bool = True,
) -> Iterable[Tuple[str, str]]:
    """Sample text strings for sentences from intents."""
    if slot_lists is None:
        slot_lists = intents.slot_lists
    else:
        # Combine with intents
        slot_lists = {**intents.slot_lists, **slot_lists}

    if slot_lists is None:
        slot_lists = {}

    if expansion_rules is None:
        expansion_rules = intents.expansion_rules
    else:
        # Combine rules
        expansion_rules = {**intents.expansion_rules, **expansion_rules}

    for intent_name, intent in intents.intents.items():
        if intent_names and (intent_name not in intent_names):
            # Skip intent
            continue

        num_intent_sentences = 0
        skip_intent = False

        for intent_data in intent.data:
            if intent_data.expansion_rules:
                local_expansion_rules = {
                    **expansion_rules,
                    **intent_data.expansion_rules,
                }
            else:
                local_expansion_rules = expansion_rules

            for intent_sentence in intent_data.sentences:
                if exclude_sentences_with_wildcards and any(
                    list_name in intent_data.wildcard_list_names
                    for list_name in intent_sentence.list_names(local_expansion_rules)
                ):
                    continue

                sentence_texts = sample_expression(
                    intent_sentence,
                    slot_lists,
                    local_expansion_rules,
                    language=language,
                    expand_ranges=expand_ranges,
                )
                for sentence_text in sentence_texts:
                    yield (intent_name, sentence_text)
                    num_intent_sentences += 1

                    if (max_sentences_per_intent is not None) and (
                        0 < max_sentences_per_intent <= num_intent_sentences
                    ):
                        skip_intent = True
                        break

                if skip_intent:
                    break

            if skip_intent:
                break


def sample_expression(
    expression: Expression,
    slot_lists: Optional[Dict[str, SlotList]] = None,
    expansion_rules: Optional[Dict[str, Sentence]] = None,
    language: Optional[str] = None,
    expand_ranges: bool = True,
) -> Iterable[str]:
    """Sample possible text strings from an expression."""
    if isinstance(expression, TextChunk):
        chunk: TextChunk = expression
        yield chunk.original_text
    elif isinstance(expression, Sequence):
        seq: Sequence = expression
        if seq.type == SequenceType.ALTERNATIVE:
            for item in seq.items:
                yield from sample_expression(
                    item,
                    slot_lists,
                    expansion_rules,
                    language=language,
                    expand_ranges=expand_ranges,
                )
        elif seq.type == SequenceType.GROUP:
            seq_sentences = map(
                partial(
                    sample_expression,
                    slot_lists=slot_lists,
                    expansion_rules=expansion_rules,
                    language=language,
                    expand_ranges=expand_ranges,
                ),
                seq.items,
            )
            sentence_texts = itertools.product(*seq_sentences)
            for sentence_words in sentence_texts:
                yield normalize_whitespace("".join(sentence_words))
        else:
            raise ValueError(f"Unexpected sequence type: {seq}")
    elif isinstance(expression, ListReference):
        # {list}
        list_ref: ListReference = expression
        if (not slot_lists) or (list_ref.list_name not in slot_lists):
            raise MissingListError(f"Missing slot list {{{list_ref.list_name}}}")

        slot_list = slot_lists[list_ref.list_name]
        if isinstance(slot_list, TextSlotList):
            text_list: TextSlotList = slot_list

            if not text_list.values:
                # Not necessarily an error, but may be a surprise
                _LOGGER.warning("No values for list: %s", list_ref.list_name)

            for text_value in text_list.values:
                yield from sample_expression(
                    text_value.text_in,
                    slot_lists,
                    expansion_rules,
                    language=language,
                    expand_ranges=expand_ranges,
                )
        elif isinstance(slot_list, RangeSlotList):
            range_list: RangeSlotList = slot_list

            if not expand_ranges:
                if range_list.name:
                    yield f"{{{range_list.name}}}"
                else:
                    yield "{number}"
                return

            if range_list.digits:
                number_strs = map(
                    str, range(range_list.start, range_list.stop + 1, range_list.step)
                )
                yield from number_strs

            if range_list.words:
                words_language = range_list.words_language or language
                if words_language:
                    engine = _ENGINE_CACHE.get(words_language)
                    if engine is None:
                        engine = RbnfEngine.for_language(words_language)
                        _ENGINE_CACHE[words_language] = engine

                    assert engine is not None

                    # digits -> words
                    for word_number in range(
                        range_list.start, range_list.stop + 1, range_list.step
                    ):
                        yield engine.format_number(
                            word_number, ruleset_name=range_list.words_ruleset
                        )
                else:
                    _LOGGER.warning(
                        "No language set, so cannot convert %s digits to words",
                        list_ref.slot_name,
                    )
        elif isinstance(slot_list, WildcardSlotList):
            wildcard_list: WildcardSlotList = slot_list
            if wildcard_list.name:
                yield f"{{{wildcard_list.name}}}"
            else:
                yield "{wildcard}"
        else:
            raise ValueError(f"Unexpected slot list type: {slot_list}")
    elif isinstance(expression, RuleReference):
        # <rule>
        rule_ref: RuleReference = expression
        if (not expansion_rules) or (rule_ref.rule_name not in expansion_rules):
            raise MissingRuleError(f"Missing expansion rule <{rule_ref.rule_name}>")

        rule_body = expansion_rules[rule_ref.rule_name]
        yield from sample_expression(
            rule_body,
            slot_lists,
            expansion_rules,
            language=language,
            expand_ranges=expand_ranges,
        )
    else:
        raise ValueError(f"Unexpected expression: {expression}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", nargs="+", help="YAML files or directories")
    parser.add_argument(
        "-n",
        "--max-sentences-per-intent",
        type=int,
        help="Limit number of sentences per intent",
    )
    parser.add_argument(
        "--intents", nargs="+", help="Only sample sentences from these intents"
    )
    parser.add_argument(
        "--areas",
        nargs="+",
        help="Area names",
        default=["area"],
    )
    parser.add_argument(
        "--names", nargs="+", default=["entity"], help="Device/entity names"
    )
    parser.add_argument("--language", help="Language for digits to words")
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

    intents_and_texts = sample_intents(
        intents,
        slot_lists,
        max_sentences_per_intent=args.max_sentences_per_intent,
        intent_names=set(args.intents) if args.intents else None,
        language=args.language,
    )
    for intent_name, sentence_text in intents_and_texts:
        json.dump(
            {"intent": intent_name, "text": sentence_text.strip()},
            sys.stdout,
            ensure_ascii=False,
        )
        print("")


if __name__ == "__main__":
    main()
