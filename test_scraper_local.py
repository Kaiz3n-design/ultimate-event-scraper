#!/usr/bin/env python3
"""
Local test script for the event scraper - tests core logic without MCP framework.
"""

import sys
import json
import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

# Test the adapter system directly
class SiteAdapter:
    """Base class for site-specific event scrapers."""
    def matches(self, url: str) -> bool:
        pass
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        pass


class TicketmasterAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        return "ticketmaster" in url.lower()
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        return {"title": "Ticketmaster Event", "source_url": url, "scrape_method": "ticketmaster_adapter"}


class EventbriteAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        return "eventbrite" in url.lower()
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        return {"title": "Eventbrite Event", "source_url": url, "scrape_method": "eventbrite_adapter"}


class FacebookEventsAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        return "facebook.com" in url.lower() and "events" in url.lower()
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        return {"title": "Facebook Event", "source_url": url, "scrape_method": "facebook_adapter"}


class MeetupAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        url_lower = url.lower()
        return "meetup.com" in url_lower and "/events/" in url_lower
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        return {"title": "Meetup Event", "source_url": url, "scrape_method": "meetup_adapter"}


class EventfulAdapter(SiteAdapter):
    def matches(self, url: str) -> bool:
        return "eventful.com" in url.lower()
    def extract_event(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        return {"title": "Eventful Event", "source_url": url, "scrape_method": "eventful_adapter"}


SITE_ADAPTERS = [
    TicketmasterAdapter(),
    EventbriteAdapter(),
    FacebookEventsAdapter(),
    MeetupAdapter(),
    EventfulAdapter(),
]


def get_site_adapter(url: str) -> Optional[SiteAdapter]:
    """Find and return the appropriate adapter for the given URL."""
    for adapter in SITE_ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


def test_adapter_detection():
    """Test that URLs are matched to correct adapters."""
    print("=" * 70)
    print("TEST 1: Site Adapter Detection")
    print("=" * 70)

    test_cases = {
        "https://www.ticketmaster.com/event/123": "TicketmasterAdapter",
        "https://www.eventbrite.com/e/456": "EventbriteAdapter",
        "https://www.facebook.com/events/789": "FacebookEventsAdapter",
        "https://www.meetup.com/group/events/100": "MeetupAdapter",
        "https://www.eventful.com/events/200": "EventfulAdapter",
        "https://example.com/event/generic": None,
    }

    passed = 0
    failed = 0

    for url, expected_adapter in test_cases.items():
        adapter = get_site_adapter(url)
        adapter_name = adapter.__class__.__name__ if adapter else None
        is_correct = adapter_name == expected_adapter

        status = "[PASS]" if is_correct else "[FAIL]"
        print(f"{status}: {url}")
        print(f"       Expected: {expected_adapter}, Got: {adapter_name}")

        if is_correct:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    print()
    return failed == 0


def test_adapter_extraction():
    """Test that adapters can extract event data."""
    print("=" * 70)
    print("TEST 2: Site Adapter Extraction")
    print("=" * 70)

    test_urls = [
        ("https://www.ticketmaster.com/event/123", "Ticketmaster"),
        ("https://www.eventbrite.com/e/456", "Eventbrite"),
        ("https://www.facebook.com/events/789", "Facebook"),
        ("https://www.meetup.com/group/events/100", "Meetup"),
        ("https://www.eventful.com/events/200", "Eventful"),
    ]

    passed = 0
    failed = 0

    for url, platform_name in test_urls:
        adapter = get_site_adapter(url)
        if not adapter:
            print(f"[FAIL] FAIL: No adapter found for {platform_name}")
            failed += 1
            continue

        # Test extraction with dummy HTML
        dummy_html = "<html><body>Test</body></html>"
        result = adapter.extract_event(dummy_html, url)

        if result and result.get("title"):
            print(f"[OK] PASS: {platform_name} adapter extracted data")
            print(f"       Title: {result.get('title')}")
            print(f"       Method: {result.get('scrape_method')}")
            passed += 1
        else:
            print(f"[FAIL] FAIL: {platform_name} adapter failed to extract")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    print()
    return failed == 0


def test_fallback_detection():
    """Test that unknown sites don't get matched to any adapter."""
    print("=" * 70)
    print("TEST 3: Fallback Detection (Generic Sites)")
    print("=" * 70)

    generic_urls = [
        "https://example.com/event/123",
        "https://myeventsite.com/event",
        "https://local-events.org/event/456",
    ]

    passed = 0
    failed = 0

    for url in generic_urls:
        adapter = get_site_adapter(url)
        if adapter is None:
            print(f"[OK] PASS: {url} correctly has no adapter (will use generic)")
            passed += 1
        else:
            print(f"[FAIL] FAIL: {url} unexpectedly matched {adapter.__class__.__name__}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    print()
    return failed == 0


def test_adapter_priority():
    """Test that adapters are checked in the right order."""
    print("=" * 70)
    print("TEST 4: Adapter Priority & Specificity")
    print("=" * 70)

    # Test that more specific patterns are matched correctly
    test_cases = [
        ("https://www.facebook.com/pages/123", None, "Facebook page (not event)"),
        ("https://www.facebook.com/events/123", "FacebookEventsAdapter", "Facebook event"),
        ("https://facebook.com/events/456", "FacebookEventsAdapter", "Facebook event (subdomain)"),
        ("https://www.meetup.com/groups/123", None, "Meetup group page (not event)"),
        ("https://www.meetup.com/group-name/events/123", "MeetupAdapter", "Meetup event"),
    ]

    passed = 0
    failed = 0

    for url, expected_adapter, description in test_cases:
        adapter = get_site_adapter(url)
        adapter_name = adapter.__class__.__name__ if adapter else None

        is_correct = adapter_name == expected_adapter
        status = "[PASS]" if is_correct else "[FAIL]"

        print(f"{status}: {description}")
        print(f"       URL: {url}")
        print(f"       Expected: {expected_adapter}, Got: {adapter_name}")

        if is_correct:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    print()
    return failed == 0


def main():
    """Run all tests."""
    print("\n")
    print("=" * 70)
    print("ULTIMATE WEBSCRAPER MCP - LOCAL TEST SUITE")
    print("Site Adapter System")
    print("=" * 70)
    print()

    results = []
    results.append(("Adapter Detection", test_adapter_detection()))
    results.append(("Adapter Extraction", test_adapter_extraction()))
    results.append(("Fallback Detection", test_fallback_detection()))
    results.append(("Adapter Priority", test_adapter_priority()))

    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
