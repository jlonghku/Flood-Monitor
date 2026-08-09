"""RSS/Atom and public article sources."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

from ..query import HK_AREA_BBOXES, HK_BBOX, HK_DISTRICT_CENTROIDS, evidence_matches_query
from ..models import Evidence
from .base import SourceAdapter
from .http import fetch_text


FLOOD_KEYWORDS = (
    "flood",
    "flooding",
    "inundation",
    "rainstorm",
    "black rain",
    "red rain",
    "amber rain",
    "landslip",
    "水浸",
    "水淹",
    "暴雨",
    "黑雨",
    "紅雨",
    "红雨",
    "黃雨",
    "黄雨",
    "山泥傾瀉",
    "山泥倾泻",
)


class RSSFeedSource(SourceAdapter):
    def __init__(self, name: str = "rss_feed", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "news", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        items: list[Evidence] = []
        for url in self.config.get("urls", []):
            xml_text = fetch_text(url, timeout=float(self.config.get("timeout", 20)))
            items.extend(self._parse_feed(xml_text, url))
        return [item for item in items if self._keyword_match(item) and evidence_matches_query(item, **query)]

    def _parse_feed(self, xml_text: str, feed_url: str) -> list[Evidence]:
        root = ET.fromstring(xml_text)
        records = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        evidence: list[Evidence] = []
        for record in records:
            title = self._text(record, "title")
            link = self._link(record)
            summary = self._text(record, "description") or self._text(record, "summary")
            published = self._time(self._text(record, "pubDate") or self._text(record, "published") or self._text(record, "updated"))
            text = clean_html(" ".join(part for part in [title, summary] if part))
            location_name, location = infer_hk_location(text)
            bbox = None if location else infer_hk_bbox(text)
            evidence.append(
                Evidence(
                    source_type="news",
                    source_name=self.name,
                    url=link or feed_url,
                    published_time=published,
                    observed_time=published,
                    location_name=location_name,
                    location=location,
                    bbox=bbox,
                    raw_text=text,
                    summary=title or summary,
                    confidence=float(self.config.get("confidence", 0.6)),
                    license=self.config.get("license"),
                )
            )
        return evidence

    def _keyword_match(self, evidence: Evidence) -> bool:
        keywords = tuple(self.config.get("keywords", FLOOD_KEYWORDS))
        text = " ".join(part for part in [evidence.raw_text, evidence.summary] if part).lower()
        return any(keyword.lower() in text for keyword in keywords)

    def _text(self, element: ET.Element, tag: str) -> str | None:
        found = element.find(tag)
        if found is None:
            found = element.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
        return found.text if found is not None else None

    def _link(self, element: ET.Element) -> str | None:
        link = self._text(element, "link")
        if link:
            return link
        found = element.find("{http://www.w3.org/2005/Atom}link")
        return found.attrib.get("href") if found is not None else None

    def _time(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value).isoformat()
        except (TypeError, ValueError):
            return value


class WebArticleSource(SourceAdapter):
    def __init__(self, name: str = "web_article", config: dict[str, Any] | None = None) -> None:
        super().__init__(name, "news", config or {})

    def fetch(self, **query: Any) -> list[Evidence]:
        evidence = []
        for url in self.config.get("urls", []):
            html = fetch_text(url, timeout=float(self.config.get("timeout", 20)))
            article = ArticleHTMLParser()
            article.feed(html)
            text = clean_html(" ".join([article.title or "", article.description or "", " ".join(article.paragraphs[: self.config.get("max_paragraphs", 24)])]))
            location_name, location = infer_hk_location(text)
            bbox = None if location else infer_hk_bbox(text)
            evidence.append(
                Evidence(
                    source_type="news",
                    source_name=self.name,
                    url=url,
                    published_time=article.published_time,
                    observed_time=article.published_time,
                    location_name=location_name,
                    location=location,
                    bbox=bbox,
                    raw_text=text,
                    summary=article.title or article.description,
                    confidence=float(self.config.get("confidence", 0.58)),
                    license=self.config.get("license"),
                )
            )
        keywords = tuple(self.config.get("keywords", FLOOD_KEYWORDS))
        return [
            item
            for item in evidence
            if any(keyword.lower() in (item.raw_text or "").lower() for keyword in keywords) and evidence_matches_query(item, **query)
        ]


class ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.description: str | None = None
        self.published_time: str | None = None
        self.paragraphs: list[str] = []
        self._tag: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs}
        if tag in {"title", "p"}:
            self._tag = tag
            self._buffer = []
        if tag == "meta":
            key = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            content = attrs_dict.get("content")
            if not content:
                return
            if key in {"og:title", "twitter:title"} and not self.title:
                self.title = content
            elif key in {"description", "og:description", "twitter:description"} and not self.description:
                self.description = content
            elif key in {"article:published_time", "pubdate", "date", "dc.date", "dc.date.issued"} and not self.published_time:
                self.published_time = content

    def handle_data(self, data: str) -> None:
        if self._tag in {"title", "p"}:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self._tag:
            return
        text = clean_html(" ".join(self._buffer))
        if tag == "title" and text and not self.title:
            self.title = text
        elif tag == "p" and len(text) >= 20:
            self.paragraphs.append(text)
        self._tag = None
        self._buffer = []


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def infer_hk_location(text: str) -> tuple[str | None, tuple[float, float] | None]:
    lowered = text.lower()
    aliases = {
        "新界北部": "Northern New Territories",
        "northern new territories": "Northern New Territories",
        "north new territories": "Northern New Territories",
        "黃大仙": "Wong Tai Sin",
        "黄大仙": "Wong Tai Sin",
        "沙田": "Sha Tin",
        "大埔": "Tai Po",
        "元朗": "Yuen Long",
        "屯門": "Tuen Mun",
        "屯门": "Tuen Mun",
        "北區": "North District",
        "北区": "North District",
        "西貢": "Sai Kung",
        "西贡": "Sai Kung",
        "觀塘": "Kwun Tong",
        "观塘": "Kwun Tong",
        "深水埗": "Sham Shui Po",
        "荃灣": "Tsuen Wan",
        "荃湾": "Tsuen Wan",
        "灣仔": "Wan Chai",
        "湾仔": "Wan Chai",
    }
    for alias, district in aliases.items():
        if alias.lower() in lowered:
            return district, HK_DISTRICT_CENTROIDS.get(district)
    for district, point in HK_DISTRICT_CENTROIDS.items():
        if district.lower() in lowered:
            return district, point
    return None, None


def infer_hk_bbox(text: str) -> tuple[float, float, float, float] | None:
    lowered = text.lower()
    area_aliases = {
        "新界北部": "Northern New Territories",
        "northern new territories": "Northern New Territories",
        "north new territories": "Northern New Territories",
        "北區": "North District",
        "北区": "North District",
        "元朗": "Yuen Long",
        "大埔": "Tai Po",
    }
    for alias, area in area_aliases.items():
        if alias.lower() in lowered:
            return HK_AREA_BBOXES.get(area)
    if "hong kong" in lowered or "香港" in lowered:
        return HK_BBOX
    return None
