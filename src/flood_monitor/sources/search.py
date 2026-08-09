"""Public media search sources."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

from ..models import Evidence
from ..query import HK_BBOX, HK_DISTRICT_CENTROIDS, evidence_matches_query, parse_time
from .base import SourceAdapter
from .http import fetch_json
from .rss import FLOOD_KEYWORDS, infer_hk_location


class GDELTMediaSearchSource(SourceAdapter):
    """Search public news coverage through the GDELT 2.1 DOC API."""

    API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, name: str = "gdelt_media_search", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "news", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        evidence: list[Evidence] = []
        seen: set[str] = set()
        for url in self._build_urls(**query):
            payload = fetch_json(url, timeout=float(self.config.get("timeout", 25)))
            for article in payload.get("articles") or []:
                article_url = article.get("url") or ""
                key = article_url or f"{article.get('title')}|{article.get('seendate')}"
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(self._article_to_evidence(article, url))
        return [item for item in evidence if evidence_matches_query(item, **query)]

    def _build_urls(self, **query: Any) -> list[str]:
        if self.config.get("queries"):
            searches = self.config["queries"]
        elif self.config.get("query"):
            searches = [self.config["query"]]
        else:
            searches = self._default_queries(query.get("region"))
        return [self._url_for_query(search, **query) for search in searches]

    def _url_for_query(self, search: str, **query: Any) -> str:
        params = {
            "query": search,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(int(self.config.get("maxrecords", query.get("max_media_records", 50)))),
            "sort": self.config.get("sort", "HybridRel"),
        }
        start = self._gdelt_time(query.get("start_time"))
        end = self._gdelt_time(query.get("end_time"))
        if start:
            params["startdatetime"] = start
        elif self.config.get("timespan"):
            params["timespan"] = self.config["timespan"]
        else:
            params["timespan"] = query.get("timespan", "3d")
        if end:
            params["enddatetime"] = end
        return f"{self.API_URL}?" + "&".join(f"{key}={quote_plus(str(value))}" for key, value in params.items())

    def _default_queries(self, region: str | None) -> list[str]:
        english = ['"flooding"', '"flood"', '"rainstorm"', '"black rain"', '"red rain"', '"landslip"']
        chinese = ["水浸", "暴雨", "黑雨", "紅雨", "山泥傾瀉"]
        region_terms = [region or "Hong Kong", "香港"]
        districts = list(HK_DISTRICT_CENTROIDS.keys())
        queries = [
            f"({' OR '.join(english)}) ({' OR '.join(self._quote(item) for item in region_terms)})",
            f"({' OR '.join(chinese)}) ({' OR '.join(self._quote(item) for item in region_terms)})",
        ]
        for district in districts[:12]:
            queries.append(f'("flood" OR "flooding" OR "rainstorm" OR 水浸 OR 暴雨) "{district}"')
        queries.extend(self.config.get("extra_queries", []))
        return queries[: int(self.config.get("max_queries", 16))]

    def _quote(self, item: str) -> str:
        return f'"{item}"' if " " in item else item

    def _gdelt_time(self, value: Any) -> str | None:
        dt = parse_time(value)
        if not dt:
            return None
        return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")

    def _article_to_evidence(self, article: dict[str, Any], search_url: str) -> Evidence:
        title = article.get("title")
        summary = article.get("seendate") or article.get("socialimage")
        text = " ".join(str(part) for part in [title, article.get("domain"), article.get("sourcecountry")] if part)
        location_name, location = infer_hk_location(text)
        bbox = None if location else HK_BBOX
        severity = self._severity_from_title(title or "")
        return Evidence(
            source_type="news",
            source_name=article.get("domain") or self.name,
            url=article.get("url") or search_url,
            published_time=article.get("seendate"),
            observed_time=article.get("seendate"),
            location_name=location_name,
            location=location,
            bbox=bbox,
            raw_text=title,
            summary=title or summary,
            extracted_facts={
                "severity": severity,
                "media_search": "gdelt",
                "search_url": search_url,
                "raw_record": article,
            },
            confidence=self._confidence(article),
            license="GDELT public DOC API metadata",
        )

    def _severity_from_title(self, title: str) -> str:
        lowered = title.lower()
        severe_terms = ("black rain", "severe", "trapped", "road closed", "landslip", "黑雨", "山泥傾瀉", "封路", "死火")
        moderate_terms = ("flood", "flooding", "rainstorm", "red rain", "水浸", "暴雨", "紅雨", "水深")
        if any(term in lowered for term in severe_terms):
            return "severe"
        if any(term in lowered for term in moderate_terms):
            return "moderate"
        return "minor"

    def _confidence(self, article: dict[str, Any]) -> float:
        confidence = float(self.config.get("confidence", 0.50))
        domain = str(article.get("domain") or "").lower()
        priority_domains = self.config.get(
            "priority_domains",
            ["rthk.hk", "news.gov.hk", "info.gov.hk", "scmp.com", "hongkongfp.com", "hk01.com", "mingpao.com", "on.cc", "wenweipo.com"],
        )
        if any(item in domain for item in priority_domains):
            confidence += 0.12
        if article.get("title") and article.get("url"):
            confidence += 0.05
        return min(confidence, 0.85)


def last_n_days_range(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()
