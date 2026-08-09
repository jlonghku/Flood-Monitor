from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flood_monitor.collect import CollectionPipeline
from flood_monitor.schemas import SourceRecord
from flood_monitor.sources import LocalFileEvidenceSource, NewsSource, RSSFeedSource, WebArticleSource


class CollectionAndSchemaTests(unittest.TestCase):
    def test_source_record_serialization_and_stable_id(self) -> None:
        first = SourceRecord(source_type="news", publisher_or_provider="Example", url="https://example.test/a", text="Road flooding reported")
        second = SourceRecord(source_type="news", publisher_or_provider="Example", url="https://example.test/a", text="Road flooding reported")
        self.assertEqual(first.source_id, second.source_id)
        payload = first.to_dict()
        self.assertEqual(payload["publisher_or_provider"], "Example")
        self.assertEqual(payload["raw_text"], "Road flooding reported")

    def test_collection_is_idempotent(self) -> None:
        item = {"url": "https://example.test/a", "raw_text": "Road flooding", "location_name": "A"}
        result = CollectionPipeline([NewsSource("example", {"items": [item, item]})]).collect()
        self.assertEqual(len(result.records), 1)

    def test_local_json_ingestion_preserves_canonical_record(self) -> None:
        record = SourceRecord(source_type="community", publisher_or_provider="Public board", text="Street flooding", url="https://example.test/post")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps([record.to_dict()]), encoding="utf-8")
            loaded = LocalFileEvidenceSource(config={"path": str(path)}).fetch()
        self.assertEqual(loaded[0].source_id, record.source_id)
        self.assertEqual(loaded[0].publisher_or_provider, "Public board")

    def test_rss_parser_remains_functional(self) -> None:
        rss = """<rss><channel><item><title>Hong Kong road flooding</title><link>https://example.test/flood</link><description>Flooding affected traffic.</description><pubDate>Wed, 18 Jun 2026 10:00:00 +0800</pubDate></item></channel></rss>"""
        records = RSSFeedSource("feed")._parse_feed(rss, "https://example.test/rss")
        self.assertEqual(len(records), 1)
        self.assertIn("flooding", records[0].raw_text.lower())

    def test_public_article_ingestion_remains_functional(self) -> None:
        html = "<html><head><title>Road flooding</title></head><body><p>Hong Kong road flooding affected traffic for several hours.</p></body></html>"
        from unittest.mock import patch

        with patch("flood_monitor.sources.rss.fetch_text", return_value=html):
            records = WebArticleSource(config={"urls": ["https://example.test/article"]}).fetch(region="Hong Kong")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].url, "https://example.test/article")


if __name__ == "__main__":
    unittest.main()
