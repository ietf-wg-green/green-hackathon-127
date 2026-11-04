from __future__ import annotations

import re
from pathlib import Path


_SEPARATOR_CELL = re.compile(r":?-{3,}:?")


def align_markdown_tables(text: str) -> str:
    lines = text.splitlines()
    aligned: list[str] = []
    index = 0
    while index < len(lines):
        if (
            index + 1 < len(lines)
            and _is_table_row(lines[index])
            and _is_separator_row(lines[index + 1])
        ):
            table_rows = [lines[index], lines[index + 1]]
            index += 2
            while index < len(lines) and _is_table_row(lines[index]):
                table_rows.append(lines[index])
                index += 1
            aligned.extend(_align_table(table_rows))
            continue
        aligned.append(lines[index])
        index += 1
    result = "\n".join(aligned)
    if text.endswith("\n"):
        result += "\n"
    return result


def align_markdown_directory(directory: Path) -> tuple[Path, ...]:
    updated = []
    for path in sorted(directory.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        aligned = align_markdown_tables(text)
        if aligned != text:
            path.write_text(aligned, encoding="utf-8")
            updated.append(path)
    return tuple(updated)


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped[1:-1]:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current.clear()
        else:
            current.append(character)
        if character == "\\":
            escaped = not escaped
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _is_separator_row(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(_SEPARATOR_CELL.fullmatch(cell) for cell in cells)


def _align_table(rows: list[str]) -> list[str]:
    cells_by_row = [_split_row(row) for row in rows]
    column_count = len(cells_by_row[0])
    if any(len(row) != column_count for row in cells_by_row):
        return rows

    separator = cells_by_row[1]
    data_rows = [cells_by_row[0], *cells_by_row[2:]]
    widths = [
        max(3, *(len(row[column]) for row in data_rows))
        for column in range(column_count)
    ]
    output = [_format_row(row, widths) for row in data_rows[:1]]
    output.append(_format_separator(separator, widths))
    output.extend(_format_row(row, widths) for row in data_rows[1:])
    return output


def _format_row(cells: list[str], widths: list[int]) -> str:
    return "| " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells)) + " |"


def _format_separator(cells: list[str], widths: list[int]) -> str:
    aligned = []
    for index, cell in enumerate(cells):
        left = cell.startswith(":")
        right = cell.endswith(":")
        dash_count = max(3, widths[index] - int(left) - int(right))
        aligned.append(f"{':' if left else ''}{'-' * dash_count}{':' if right else ''}")
    return "| " + " | ".join(aligned) + " |"