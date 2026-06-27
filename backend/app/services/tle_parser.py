"""TLE parsing and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sgp4.api import Satrec


@dataclass(frozen=True)
class ParsedTle:
    name: str
    line1: str
    line2: str
    norad_id: int

    @property
    def text(self) -> str:
        return f"{self.name}\n{self.line1}\n{self.line2}"


def parse_tle(text: str) -> ParsedTle:
    """Parse 2-line or 3-line TLE text."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) == 2:
        name = "UNKNOWN"
        line1, line2 = lines
    elif len(lines) >= 3:
        name = lines[0]
        line1, line2 = lines[1], lines[2]
    else:
        raise ValueError("TLEは2行または3行で入力してください。")

    if not line1.startswith("1 ") or not line2.startswith("2 "):
        raise ValueError("TLEの1行目・2行目は '1 ' / '2 ' で始まる必要があります。")

    if len(line1) < 69 or len(line2) < 69:
        raise ValueError("TLEの各行は69文字以上である必要があります。")

    norad_match = re.match(r"1\s+(\d+)", line1)
    if not norad_match:
        raise ValueError("TLEからNORAD IDを読み取れません。")

    sat = Satrec.twoline2rv(line1, line2)
    if sat.error != 0:
        raise ValueError(f"TLEが無効です (SGP4 code={sat.error})")

    return ParsedTle(
        name=name,
        line1=line1,
        line2=line2,
        norad_id=int(norad_match.group(1)),
    )


def parse_tle_catalog(text: str) -> list[ParsedTle]:
    """Parse multi-entry TLE catalog (compact or blank-line separated)."""
    lines = [line.strip() for line in text.splitlines()]
    entries: list[ParsedTle] = []
    i = 0
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue

        if lines[i].startswith("1 "):
            line1 = lines[i]
            name = "UNKNOWN"
            j = i - 1
            while j >= 0 and not lines[j]:
                j -= 1
            if j >= 0 and not lines[j].startswith("1 ") and not lines[j].startswith("2 "):
                name = lines[j]

            i += 1
            while i < len(lines) and not lines[i]:
                i += 1
            if i < len(lines) and lines[i].startswith("2 "):
                line2 = lines[i]
                try:
                    entries.append(parse_tle(f"{name}\n{line1}\n{line2}"))
                except ValueError:
                    pass
            i += 1
            continue

        # Compact 3-line blocks: name, line1, line2 without blank lines
        if (
            i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            try:
                entries.append(parse_tle("\n".join(lines[i : i + 3])))
            except ValueError:
                pass
            i += 3
            continue

        i += 1
    return entries
