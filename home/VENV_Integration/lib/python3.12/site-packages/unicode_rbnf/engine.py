import logging
from abc import ABC
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, IntFlag
from math import ceil, floor, isinf, isnan, log, modf
from pathlib import Path
from typing import Dict, Final, Iterable, List, Optional, Union
from xml.etree import ElementTree as et


class RulesetName(str, Enum):
    """Names of common rulesets."""

    NUMBERING = "spellout-numbering"
    VERBOSE = "spellout-numbering-verbose"
    CARDINAL = "spellout-cardinal"
    CARDINAL_VERBOSE = "spellout-cardinal-verbose"
    ORDINAL = "spellout-ordinal"
    ORDINAL_VERBOSE = "spellout-ordinal-verbose"
    YEAR = "spellout-numbering-year"


class FormatOptions(IntFlag):
    """Extra options for formatting."""

    PRESERVE_SOFT_HYPENS = 1


DEFAULT_RULESET = RulesetName.NUMBERING
DEFAULT_RULESET_FOR_LANGUAGE: Final = {
    "en": RulesetName.CARDINAL,
}
DEFAULT_LANGUAGE: Final = "en"
DEFAULT_TOLERANCE: Final = 1e-8
SKIP_RULESETS: Final = {"lenient-parse"}

_LANG_DIR = Path(__file__).parent / "rbnf"
_LOGGER = logging.getLogger()


class RbnfRulePart(ABC):
    """Abstract base class for rule parts."""


@dataclass
class TextRulePart(RbnfRulePart):
    """Literal text rule part."""

    text: str
    """Literal text to insert."""


class SubType(str, Enum):
    """Type of substitution."""

    REMAINDER = "remainder"
    """Use remainder for rule value."""

    QUOTIENT = "quotient"
    """Use quotient for rule value."""


@dataclass
class SubRulePart(RbnfRulePart):
    """Substitution rule part."""

    type: SubType
    """Type of substitution."""

    is_optional: bool = False
    """True if substitution is optional."""

    text_before: str = ""
    """Text to insert before substitution."""

    text_after: str = ""
    """Text to insert after substitution."""

    ruleset_name: Optional[str] = None
    """Ruleset name to use during substitution (None for current ruleset name)."""


@dataclass
class ReplaceRulePart(RbnfRulePart):
    """Replace with other ruleset (keep value)."""

    ruleset_name: str
    """Name of ruleset to use."""


class ParseState(str, Enum):
    """Set of rbnf parser."""

    TEXT = "text"
    SUB_OPTIONAL_BEFORE = "optional_before"
    SUB_OPTIONAL_AFTER = "optional_after"
    SUB_REMAINDER = "remainder"
    SUB_QUOTIENT = "quotient"
    SUB_RULESET_NAME = "sub_ruleset_name"
    REPLACE_RULESET_NAME = "replace_ruleset_name"


class RbnfSpecialRule(str, Enum):
    """Special rule types"""

    NEGATIVE_NUMBER = "negative_number"
    """The rule is a negative-number rule (-x)."""

    NOT_A_NUMBER = "not_a_number"
    """The rule for an IEEE 754 NaN (NaN)."""

    INFINITY = "infinity"
    """The rule for infinity (Inf)."""

    IMPROPER_FRACTION = "improper_fraction"
    """The rule for improper fractions (x.x)"""


@dataclass
class RbnfRule:
    """Parsed rbnf rule."""

    value: Union[int, RbnfSpecialRule]
    """Numeric lookup value for rule."""

    parts: List[RbnfRulePart] = field(default_factory=list)
    """Parts of rule in order to be processed."""

    radix: int = 10
    """Radix used when calculating divisor."""

    @staticmethod
    def parse(value_str: str, text: str, radix: int = 10) -> "Optional[RbnfRule]":
        """Parse RBNF rule for a value."""
        # Handle special rules
        if value_str == "-x":
            rule = RbnfRule(value=RbnfSpecialRule.NEGATIVE_NUMBER)
        elif value_str in ("x.x", "x,x"):
            rule = RbnfRule(value=RbnfSpecialRule.IMPROPER_FRACTION)
        elif value_str == "NaN":
            rule = RbnfRule(value=RbnfSpecialRule.NOT_A_NUMBER)
        elif value_str == "Inf":
            rule = RbnfRule(value=RbnfSpecialRule.INFINITY)
        else:
            try:
                rule = RbnfRule(value=int(value_str), radix=radix)
            except ValueError:
                _LOGGER.debug(
                    "Unrecognized special rule: value=%s, text=%s", value_str, text
                )
                return None

        state = ParseState.TEXT
        part: Optional[RbnfRulePart] = None
        is_sub_optional = False
        sub_text_before = ""

        for c in text:
            if c == ";":
                # End of rule text
                break

            if c == "'":
                # Placeholder
                continue

            if c in (">", "→"):
                # Divide the number by the rule's divisor and format the remainder
                if state in {ParseState.TEXT, ParseState.SUB_OPTIONAL_BEFORE}:
                    state = ParseState.SUB_REMAINDER
                    part = SubRulePart(
                        SubType.REMAINDER,
                        is_optional=is_sub_optional,
                        text_before=sub_text_before,
                    )
                    rule.parts.append(part)
                    sub_text_before = ""
                elif state in {ParseState.SUB_REMAINDER, ParseState.SUB_RULESET_NAME}:
                    if is_sub_optional:
                        state = ParseState.SUB_OPTIONAL_AFTER
                    else:
                        state = ParseState.TEXT
                        part = None
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif c in ("<", "←"):
                # Divide the number by the rule's divisor and format the quotient
                if state in {ParseState.TEXT, ParseState.SUB_OPTIONAL_BEFORE}:
                    state = ParseState.SUB_QUOTIENT
                    part = SubRulePart(SubType.QUOTIENT, is_optional=is_sub_optional)
                    rule.parts.append(part)
                elif state in {ParseState.SUB_QUOTIENT, ParseState.SUB_RULESET_NAME}:
                    if is_sub_optional:
                        state = ParseState.SUB_OPTIONAL_AFTER
                    else:
                        state = ParseState.TEXT
                        part = None
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif c == "%":
                # =%rule_name= replacement
                if state in {ParseState.SUB_QUOTIENT, ParseState.SUB_REMAINDER}:
                    assert isinstance(part, SubRulePart)
                    state = ParseState.SUB_RULESET_NAME
                    part.ruleset_name = ""
                elif state in {
                    ParseState.REPLACE_RULESET_NAME,
                    ParseState.SUB_RULESET_NAME,
                }:
                    pass
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif c == "[":
                # [optional] (start)
                if state == ParseState.TEXT:
                    is_sub_optional = True
                    state = ParseState.SUB_OPTIONAL_BEFORE
                    sub_text_before = ""
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif c == "]":
                # [optional] (end)
                if state == ParseState.SUB_OPTIONAL_AFTER:
                    is_sub_optional = False
                    state = ParseState.TEXT
                    part = None
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif c == "=":
                # =%rule_name= replacement
                if state == ParseState.TEXT:
                    part = ReplaceRulePart("")
                    rule.parts.append(part)
                    state = ParseState.REPLACE_RULESET_NAME
                elif state == ParseState.REPLACE_RULESET_NAME:
                    part = None
                    state = ParseState.TEXT
                else:
                    raise ValueError(f"Got {c} in {state}")
            elif state == ParseState.SUB_OPTIONAL_BEFORE:
                # [before ...]
                sub_text_before += c
            elif state == ParseState.SUB_OPTIONAL_AFTER:
                # [... after]
                assert isinstance(part, SubRulePart)
                part.text_after += c
            elif state == ParseState.SUB_RULESET_NAME:
                # %ruleset_name in << or >>
                assert isinstance(part, SubRulePart)
                assert part.ruleset_name is not None
                part.ruleset_name += c
            elif state == ParseState.REPLACE_RULESET_NAME:
                # =%ruleset_name=
                assert isinstance(part, ReplaceRulePart)
                part.ruleset_name += c
            elif state == ParseState.TEXT:
                # literal text
                if part is None:
                    part = TextRulePart("")
                    rule.parts.append(part)

                assert isinstance(part, TextRulePart)
                part.text += c
            else:
                raise ValueError(f"Got {c} in {state}")

        return rule


@dataclass
class RbnfRuleSet:
    """Named collection of rbnf rules."""

    name: str
    """Name of ruleset."""

    numeric_rules: Dict[int, RbnfRule] = field(default_factory=dict)
    """Rules keyed by lookup number."""

    special_rules: Dict[RbnfSpecialRule, RbnfRule] = field(default_factory=dict)
    """Rules keyed by special rule type."""

    _sorted_numbers: Optional[List[int]] = field(default=None)
    """Sorted list of numeric_rules keys (updated on demand)."""

    def update(self) -> None:
        """Force update to sorted key list."""
        self._sorted_numbers = sorted(self.numeric_rules.keys())

    def find_rule(
        self,
        number: float,
        tolerance: float = DEFAULT_TOLERANCE,
        rulesets: Optional[Dict[str, "RbnfRuleSet"]] = None,
    ) -> Optional[RbnfRule]:
        """Look up closest rule by number."""

        # Special rules
        if number < 0:
            return self.find_special_rule(RbnfSpecialRule.NEGATIVE_NUMBER, rulesets)

        if isnan(number):
            return self.find_special_rule(RbnfSpecialRule.NOT_A_NUMBER, rulesets)

        if isinf(number):
            return self.find_special_rule(RbnfSpecialRule.INFINITY, rulesets)

        if abs(number - round(number)) > DEFAULT_TOLERANCE:
            return self.special_rules.get(RbnfSpecialRule.IMPROPER_FRACTION)

        # Numeric rules
        number_int = int(number)
        if (self._sorted_numbers is None) or (
            len(self._sorted_numbers) != len(self.numeric_rules)
        ):
            self.update()

        assert self._sorted_numbers is not None

        # Find index of place where number would be inserted
        index = bisect_left(self._sorted_numbers, number_int)
        num_rules = len(self._sorted_numbers)

        if index >= num_rules:
            # Last rule
            index = num_rules - 1
        elif index < 0:
            # First rule
            index = 0

        rule_number = self._sorted_numbers[index]
        if number_int < rule_number:
            # Not an exact match, use one rule down
            index = max(0, index - 1)
            rule_number = self._sorted_numbers[index]

        return self.numeric_rules.get(rule_number)

    def find_special_rule(
        self,
        special_rule: RbnfSpecialRule,
        rulesets: Optional[Dict[str, "RbnfRuleSet"]] = None,
    ) -> Optional[RbnfRule]:
        """Find special rule in this ruleset or in its 0-rule."""
        rule = self.special_rules.get(special_rule)
        if rule is not None:
            return rule

        if rulesets is None:
            # Can't resolve replacement rule
            return None

        # Find the default replacement rule
        zero_rule = self.numeric_rules.get(0)
        if (
            (zero_rule is not None)
            and zero_rule.parts
            and isinstance(zero_rule.parts[0], ReplaceRulePart)
        ):
            replace_part: ReplaceRulePart = zero_rule.parts[0]
            replace_rule = rulesets.get(replace_part.ruleset_name)
            if replace_rule is not None:
                # Try to resolve the special rule in the replacement
                return replace_rule.find_special_rule(special_rule, rulesets)

        return None


class RbnfEngine:
    """Formatting engine using rbnf."""

    def __init__(self, language: Optional[str] = None) -> None:
        # Default language
        self.language = language

        # lang -> ruleset name -> ruleset
        self.rulesets: Dict[str, Dict[str, RbnfRuleSet]] = defaultdict(dict)

    @staticmethod
    def get_supported_languages() -> List[str]:
        """Return a list of supported language codes."""
        return sorted([f.stem for f in _LANG_DIR.glob("*.xml")])

    @staticmethod
    def for_language(language: str) -> "RbnfEngine":
        """Load XML rules for a language and construct an engine."""
        xml_path = _LANG_DIR / f"{language}.xml"
        if not xml_path.is_file():
            raise ValueError(f"{language} is not supported")

        engine = RbnfEngine(language=language)
        with open(xml_path, "r", encoding="utf-8") as xml_file:
            root = et.fromstring(xml_file.read())
            engine.load_xml(root)

        return engine

    def add_rule(
        self,
        value_str: str,
        rule_text: str,
        radix: int = 10,
        ruleset_name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[RbnfRule]:
        """Manually add a rule to the engine."""
        language = language or self.language or DEFAULT_LANGUAGE
        ruleset_name = ruleset_name or DEFAULT_RULESET_FOR_LANGUAGE.get(
            language, DEFAULT_RULESET
        )

        assert ruleset_name is not None
        ruleset = self.rulesets[language].get(ruleset_name)
        if ruleset is None:
            ruleset = RbnfRuleSet(name=ruleset_name)
            self.rulesets[language][ruleset_name] = ruleset

        rule = RbnfRule.parse(value_str, rule_text, radix=radix)
        if rule is None:
            return rule

        if isinstance(rule.value, RbnfSpecialRule):
            # Special rule
            ruleset.special_rules[rule.value] = rule
        else:
            # Numeric rule
            ruleset.numeric_rules[rule.value] = rule

        return rule

    def load_xml(self, root: et.Element, language: Optional[str] = None) -> None:
        """Load an XML file with rbnf rules."""
        if language is None:
            lang_elem = root.find("identity/language")
            language = (
                lang_elem.attrib["type"] if lang_elem is not None else DEFAULT_LANGUAGE
            )

        for group_elem in root.findall("rbnf//ruleset"):
            ruleset_name = group_elem.attrib["type"]
            if ruleset_name in SKIP_RULESETS:
                _LOGGER.debug("Skipping ruleset: %s", ruleset_name)
                continue

            for rule_elem in group_elem.findall("rbnfrule"):
                if not rule_elem.text:
                    continue

                value_str = rule_elem.attrib["value"]
                radix = int(rule_elem.attrib.get("radix", 10))

                self.add_rule(
                    value_str,
                    rule_elem.text,
                    radix=radix,
                    ruleset_name=ruleset_name,
                    language=language,
                )

    def format_number(
        self,
        number: Union[int, float, str, Decimal],
        ruleset_name: Optional[str] = None,
        radix: Optional[int] = None,
        language: Optional[str] = None,
        tolerance: float = DEFAULT_TOLERANCE,
        options: Optional[FormatOptions] = None,
    ) -> str:
        """Format a number using loaded rulesets."""
        if options is None:
            options = FormatOptions(0)

        number_str = "".join(
            self.iter_format_number(
                number,
                ruleset_name=ruleset_name,
                language=language,
                tolerance=tolerance,
            )
        )

        if not (options & FormatOptions.PRESERVE_SOFT_HYPENS):
            # https://en.wikipedia.org/wiki/Soft_hyphen
            number_str = number_str.replace("\xad", "")

        return number_str

    def iter_format_number(
        self,
        number: Union[int, float, str, Decimal],
        ruleset_name: Optional[str] = None,
        radix: Optional[int] = None,
        language: Optional[str] = None,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> Iterable[str]:
        """Format a number using loaded rulesets (generator)."""
        language = language or self.language or DEFAULT_LANGUAGE
        ruleset_name = ruleset_name or DEFAULT_RULESET_FOR_LANGUAGE.get(
            language, DEFAULT_RULESET
        )

        if isinstance(number, str):
            number = Decimal(number)

        assert ruleset_name is not None
        ruleset = self.rulesets[language].get(ruleset_name)
        if ruleset is None:
            raise ValueError(f"No ruleset: {ruleset_name}")

        rule = ruleset.find_rule(
            float(number), tolerance=tolerance, rulesets=self.rulesets[language]
        )
        if rule is None:
            raise ValueError(f"No rule for {number} in {ruleset_name}")

        q: int = 0
        r: int = 0

        if isinstance(rule.value, RbnfSpecialRule):
            if rule.value == RbnfSpecialRule.NEGATIVE_NUMBER:
                r = int(-number)
            elif rule.value == RbnfSpecialRule.IMPROPER_FRACTION:
                frac_part, int_part = modf(number)
                q = int(int_part)
                r = fractional_to_int(frac_part * 10, tolerance=tolerance)
            elif rule.value in {RbnfSpecialRule.NOT_A_NUMBER, RbnfSpecialRule.INFINITY}:
                # Should just be text substitutions
                pass
            else:
                _LOGGER.warning("Unhandled special rule: %s", rule.value)
        elif rule.value > 0:
            power_below = rule.radix ** int(floor(log(rule.value, rule.radix)))
            power_above = rule.radix ** int(ceil(log(rule.value, rule.radix)))
            divisor = power_above if (number >= power_above) else power_below
            q, r = divmod(number, divisor)

        for part in rule.parts:
            if isinstance(part, TextRulePart):
                if part.text:
                    yield part.text
            elif isinstance(part, SubRulePart):
                if (part.type == SubType.QUOTIENT) and (q > 0):
                    if (q == 0) and (part.ruleset_name is None):
                        # Rulesets can use quotients of zero
                        continue

                    if part.text_before:
                        yield part.text_before
                    yield from self.iter_format_number(
                        q,
                        ruleset_name=part.ruleset_name or ruleset_name,
                        language=language,
                        tolerance=tolerance,
                    )
                    if part.text_after:
                        yield part.text_after
                elif part.type == SubType.REMAINDER:
                    if (r == 0) and (part.ruleset_name is None):
                        # Rulesets can use remainders of zero
                        continue

                    if part.text_before:
                        yield part.text_before
                    yield from self.iter_format_number(
                        r,
                        ruleset_name=part.ruleset_name or ruleset_name,
                        language=language,
                        tolerance=tolerance,
                    )
                    if part.text_after:
                        yield part.text_after
            elif isinstance(part, ReplaceRulePart):
                yield from self.iter_format_number(
                    number,
                    ruleset_name=part.ruleset_name,
                    language=language,
                    tolerance=tolerance,
                )


def fractional_to_int(frac_part: float, tolerance: float = DEFAULT_TOLERANCE) -> int:
    """Convert fractional part to int like 0.14000000000000012 -> 14"""
    frac_int = round(frac_part)

    if abs(frac_part - frac_int) > tolerance:
        return fractional_to_int(frac_part * 10, tolerance=tolerance)

    return frac_int
