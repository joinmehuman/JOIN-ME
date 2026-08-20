#!/usr/bin/env python3
"""Deterministic security and release checks for the current static JOIN ME surface."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 8, 20)


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.local_refs: list[str] = []
        self.auto_origins: set[str] = set()
        self.capture_tags: list[str] = []
        self.script_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag in {"form", "input", "textarea", "select"} or "contenteditable" in values:
            self.capture_tags.append(tag)
        ref = None
        if tag in {"script", "img", "iframe", "source", "video", "audio"}:
            ref = values.get("src")
        elif tag == "link" and values.get("rel") in {"stylesheet", "preload", "preconnect"}:
            ref = values.get("href")
        if tag == "script" and values.get("src"):
            self.script_sources.append(values["src"] or "")
        if ref:
            parsed = urlparse(ref)
            if parsed.scheme in {"http", "https"}:
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

record("HTML-INDEX-SINGLE-SCRIPT", index.script_sources == ["script.js"], f"scripts={index.script_sources}")

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

price_ok = all(
    phrase in index_text
    for phrase in ("24時間使い放題", "110円", "30日パス", "380円", "自動更新はありません", "月額サブスクは現時点では導入しません")
)
obsolete = sorted(
    term
    for term in ("330円", "580円", "500円", "1500円", "月額480円", "月額780円", "7日無料", "自動更新あり")
    if term in index_text
)
record("MASTER-PRICE-CONSISTENCY", price_ok and not obsolete, f"obsolete={obsolete or 'none'}")

market = json.loads((ROOT / "config/markets/jp.json").read_text(encoding="utf-8"))
market_prices = {(item["id"], item["price_tax_inclusive"], item["duration_hours"], item["auto_renew"]) for item in market["passes"]}
record(
    "COUNTRY-JP-PRICE-CONFIG",
    market_prices == {("24h", 110, 24, False), ("30d", 380, 720, False)} and market.get("monthly_subscription") == "not_offered",
    f"passes={sorted(market_prices)}; monthly={market.get('monthly_subscription')}",
)
legal_is_approved = market.get("legal_approval_status") == "approved" and market.get("legal_approved_at") and market.get("review_expires_at")
record(
    "COUNTRY-JP-FAIL-CLOSED",
    bool(legal_is_approved) or (market.get("enabled") is False and market.get("payment_enabled") is False),
    f"legal={market.get('legal_approval_status')}; enabled={market.get('enabled')}; payment_enabled={market.get('payment_enabled')}",
)

vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
global_rule = next(rule for rule in vercel["headers"] if rule["source"] == "/(.*)")
headers = {item["key"]: item["value"] for item in global_rule["headers"]}
required_headers = {
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
}
record("HEADERS-CONFIG-PRESENT", required_headers.issubset(headers), f"headers={sorted(headers)}")
csp = headers.get("Content-Security-Policy", "")
required_csp = ("default-src 'self'", "connect-src 'none'", "object-src 'none'", "frame-ancestors 'none'", "form-action 'none'", "base-uri 'none'")
record("CSP-RESTRICTIVE", all(item in csp for item in required_csp), csp)

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
record("CRISIS-SCHEMA-AND-ROUTES", crisis.get("enabled") is True and required_routes.issubset(route_ids) and len(route_ids) == len(set(route_ids)), f"routes={route_ids}")
review_due = date.fromisoformat(crisis["review_due"])
record("CRISIS-REVIEW-NOT-EXPIRED", review_due > TODAY, f"verified_at={crisis['verified_at']}; review_due={review_due.isoformat()}")
allowed_hosts = {"www.fdma.go.jp", "www.npa.go.jp", "www.mhlw.go.jp", "www.gender.go.jp", "www.caa.go.jp"}
source_hosts = {urlparse(route["source"]).hostname for route in crisis["routes"]}
record("CRISIS-OFFICIAL-SOURCE-HOSTS", source_hosts.issubset(allowed_hosts), f"hosts={sorted(source_hosts)}")
phones = {route["phone"] for route in crisis["routes"]}
displayed = {re.sub(r"[^0-9#]", "", value) for value in re.findall(r">([#0-9][#0-9\-]+)<", support_text)}
normalized_registry = {re.sub(r"[^0-9#]", "", phone) for phone in phones}
record("CRISIS-UI-MATCHES-REGISTRY", normalized_registry.issubset(displayed), f"registry={sorted(normalized_registry)}; displayed={sorted(displayed)}")

css_external = re.findall(r"url\(\s*['\"]?https?://", css_text, re.I)
record("CSS-NO-REMOTE-ASSETS", not css_external, f"remote_url_count={len(css_external)}")

artifact_hashes = {
    str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(ROOT.rglob("*"))
    if path.is_file() and path.name != "SECURITY_TEST_RESULTS.json"
}

failed = [item for item in results if item["status"] == "FAIL"]
report = {
    "scope": "static landing surface plus Japan crisis registry and deployment header configuration",
    "source_commit": "711d8c865ce803413f6d00c04c024695453c2b20",
    "tested_at": "2026-08-20",
    "overall": "PASS_CURRENT_STATIC_SURFACE" if not failed else "FAIL",
    "product_release_gate": "BLOCKED_NOT_IMPLEMENTED",
    "not_testable_in_current_repo": [
        "AI input/output dual safety classifier",
        "prompt-injection and model-output safety",
        "authentication, authorization, CSRF and rate limiting",
        "AES-GCM IndexedDB save and delete-after-retrieval E2E",
        "payment and entitlement enforcement",
        "runtime DAST and penetration test against a deployed production-equivalent environment"
    ],
    "tests": results,
    "sha256": artifact_hashes,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if failed else 0)
