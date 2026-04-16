"""
Tests for the FIX market data feed (acceptor + initiator).

Run from the repo root:
    pytest tests/test_fix_feed.py -v

Requirements: quickfix must be installed (pip install quickfix).
RT-specific code (pykx / rtpy) is NOT required — acceptor tests run
with RT_ENABLED=false and a mock publisher callable.
"""

import os
import sys
import time
import threading
import unittest
from unittest.mock import MagicMock, patch, call

# Ensure RT is disabled so acceptor can be imported without pykx/rtpy
os.environ["RT_ENABLED"] = "false"

# Add the feed source dirs to the path so we can import directly
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "fix-market-feed", "initiator"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "fix-market-feed", "acceptor"))

import quickfix as fix

# Import after path setup and RT_ENABLED override
import initiator as init_mod
import acceptor as acc_mod

SYMBOLS = init_mod.SYMBOLS
BASE_PRICES = init_mod.BASE_PRICES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_quote_message(symbol="AAPL", bid=184.95, ask=185.05, bsize=1000, asize=1200):
    """Build a minimal FIX Quote (S) message as the initiator would send it."""
    msg = fix.Message()
    header = msg.getHeader()
    header.setField(fix.MsgType(fix.MsgType_Quote))
    header.setField(fix.BeginString(fix.BeginString_FIX44))
    msg.setField(fix.Symbol(symbol))
    msg.setField(fix.BidPx(bid))
    msg.setField(fix.OfferPx(ask))
    msg.setField(fix.BidSize(bsize))
    msg.setField(fix.OfferSize(asize))
    return msg


def _make_trade_message(symbol="AAPL", price=185.0, qty=500, side=fix.Side_BUY):
    """Build a minimal FIX Trade Capture Report (AE) message as the initiator would send it."""
    msg = fix.Message()
    header = msg.getHeader()
    header.setField(fix.MsgType("AE"))
    header.setField(fix.BeginString(fix.BeginString_FIX44))
    msg.setField(fix.Symbol(symbol))
    msg.setField(fix.LastPx(price))
    msg.setField(fix.LastQty(qty))
    msg.setField(fix.Side(side))
    return msg


# ---------------------------------------------------------------------------
# Initiator tests
# ---------------------------------------------------------------------------

class TestTickPrice(unittest.TestCase):

    def setUp(self):
        self.app = init_mod.MarketDataInitiator()

    def test_price_stays_positive_after_many_ticks(self):
        for _ in range(10_000):
            price = self.app._tick_price("AAPL")
            self.assertGreater(price, 0, "Price must always be positive")

    def test_price_clamped_at_minimum(self):
        self.app.prices["AAPL"] = 0.001          # force tiny price
        for _ in range(100):
            price = self.app._tick_price("AAPL")
        self.assertGreaterEqual(price, 0.01)

    def test_price_stays_near_base(self):
        for _ in range(1000):
            self.app._tick_price("AAPL")
        # After 1000 ticks the price shouldn't have drifted catastrophically (±50%)
        self.assertGreater(self.app.prices["AAPL"], BASE_PRICES["AAPL"] * 0.5)
        self.assertLess(self.app.prices["AAPL"], BASE_PRICES["AAPL"] * 2.0)

    def test_all_symbols_updated_independently(self):
        for sym in SYMBOLS:
            self.app._tick_price(sym)
        prices = {s: self.app.prices[s] for s in SYMBOLS}
        self.assertEqual(len(set(prices.values())), len(SYMBOLS),
                         "All symbol prices should differ after individual ticks")


class TestBuildQuote(unittest.TestCase):

    def setUp(self):
        self.app = init_mod.MarketDataInitiator()

    def test_msg_type_is_quote(self):
        msg = self.app.build_quote("AAPL")
        mt = fix.MsgType()
        msg.getHeader().getField(mt)
        self.assertEqual(mt.getValue(), fix.MsgType_Quote)

    def test_begin_string_is_fix44(self):
        msg = self.app.build_quote("MSFT")
        bs = fix.BeginString()
        msg.getHeader().getField(bs)
        self.assertEqual(bs.getValue(), fix.BeginString_FIX44)

    def test_required_fields_present(self):
        msg = self.app.build_quote("GOOGL")
        for field_cls in [fix.Symbol, fix.BidPx, fix.OfferPx, fix.BidSize, fix.OfferSize, fix.QuoteID]:
            field = field_cls()
            msg.getField(field)   # raises FieldNotFound if missing

    def test_bid_less_than_ask(self):
        for sym in SYMBOLS:
            msg = self.app.build_quote(sym)
            bid = fix.BidPx();   msg.getField(bid)
            ask = fix.OfferPx(); msg.getField(ask)
            self.assertLess(bid.getValue(), ask.getValue(),
                            f"{sym}: bid must be < ask")

    def test_sizes_are_multiples_of_100(self):
        for _ in range(20):
            msg = self.app.build_quote("TSLA")
            bs = fix.BidSize();   msg.getField(bs)
            os_ = fix.OfferSize(); msg.getField(os_)
            self.assertEqual(int(bs.getValue()) % 100, 0)
            self.assertEqual(int(os_.getValue()) % 100, 0)

    def test_symbol_matches(self):
        for sym in SYMBOLS:
            msg = self.app.build_quote(sym)
            s = fix.Symbol(); msg.getField(s)
            self.assertEqual(s.getValue(), sym)


class TestBuildTrade(unittest.TestCase):

    def setUp(self):
        self.app = init_mod.MarketDataInitiator()

    def test_msg_type_is_ae(self):
        msg = self.app.build_trade("AAPL")
        mt = fix.MsgType()
        msg.getHeader().getField(mt)
        self.assertEqual(mt.getValue(), "AE")

    def test_required_fields_present(self):
        msg = self.app.build_trade("AAPL")
        for field_cls in [fix.Symbol, fix.LastPx, fix.LastQty, fix.Side, fix.TradeReportID]:
            field = field_cls()
            msg.getField(field)

    def test_qty_is_multiple_of_100(self):
        for _ in range(20):
            msg = self.app.build_trade("AMZN")
            qty = fix.LastQty(); msg.getField(qty)
            self.assertEqual(int(qty.getValue()) % 100, 0)

    def test_side_is_buy_or_sell(self):
        sides = set()
        for _ in range(50):
            msg = self.app.build_trade("MSFT")
            s = fix.Side(); msg.getField(s)
            sides.add(s.getValue())
        self.assertIn(fix.Side_BUY, sides)
        self.assertIn(fix.Side_SELL, sides)

    def test_price_within_1pct_of_mid(self):
        for sym in SYMBOLS:
            mid = self.app.prices[sym]
            msg = self.app.build_trade(sym)
            px = fix.LastPx(); msg.getField(px)
            self.assertAlmostEqual(px.getValue(), mid, delta=mid * 0.01)


class TestWaitForLogon(unittest.TestCase):

    def test_returns_true_when_session_already_set(self):
        app = init_mod.MarketDataInitiator()
        app.session_id = MagicMock()
        self.assertTrue(app.wait_for_logon(timeout=1))

    def test_returns_false_on_timeout(self):
        app = init_mod.MarketDataInitiator()
        start = time.time()
        result = app.wait_for_logon(timeout=2)
        elapsed = time.time() - start
        self.assertFalse(result)
        self.assertGreaterEqual(elapsed, 2)

    def test_returns_true_when_logon_arrives_during_wait(self):
        app = init_mod.MarketDataInitiator()

        def set_session():
            time.sleep(0.5)
            app.session_id = MagicMock()

        t = threading.Thread(target=set_session, daemon=True)
        t.start()
        self.assertTrue(app.wait_for_logon(timeout=5))


# ---------------------------------------------------------------------------
# Acceptor tests
# ---------------------------------------------------------------------------

class TestParseQuote(unittest.TestCase):

    def setUp(self):
        self.app = acc_mod.MarketDataAcceptor(rt_publisher=None)

    def test_valid_quote_logged_without_error(self):
        msg = _make_quote_message("AAPL", bid=184.95, ask=185.05, bsize=1000, asize=1200)
        with self.assertLogs("acceptor", level="INFO") as cm:
            self.app._parse_quote(msg)
        log_output = " ".join(cm.output)
        self.assertIn("AAPL", log_output)
        self.assertIn("184.9500", log_output)

    def test_missing_field_logs_error_and_does_not_raise(self):
        """Message with no BidPx should log an error and not crash."""
        msg = fix.Message()
        msg.getHeader().setField(fix.MsgType(fix.MsgType_Quote))
        msg.setField(fix.Symbol("AAPL"))
        # BidPx, OfferPx, BidSize, OfferSize intentionally omitted
        with self.assertLogs("acceptor", level="ERROR") as cm:
            self.app._parse_quote(msg)   # must not raise
        self.assertTrue(any("Missing required field" in line for line in cm.output))

    def test_rt_publish_called_with_correct_stream(self):
        mock_pub = MagicMock()
        app = acc_mod.MarketDataAcceptor(rt_publisher=mock_pub)

        # We need pykx to be importable for this to work; skip if not available
        try:
            import pykx as kx  # noqa: F401
        except ImportError:
            self.skipTest("pykx not installed — skipping RT publish stream-name test")

        msg = _make_quote_message("AAPL")
        app._parse_quote(msg)
        self.assertEqual(mock_pub.call_args[0][0], "quote",
                         "Quote must be published to the 'quote' RT stream")

    def test_rt_publish_failure_does_not_crash(self):
        mock_pub = MagicMock(side_effect=RuntimeError("RT down"))
        app = acc_mod.MarketDataAcceptor(rt_publisher=mock_pub)

        try:
            import pykx as kx  # noqa: F401
        except ImportError:
            self.skipTest("pykx not installed — skipping RT publish error test")

        msg = _make_quote_message("MSFT")
        with self.assertLogs("acceptor", level="ERROR"):
            app._parse_quote(msg)   # must not raise even when pub raises


class TestParseTrade(unittest.TestCase):

    def setUp(self):
        self.app = acc_mod.MarketDataAcceptor(rt_publisher=None)

    def test_valid_buy_trade_logged(self):
        msg = _make_trade_message("TSLA", price=175.0, qty=300, side=fix.Side_BUY)
        with self.assertLogs("acceptor", level="INFO") as cm:
            self.app._parse_trade(msg)
        log_output = " ".join(cm.output)
        self.assertIn("TSLA", log_output)
        self.assertIn("buy", log_output)

    def test_valid_sell_trade_logged(self):
        msg = _make_trade_message("AMZN", price=195.0, qty=200, side=fix.Side_SELL)
        with self.assertLogs("acceptor", level="INFO") as cm:
            self.app._parse_trade(msg)
        log_output = " ".join(cm.output)
        self.assertIn("sell", log_output)

    def test_missing_field_logs_error_and_does_not_raise(self):
        """Trade message missing LastPx should log error and not crash."""
        msg = fix.Message()
        msg.getHeader().setField(fix.MsgType("AE"))
        msg.setField(fix.Symbol("AAPL"))
        # LastPx, LastQty, Side intentionally omitted
        with self.assertLogs("acceptor", level="ERROR") as cm:
            self.app._parse_trade(msg)
        self.assertTrue(any("Missing required field" in line for line in cm.output))

    def test_rt_publish_called_with_rawtrade_stream(self):
        mock_pub = MagicMock()
        app = acc_mod.MarketDataAcceptor(rt_publisher=mock_pub)

        try:
            import pykx as kx  # noqa: F401
        except ImportError:
            self.skipTest("pykx not installed — skipping RT stream-name test")

        msg = _make_trade_message("AAPL")
        app._parse_trade(msg)
        self.assertEqual(mock_pub.call_args[0][0], "rawTrade",
                         "Trades must be published to the 'rawTrade' RT stream (consumed by kxi-spw)")

    def test_rt_publish_failure_does_not_crash(self):
        mock_pub = MagicMock(side_effect=RuntimeError("RT down"))
        app = acc_mod.MarketDataAcceptor(rt_publisher=mock_pub)

        try:
            import pykx as kx  # noqa: F401
        except ImportError:
            self.skipTest("pykx not installed — skipping RT publish error test")

        msg = _make_trade_message("GOOGL")
        with self.assertLogs("acceptor", level="ERROR"):
            app._parse_trade(msg)


class TestFromApp(unittest.TestCase):
    """Verify the message router dispatches correctly and handles unknown types."""

    def setUp(self):
        self.app = acc_mod.MarketDataAcceptor(rt_publisher=None)

    def test_routes_quote_to_parse_quote(self):
        msg = _make_quote_message("AAPL")
        with patch.object(self.app, "_parse_quote") as mock_pq:
            self.app.fromApp(msg, None)
            mock_pq.assert_called_once_with(msg)

    def test_routes_trade_to_parse_trade(self):
        msg = _make_trade_message("AAPL")
        with patch.object(self.app, "_parse_trade") as mock_pt:
            self.app.fromApp(msg, None)
            mock_pt.assert_called_once_with(msg)

    def test_unknown_msg_type_logged_as_warning(self):
        msg = fix.Message()
        msg.getHeader().setField(fix.MsgType("D"))   # NewOrderSingle — not handled
        msg.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        with self.assertLogs("acceptor", level="WARNING") as cm:
            self.app.fromApp(msg, None)
        self.assertTrue(any("Unhandled" in line for line in cm.output))


# ---------------------------------------------------------------------------
# Config / env-var tests
# ---------------------------------------------------------------------------

class TestAcceptorConfigEnvVars(unittest.TestCase):

    def test_rt_config_missing_exits(self):
        """main() should exit(1) when RT_ENABLED=true and config file absent."""
        with patch.dict(os.environ, {"RT_ENABLED": "true",
                                     "RT_CONFIG_FILE": "/nonexistent/rt.json"}):
            with patch("sys.exit") as mock_exit:
                # Re-evaluate RT_ENABLED inside main() by calling it directly
                # We patch sys.exit to catch the call without actually exiting
                try:
                    acc_mod.main()
                except SystemExit:
                    pass
                mock_exit.assert_called_with(1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
