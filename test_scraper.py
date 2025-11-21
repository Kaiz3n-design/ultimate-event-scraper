#!/usr/bin/env python3
"""
Test script for the event scraper MCP server.
Tests site-specific adapters and fallback mechanisms.
"""

import asyncio
import json
from event_scraper_mcp_server import (
    hybrid_fetch,
    get_site_adapter,
    fetch_static_html,
    parse_event_html,
)


# Test cases with real event URLs
TEST_URLS = {
    "ticketmaster": [
        # Example Ticketmaster event URLs (replace with real ones)
        "https://www.ticketmaster.com/example-event",
    ],
    "eventbrite": [
        # Example Eventbrite event URLs (replace with real ones)
        "https://www.eventbrite.com/e/example-event",
    ],
    "facebook": [
        # Example Facebook Events URLs (replace with real ones)
        # "https://www.facebook.com/events/example",
    ],
    "meetup": [
        # Example Meetup event URLs (replace with real ones)
        # "https://www.meetup.com/group-name/events/example",
    ],
    "generic": [
        # Generic event site that uses schema.org
        # "https://example-event-site.com/event/example",
    ],
}


def test_adapter_detection():
    """Test that URLs are matched to correct adapters."""
    print("=" * 60)
    print("TEST 1: Adapter Detection")
    print("=" * 60)

    test_cases = {
        "https://www.ticketmaster.com/event/123": "TicketmasterAdapter",
        "https://www.eventbrite.com/e/456": "EventbriteAdapter",
        "https://www.facebook.com/events/789": "FacebookEventsAdapter",
        "https://www.meetup.com/group/events/100": "MeetupAdapter",
        "https://www.eventful.com/events/200": "EventfulAdapter",
        "https://example.com/event/generic": None,
    }

    for url, expected_adapter in test_cases.items():
        adapter = get_site_adapter(url)
        adapter_name = adapter.__class__.__name__ if adapter else None
        status = "✓" if adapter_name == expected_adapter else "✗"
        print(f"{status} {url}")
        print(f"  Expected: {expected_adapter}, Got: {adapter_name}")
    print()


def test_static_fetch():
    """Test static HTML fetching capability."""
    print("=" * 60)
    print("TEST 2: Static HTML Fetching")
    print("=" * 60)

    test_urls = [
        "https://www.wikipedia.org",  # Simple, reliable site for testing
    ]

    for url in test_urls:
        print(f"Testing: {url}")
        html = fetch_static_html(url)
        if html and len(html) > 100:
            print(f"  ✓ Successfully fetched HTML ({len(html)} bytes)")
        else:
            print(f"  ✗ Failed to fetch or empty HTML")
    print()


def test_hybrid_scraper():
    """Test the hybrid scraper with provided URLs."""
    print("=" * 60)
    print("TEST 3: Hybrid Scraper")
    print("=" * 60)
    print("NOTE: Provide real event URLs in TEST_URLS to test scraping")
    print()

    for platform, urls in TEST_URLS.items():
        if not urls:
            print(f"[{platform.upper()}] No URLs to test")
            continue

        print(f"[{platform.upper()}]")
        for url in urls:
            print(f"  Testing: {url}")
            try:
                result = hybrid_fetch(url)
                event = result.get("event")
                method = result.get("scrape_method", "unknown")

                if event and event.get("title"):
                    print(f"    ✓ Success ({method})")
                    print(f"      Title: {event.get('title')[:60]}")
                    if event.get("start"):
                        print(f"      Start: {event.get('start')}")
                    if event.get("location"):
                        print(f"      Location: {event.get('location')[:50]}")
                else:
                    print(f"    ✗ Failed to extract event ({method})")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:100]}")
        print()


def test_generic_fallback():
    """Test fallback to generic scraper."""
    print("=" * 60)
    print("TEST 4: Generic Fallback")
    print("=" * 60)

    # This tests that unknown sites fall back to generic scraper
    test_url = "https://example.org"  # Unknown site
    adapter = get_site_adapter(test_url)

    if adapter is None:
        print(f"✓ No adapter for {test_url} (will use generic parser)")
    else:
        print(f"✗ Unexpected adapter for {test_url}: {adapter.__class__.__name__}")

    try:
        result = hybrid_fetch(test_url)
        method = result.get("scrape_method", "unknown")
        print(f"✓ Fallback scraper used: {method}")
    except Exception as e:
        print(f"✗ Error during fallback: {str(e)[:100]}")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " EVENT SCRAPER MCP - TEST SUITE ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    test_adapter_detection()
    test_static_fetch()
    test_generic_fallback()
    test_hybrid_scraper()

    print("=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print()
    print("To test with real event URLs:")
    print("1. Update TEST_URLS with actual event URLs from each platform")
    print("2. Run: python test_scraper.py")
    print()


if __name__ == "__main__":
    main()
