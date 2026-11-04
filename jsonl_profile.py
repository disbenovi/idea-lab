"""Bounded-cardinality, two-level JSON Lines profiler (standard library only)."""
import argparse
import json
import math
import sys


def json_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return {str: "string", list: "array", dict: "object"}[type(value)]


def canonical(value):
    """Tag types, ignore object order, and equate integral JSON numbers."""
    kind = json_type(value)
    if kind == "object":
        value = sorted((k, canonical(v)) for k, v in value.items())
    elif kind == "array":
        value = [canonical(v) for v in value]
    elif kind == "number" and isinstance(value, float) and value.is_integer():
        value = int(value)
    return json.dumps([kind, value], ensure_ascii=True, separators=(",", ":"))


def reject_constant(value):
    raise ValueError("Non-JSON constant: " + value)


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Number outside finite float range")
    return number


def escape(key):
    return key.replace("\\", "\\\\").replace(".", "\\.")


def fields(record):
    for key, value in record.items():
        name = escape(key)
        yield name, value
        if isinstance(value, dict):
            for child, item in value.items():
                yield name + "." + escape(child), item


class Field:
    def __init__(self, cap):
        self.cap = cap
        self.present = self.nulls = 0
        self.types = set()
        self.seen = set()
        self.overflow = False
        self.strings = {}
        self.strings_overflow = False
        self.low = self.high = None
        self.integral = True
        self.example = None

    def add(self, value):
        kind = json_type(value)
        self.present += 1
        self.types.add(kind)
        self.nulls += value is None
        if self.example is None:
            rendered = json.dumps(value, ensure_ascii=True, sort_keys=True)
            self.example = rendered if len(rendered) <= 80 else rendered[:77] + "..."
        if not self.overflow:
            token = canonical(value)
            if token not in self.seen:
                if len(self.seen) == self.cap:
                    self.overflow = True
                else:
                    self.seen.add(token)
        if kind == "number":
            self.low = value if self.low is None else min(self.low, value)
            self.high = value if self.high is None else max(self.high, value)
            self.integral &= isinstance(value, int) or value.is_integer()
        if kind == "string" and not self.strings_overflow:
            if value not in self.strings and len(self.strings) == 20:
                self.strings_overflow = True
                self.strings.clear()
            else:
                self.strings[value] = self.strings.get(value, 0) + 1

    def result(self, lines):
        result = dict(present=self.present, missing=lines - self.present,
                      types=sorted(self.types), nulls=self.nulls,
                      distinct=f">={self.cap}" if self.overflow else len(self.seen),
                      example=self.example)
        if "number" in self.types:
            result.update(min=self.low, max=self.high, integral=self.integral)
        if ("string" in self.types and not self.overflow
                and len(self.seen) <= 20 and not self.strings_overflow):
            result["values"] = dict(sorted(self.strings.items()))
        return result


def profile(stream, max_card=1000):
    if max_card < 1:
        raise ValueError("max_card must be positive")
    lines = malformed = 0
    keys = {}
    for line in stream:
        lines += 1
        try:
            record = json.loads(line, parse_constant=reject_constant,
                                parse_float=finite_float)
            if not isinstance(record, dict):
                raise ValueError("Expected an object")
            # Materialize before updating any counts if deeply nested input fails.
            entries = [(name, value) for name, value in fields(record)]
            for _, value in entries:
                canonical(value)
        except (ValueError, RecursionError):
            malformed += 1
            continue
        for name, value in entries:
            if name not in keys:
                keys[name] = Field(max_card)
            keys[name].add(value)
    return dict(lines=lines, malformed=malformed,
                keys={key: keys[key].result(lines) for key in sorted(keys)})


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="JSONL file or - for stdin")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--max-card", type=positive, default=1000)
    args = parser.parse_args(argv)
    try:
        if args.path == "-":
            result = profile(sys.stdin, args.max_card)
        else:
            with open(args.path, encoding="utf-8") as stream:
                result = profile(stream, args.max_card)
        if args.json:
            print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        else:
            print(f"lines: {result['lines']}; malformed: {result['malformed']}")
            for key, stats in result["keys"].items():
                print(json.dumps(key) + ": " + json.dumps(stats, ensure_ascii=True))
    except (OSError, UnicodeError) as error:
        parser.exit(2, f"jsonl-profile: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
