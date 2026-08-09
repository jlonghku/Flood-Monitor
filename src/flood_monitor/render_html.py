"""Render Flood Monitor HTML views from a JSON database."""

from __future__ import annotations

import argparse
import json
import os
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_TEMPLATE = Path(__file__).with_name("template.html")
EMBED_MARKER = "<!-- FLOOD_MONITOR_EMBED_JSON -->"


def load_database(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json_reader_html(
    output_path: str | Path,
    *,
    template_path: str | Path = DEFAULT_TEMPLATE,
    database_filename: str = "flood_data.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = _template_text(template_path)
    html = _set_database_filename(html, database_filename)
    path.write_text(html, encoding="utf-8")
    return path


def write_injected_html(
    database_path: str | Path,
    output_path: str | Path,
    *,
    template_path: str | Path = DEFAULT_TEMPLATE,
    database_filename: str | None = None,
) -> Path:
    database = load_database(database_path)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = _template_text(template_path)
    html = _set_database_filename(html, database_filename or Path(database_path).name)
    html = _embed_database(html, database)
    path.write_text(html, encoding="utf-8")
    return path


def write_html_pair(
    database_path: str | Path,
    *,
    injected_output: str | Path,
    reader_output: str | Path,
    template_path: str | Path = DEFAULT_TEMPLATE,
) -> tuple[Path, Path]:
    database = Path(database_path)
    injected_ref = _relative_ref(database, Path(injected_output).parent)
    reader_ref = _relative_ref(database, Path(reader_output).parent)
    injected = write_injected_html(
        database_path,
        injected_output,
        template_path=template_path,
        database_filename=injected_ref,
    )
    reader = write_json_reader_html(
        reader_output,
        template_path=template_path,
        database_filename=reader_ref,
    )
    return injected, reader


def _template_text(template_path: str | Path) -> str:
    return Path(template_path).read_text(encoding="utf-8")


def _set_database_filename(html: str, database_filename: str) -> str:
    safe_name = escape(database_filename, quote=True)
    return html.replace('data-json="flood_data.json"', f'data-json="{safe_name}"')


def _relative_ref(path: Path, start: Path) -> str:
    return os.path.relpath(path.resolve(), start.resolve()).replace(os.sep, "/")


def _embed_database(html: str, database: dict[str, Any]) -> str:
    data = json.dumps(database, ensure_ascii=False).replace("</", "<\\/")
    script = f'<script type="application/json" id="flood-data">{data}</script>'
    if EMBED_MARKER in html:
        return html.replace(EMBED_MARKER, script)
    return html.replace("</body>", f"{script}\n</body>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Flood Monitor HTML from flood_data.json")
    parser.add_argument("--database", default="flood_data.json", help="input JSON database")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="HTML template path")
    parser.add_argument("--injected-output", default="map.html", help="self-contained injected HTML output")
    parser.add_argument("--reader-output", default="template.html", help="HTML output that reads the JSON file")
    args = parser.parse_args()
    write_html_pair(
        args.database,
        injected_output=args.injected_output,
        reader_output=args.reader_output,
        template_path=args.template,
    )


if __name__ == "__main__":
    main()
