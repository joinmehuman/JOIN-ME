#!/usr/bin/env python3
"""Deterministic checks for the public GitHub Pages prelaunch surface."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now(ZoneInfo("Asia/Tokyo")).date()


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.local_refs: list[str] = []
        self.auto_origins: set[str] = set()
        self.capture_tags: list[str] = []
        self.script_sources: list[str] = []
        self.csp_values: list[str] = []
        self.referrer_values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag in {"form", "input", "textarea", "select"} or "contenteditable" in values:
            self.capture_tags.append(tag)

        if tag == "meta" and (values.get("http-equiv") or "").lower() == "content-security-policy":
            self.csp_values.append(values.get("content") or "")
        if tag == "meta" and (values.get("name") or "").lower() == "referrer":
            self.referrer_values.append(values.get("content") or "")

        ref = None
        if tag in {"script", "img", "iframe", "source", "video", "audio"}:
            ref = values.get("src")
        elif tag == "link" and values.get("rel") in {"stylesheet", "preload", "preconnect"}:
            ref = values.get("href")
        elif tag == "a":
            ref = values.get("href")

        if tag == "script" and values.get("src"):
            self.script_sources.append(values["src"] or "")

        if ref:
            parsed = urlparse(ref)
            if parsed.scheme in {"http", "https"}:
                if tag != "a":
                    self.auto_origins.add(f"{parsed.scheme}://{parsed.netloc}")
            elif not ref.startswith(("data:", "#", "tel:", "mailto:")):
                self.local_refs.append(ref.split("?", 1)[0].split("#", 1)[0])


results: list[dict[str, str]] = []


def record(test_id: str, ok: bool, evidence: str) -> None:
    results.append({"id": test_id, "status": "PASS" if ok else "FAIL", "evidence": evidence})


def parse_html(path: Path) -> tuple[str, SurfaceParser]:
    text = path.read_text(encoding="utf-8")
    parser = SurfaceParser()
    parser.feed(text)
    return text, parser


index_text, index = parse_html(ROOT / "index.html")
support_text, support = parse_html(ROOT / "support-jp.html")
script_text = (ROOT / "script.js").read_text(encoding="utf-8")
css_text = (ROOT / "style.css").read_text(encoding="utf-8")
readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

required_csp = (
    "default-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "object-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "connect-src 'none'",
)

for name, text, parser in (
    ("index", index_text, index),
    ("support", support_text, support),
):
    duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    structure_ok = all(
        (
            len(re.findall(r"<!doctype\s+html", text, re.I)) == 1,
            len(re.findall(r"<html(?:\s|>)", text, re.I)) == 1,
            len(re.findall(r"</html>", text, re.I)) == 1,
            len(re.findall(r"<body(?:\s|>)", text, re.I)) == 1,
            len(re.findall(r"</body>", text, re.I)) == 1,
            not duplicate_ids,
        )
    )
    record(f"HTML-{name.upper()}-STRUCTURE", structure_ok, f"duplicate_ids={duplicate_ids or 'none'}")
    missing = sorted({ref for ref in parser.local_refs if ref and not (ROOT / ref).exists()})
    record(f"HTML-{name.upper()}-LOCAL-REFS", not missing, f"missing={missing or 'none'}")
    record(f"PRIVACY-{name.upper()}-NO-CAPTURE", not parser.capture_tags, f"capture_tags={parser.capture_tags or 'none'}")
    record(f"PRIVACY-{name.upper()}-NO-AUTO-THIRD-PARTY", not parser.auto_origins, f"auto_origins={sorted(parser.auto_origins) or 'none'}")
    csp_ok = len(parser.csp_values) == 1 and all(item in parser.csp_values[0] for item in required_csp)
    record(f"SECURITY-{name.upper()}-META-CSP", csp_ok, parser.csp_values[0] if parser.csp_values else "missing")
    record(
        f"PRIVACY-{name.upper()}-REFERRER",
        parser.referrer_values == ["no-referrer"],
        f"values={parser.referrer_values}",
    )

record("HTML-INDEX-SINGLE-SCRIPT", index.script_sources == ["script.js"], f"scripts={index.script_sources}")
record("HTML-SUPPORT-NO-SCRIPT", not support.script_sources, f"scripts={support.script_sources or 'none'}")

node_check = subprocess.run(
    ["node", "--check", str(ROOT / "script.js")],
    capture_output=True,
    text=True,
    check=False,
)
record("JS-SYNTAX", node_check.returncode == 0, node_check.stderr.strip() or "node --check passed")

unsafe_js = sorted(
    pattern
    for pattern in ("eval(", "new Function", "document.write", ".innerHTML", ".outerHTML", "insertAdjacentHTML")
    if pattern in script_text
)
record("JS-NO-DYNAMIC-CODE-OR-HTML-SINK", not unsafe_js, f"matches={unsafe_js or 'none'}")

network_js = sorted(
    pattern
    for pattern in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "EventSource")
    if pattern in script_text
)
record("PRIVACY-JS-NO-NETWORK-SEND", not network_js, f"matches={network_js or 'none'}")

storage_js = sorted(
    pattern
    for pattern in ("localStorage", "sessionStorage", "indexedDB", "caches.", "CacheStorage")
    if pattern in script_text
)
record("PRIVACY-JS-NO-PERSISTENT-STORAGE", not storage_js, f"matches={storage_js or 'none'}")

tracking_terms = sorted(
    term
    for term in ("google-analytics", "gtag(", "segment", "mixpanel", "amplitude", "fullstory", "hotjar", "logrocket", "sessionreplay")
    if term.lower() in (index_text + support_text + script_text).lower()
)
record("PRIVACY-NO-ANALYTICS-OR-SESSION-REPLAY", not tracking_terms, f"matches={tracking_terms or 'none'}")

secret_patterns = {
    "generic_api_key": r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
    "openai": r"sk-[A-Za-z0-9]{20,}",
    "stripe": r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}",
    "github": r"gh[pousr]_[A-Za-z0-9]{20,}",
}
scan_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file() and path.suffix in {".html", ".js", ".css", ".json", ".md", ".py"}
)
secret_hits = [name for name, pattern in secret_patterns.items() if re.search(pattern, scan_text)]
record("SECRETS-STATIC-SCAN", not secret_hits, f"matches={secret_hits or 'none'}")

prelaunch_phrases = ("おかえり", "現在は開発確認ページです", "入力・AI・会員登録・保存・決済はまだ利用できません")
record(
    "SURFACE-PRELAUNCH-TRUTHFUL",
    all(phrase in index_text for phrase in prelaunch_phrases),
    f"required={prelaunch_phrases}",
)

misleading_or_sales_terms = sorted(
    term
    for term in ("自己観察を始める", "24時間使い放題", "30日パス", "購入する", "今すぐ購入")
    if term in index_text
)
record("SURFACE-NO-UNAVAILABLE-CTA-OR-SALES", not misleading_or_sales_terms, f"matches={misleading_or_sales_terms or 'none'}")

legacy_terms = sorted(
    term
    for term in (
        "\u932c\u91d1\u5854",
        "\u932c\u91d1\u8853",
        "\u53cd\u5bfe\u8a71\u306e\u932c\u91d1\u8853",
    )
    if term in scan_text
)
record("MASTER-NO-LEGACY-CONCEPTS", not legacy_terms, f"matches={legacy_terms or 'none'}")

record("DEPLOY-NO-VERCEL-CONFIG", not (ROOT / "vercel.json").exists(), "vercel.json absent")

market = json.loads((ROOT / "config/markets/jp.json").read_text(encoding="utf-8"))
market_prices = {
    (item["id"], item["price_tax_inclusive"], item["duration_hours"], item["auto_renew"])
    for item in market["passes"]
}
record(
    "COUNTRY-JP-CONFIG",
    market.get("minimum_age") == 18
    and market.get("enabled") is False
    and market.get("payment_enabled") is False
    and market_prices == {("24h", 110, 24, False), ("30d", 380, 720, False)}
    and market.get("monthly_subscription") == "not_offered",
    f"enabled={market.get('enabled')}; payment={market.get('payment_enabled')}; passes={sorted(market_prices)}",
)

crisis = json.loads((ROOT / "config/crisis/jp.json").read_text(encoding="utf-8"))
route_ids = [route["id"] for route in crisis["routes"]]
required_routes = {
    "emergency_medical_fire",
    "emergency_police",
    "suicide_inochi_sos",
    "suicide_yorisoi",
    "mental_health_prefecture",
    "domestic_violence",
    "sexual_violence",
    "police_non_emergency",
    "consumer_contract_billing",
}
record(
    "CRISIS-SCHEMA-AND-ROUTES",
    crisis.get("enabled") is True and required_routes.issubset(route_ids) and len(route_ids) == len(set(route_ids)),
    f"routes={route_ids}",
)
review_due = date.fromisoformat(crisis["review_due"])
record(
    "CRISIS-REVIEW-NOT-EXPIRED",
    review_due > TODAY,
    f"verified_at={crisis['verified_at']}; review_due={review_due.isoformat()}; today={TODAY.isoformat()}",
)
allowed_hosts = {"www.fdma.go.jp", "www.npa.go.jp", "www.mhlw.go.jp", "www.gender.go.jp", "www.caa.go.jp"}
source_hosts = {urlparse(route["source"]).hostname for route in crisis["routes"]}
record("CRISIS-OFFICIAL-SOURCE-HOSTS", source_hosts.issubset(allowed_hosts), f"hosts={sorted(source_hosts)}")

phones = {route["phone"] for route in crisis["routes"]}
displayed = {re.sub(r"[^0-9#]", "", value) for value in re.findall(r">([#0-9][#0-9\-]+)<", support_text)}
normalized_registry = {re.sub(r"[^0-9#]", "", phone) for phone in phones}
record(
    "CRISIS-UI-MATCHES-REGISTRY",
    normalized_registry.issubset(displayed),
    f"registry={sorted(normalized_registry)}; displayed={sorted(displayed)}",
)

css_external = re.findall(r"url\(\s*['\"]?https?://", css_text, re.I)
record("CSS-NO-REMOTE-ASSETS", not css_external, f"remote_url_count={len(css_external)}")

readme_ok = all(
    phrase in readme_text
    for phrase in ("GitHub Pages", "入力、AI生成、会員登録、端末保存、決済は公開していません", "python3 tests/security_static.py")
)
record("DOCS-CURRENT-SCOPE", readme_ok, "README describes the current prelaunch scope")

failed = [item for item in results if item["status"] == "FAIL"]
report = {
    "scope": "GitHub Pages prelaunch surface, Japan crisis registry, and fail-closed market configuration",
    "tested_at": TODAY.isoformat(),
    "overall": "PASS_CURRENT_STATIC_SURFACE" if not failed else "FAIL",
    "product_release_gate": "BLOCKED_NOT_IMPLEMENTED",
    "tests_total": len(results),
    "tests_passed": len(results) - len(failed),
    "not_testable_in_current_repo": [
        "question input and deletion E2E",
        "AI input/output dual safety classifier",
        "authentication and authorization",
        "encrypted IndexedDB save and delete-after-retrieval E2E",
        "payment and entitlement enforcement",
        "runtime DAST and penetration test against a production-equivalent environment",
    ],
    "tests": results,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if failed else 0)
