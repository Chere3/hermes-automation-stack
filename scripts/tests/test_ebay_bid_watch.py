#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "ebay_bid_watch.py"
spec = importlib.util.spec_from_file_location("ebay_bid_watch", SCRIPT)
watch = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(watch)


def fixture(
    *,
    price: str = "1.00",
    bids: int = 2,
    countdown: str = "2d 15h",
    ended: bool = False,
    item_id: str = watch.ITEM_ID,
    seller: str = "example-seller",
) -> str:
    title = "Example collectible listing"
    if ended:
        timing = "This listing ended\n"
        bid_action = ""
    else:
        timing = f"Ends in {countdown} Saturday, 03:19 PM\n"
        bid_action = "[Place bid](https://signin.ebay.com/example)\n"
    body = f"""Title: {title} | eBay
URL Source: http://www.ebay.com/itm/{item_id}
Markdown Content:
# {title}
[J](https://www.ebay.com/sch/{seller}/m.html?item={item_id})
[{seller}](https://www.ebay.com/sch/{seller}/m.html?item={item_id})
EUR {price}
Approximately US $1.14
[{bids} bids](https://www.ebay.com/bfl/viewbids/{item_id}?item={item_id})
{timing}{bid_action}About this item
Seller assumes all responsibility for this listing.
eBay item number:{item_id}
"""
    return body


def german_fixture(*, price: str = "1,00", bids: int = 2) -> str:
    return f"""Title: Looner 1 großes weiches Anlass aufblasbares Kissen 2,50m Vinyl Ring Rollballon | eBay.de
URL Source: http://www.ebay.de/itm/{watch.ITEM_ID}?monitor_tick=1
Markdown Content:
# Example collectible listing
[E](https://www.ebay.de/sch/example-seller/m.html?item={watch.ITEM_ID})
[example-seller](https://www.ebay.de/sch/example-seller/m.html?item={watch.ITEM_ID})
EUR {price}
[{bids} Gebote](https://www.ebay.de/bfl/viewbids/{watch.ITEM_ID}?item={watch.ITEM_ID})
Endet in 2 T 9 Std Samstag, 15:19
[Bieten](https://signin.ebay.de/example)
## Ähnliche Artikel
"""


class ParserTests(unittest.TestCase):
    def test_parses_exact_active_auction(self):
        auction = watch.parse_auction(fixture())
        self.assertEqual(auction["item_id"], watch.ITEM_ID)
        self.assertEqual(auction["seller"], "example-seller")
        self.assertEqual(auction["price"], "1.00")
        self.assertEqual(auction["currency"], "EUR")
        self.assertEqual(auction["bid_count"], 2)
        self.assertEqual(auction["status"], "active")
        self.assertEqual(auction["end_label"], "Saturday, 15:19")

    def test_parses_german_fallback_and_normalizes_fields(self):
        auction = watch.parse_auction(german_fixture())
        self.assertEqual(auction["seller"], "example-seller")
        self.assertEqual(auction["price"], "1.00")
        self.assertEqual(auction["currency"], "EUR")
        self.assertEqual(auction["bid_count"], 2)
        self.assertEqual(auction["status"], "active")
        self.assertEqual(auction["end_label"], "Saturday, 15:19")

    def test_german_translation_does_not_fabricate_title_change(self):
        old = watch.parse_auction(fixture())
        new = watch.parse_auction(german_fixture())
        new["_source"] = "de"
        self.assertEqual(watch.changed_fields(old, new), [])

    def test_countdown_progress_does_not_look_like_change(self):
        old = watch.parse_auction(fixture(countdown="2d 15h"))
        new = watch.parse_auction(fixture(countdown="2d 14h"))
        self.assertEqual(watch.changed_fields(old, new), [])

    def test_bid_count_change_detected_even_when_price_is_same(self):
        old = watch.parse_auction(fixture(price="1.00", bids=2))
        new = watch.parse_auction(fixture(price="1.00", bids=3))
        self.assertEqual(watch.changed_fields(old, new), ["bid_count"])
        report = watch.change_report(old, new, ["bid_count"])
        self.assertIn("*2* → *3*", report)
        self.assertIn("Revisa eBay inmediatamente", report)

    def test_price_change_detected(self):
        old = watch.parse_auction(fixture(price="1.00"))
        new = watch.parse_auction(fixture(price="12.50"))
        self.assertEqual(watch.changed_fields(old, new), ["price"])
        self.assertIn("*1.00 EUR* → *12.50 EUR*", watch.change_report(old, new, ["price"]))

    def test_ended_transition_detected(self):
        old = watch.parse_auction(fixture())
        new = watch.parse_auction(fixture(ended=True))
        self.assertEqual(new["status"], "ended")
        self.assertEqual(watch.changed_fields(old, new), ["status", "end_label"])

    def test_wrong_item_identity_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "identity marker missing"):
            watch.parse_auction(fixture(item_id="999999999999"))

    def test_missing_bid_count_fails_closed(self):
        broken = fixture().replace(
            f"[2 bids](https://www.ebay.com/bfl/viewbids/{watch.ITEM_ID}?item={watch.ITEM_ID})",
            "bid data unavailable",
        )
        with self.assertRaisesRegex(RuntimeError, "bid_count"):
            watch.parse_auction(broken)

    def test_avatar_is_not_mistaken_for_seller(self):
        auction = watch.parse_auction(fixture())
        self.assertEqual(auction["seller"], "example-seller")
        self.assertNotEqual(auction["seller"], "J")


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        state = Path(self.tmp.name)
        self.original = (watch.STATE_DIR, watch.BASELINE, watch.HISTORY, watch.FAILURES, watch.HEALTH, watch.EVENTS)
        watch.STATE_DIR = state
        watch.BASELINE = state / "auction.json"
        watch.HISTORY = state / "history.jsonl"
        watch.FAILURES = state / "failures.json"
        watch.HEALTH = state / "health.json"
        watch.EVENTS = state / "checks.jsonl"

    def tearDown(self):
        watch.STATE_DIR, watch.BASELINE, watch.HISTORY, watch.FAILURES, watch.HEALTH, watch.EVENTS = self.original
        self.tmp.cleanup()

    def test_failure_counter_preserves_baseline(self):
        auction = watch.parse_auction(fixture())
        watch.save_baseline(auction)
        baseline_before = watch.BASELINE.read_bytes()
        self.assertEqual(watch.record_failure(RuntimeError("blocked")), 1)
        self.assertEqual(watch.record_failure(RuntimeError("blocked")), 2)
        self.assertEqual(watch.record_failure(RuntimeError("blocked")), 3)
        self.assertEqual(watch.BASELINE.read_bytes(), baseline_before)
        failure = json.loads(watch.FAILURES.read_text())
        self.assertEqual(failure["count"], 3)
        watch.clear_failures()
        self.assertFalse(watch.FAILURES.exists())

    def test_baseline_round_trip(self):
        auction = watch.parse_auction(fixture())
        watch.save_baseline(auction)
        self.assertEqual(watch.load_baseline(), auction)
        self.assertEqual(watch.BASELINE.stat().st_mode & 0o777, 0o600)

    def test_success_heartbeat_is_persisted(self):
        auction = watch.parse_auction(fixture())
        watch.record_success(auction)
        health = json.loads(watch.HEALTH.read_text())
        self.assertEqual(health["item_id"], watch.ITEM_ID)
        self.assertEqual(health["bid_count"], 2)
        self.assertEqual(health["status"], "active")
        self.assertEqual(watch.HEALTH.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
