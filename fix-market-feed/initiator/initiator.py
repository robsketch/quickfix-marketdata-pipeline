import quickfix as fix
import logging
import sys
import time
import random
import uuid
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INITIATOR] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Dummy market data config
# ------------------------------------------------------------------
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

BASE_PRICES = {
    "AAPL":  185.0,
    "MSFT":  415.0,
    "GOOGL": 175.0,
    "AMZN":  195.0,
    "TSLA":  175.0,
}

PUBLISH_INTERVAL_SECS = 2    # how often to send a batch of messages
LOGON_TIMEOUT_SECS    = 30   # max time to wait for FIX session logon


class MarketDataInitiator(fix.Application):
    """
    FIX Initiator — generates dummy Quote (S) and Trade Capture Report (AE)
    messages and sends them to the acceptor on a timer.
    """

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.prices = dict(BASE_PRICES)  # mutable mid-prices

    def onCreate(self, sessionID):
        logger.info(f"Session created: {sessionID}")

    def onLogon(self, sessionID):
        logger.info(f"Logon: {sessionID}")
        self.session_id = sessionID

    def onLogout(self, sessionID):
        logger.info(f"Logout: {sessionID}")
        self.session_id = None

    def toAdmin(self, message, sessionID):
        pass

    def fromAdmin(self, message, sessionID):
        pass

    def toApp(self, message, sessionID):
        logger.debug(f"Sending: {message}")

    def fromApp(self, message, sessionID):
        pass

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    def _tick_price(self, symbol: str) -> float:
        """Random-walk the mid price, clamped to a minimum of 0.01."""
        change = self.prices[symbol] * random.uniform(-0.002, 0.002)
        self.prices[symbol] = max(0.01, round(self.prices[symbol] + change, 4))
        return self.prices[symbol]

    def build_quote(self, symbol: str) -> fix.Message:
        mid       = self._tick_price(symbol)
        spread    = round(mid * 0.0005, 4)          # 5 bps spread
        bid       = round(mid - spread / 2, 4)
        ask       = round(mid + spread / 2, 4)
        bid_size  = random.randint(1, 50) * 100
        ask_size  = random.randint(1, 50) * 100

        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType(fix.MsgType_Quote))          # 35=S
        header.setField(fix.BeginString(fix.BeginString_FIX44))

        msg.setField(fix.QuoteID(str(uuid.uuid4())[:8]))
        msg.setField(fix.Symbol(symbol))
        msg.setField(fix.BidPx(bid))
        msg.setField(fix.OfferPx(ask))
        msg.setField(fix.BidSize(bid_size))
        msg.setField(fix.OfferSize(ask_size))
        msg.setField(fix.TransactTime())

        return msg

    def build_trade(self, symbol: str) -> fix.Message:
        mid   = self.prices.get(symbol, BASE_PRICES[symbol])
        price = round(mid * random.uniform(0.9995, 1.0005), 4)
        qty   = random.randint(1, 20) * 100
        side  = fix.Side_BUY if random.random() > 0.5 else fix.Side_SELL

        msg = fix.Message()
        header = msg.getHeader()
        header.setField(fix.MsgType("AE"))                        # 35=AE
        header.setField(fix.BeginString(fix.BeginString_FIX44))

        msg.setField(fix.TradeReportID(str(uuid.uuid4())[:8]))
        msg.setField(fix.Symbol(symbol))
        msg.setField(fix.LastPx(price))
        msg.setField(fix.LastQty(qty))
        msg.setField(fix.Side(side))
        msg.setField(fix.TransactTime())
        msg.setField(fix.TradeReportTransType(0))                 # 487=0 New

        return msg

    # ------------------------------------------------------------------
    # Publishing loop
    # ------------------------------------------------------------------

    def wait_for_logon(self, timeout: int = LOGON_TIMEOUT_SECS) -> bool:
        """Block until the FIX session logs on, or timeout expires. Returns True on success."""
        deadline = time.time() + timeout
        while not self.session_id:
            if time.time() >= deadline:
                logger.error(f"Session logon timed out after {timeout}s")
                return False
            logger.info("Waiting for session logon...")
            time.sleep(1)
        logger.info(f"Session established: {self.session_id}")
        return True

    def publish_loop(self):
        """Called from main after logon is confirmed."""
        while True:
            if self.session_id:
                for symbol in SYMBOLS:
                    try:
                        quote = self.build_quote(symbol)
                        fix.Session.sendToTarget(quote, self.session_id)
                        logger.info(f"Sent QUOTE for {symbol}: {quote.toString().replace(chr(1), '|')}")

                        trade = self.build_trade(symbol)
                        fix.Session.sendToTarget(trade, self.session_id)
                        logger.info(f"Sent TRADE for {symbol}: {trade.toString().replace(chr(1), '|')}")

                    except fix.SessionNotFound as e:
                        logger.warning(f"Session not found: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error sending message for {symbol}: {e}")
            else:
                logger.info("Session dropped — waiting for reconnect...")

            time.sleep(PUBLISH_INTERVAL_SECS)


def main():
    config_file = os.environ.get("FIX_CONFIG_FILE", "/app/config/initiator.cfg")
    initiator   = None
    try:
        settings     = fix.SessionSettings(config_file)
        application  = MarketDataInitiator()
        storeFactory = fix.FileStoreFactory(settings)
        logFactory   = fix.FileLogFactory(settings)
        initiator    = fix.SocketInitiator(application, storeFactory, settings, logFactory)

        logger.info("Starting FIX initiator...")
        initiator.start()

        if not application.wait_for_logon():
            sys.exit(1)

        application.publish_loop()

    except (fix.ConfigError, fix.RuntimeError) as e:
        logger.error(f"FIX error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down initiator...")
    finally:
        if initiator is not None:
            initiator.stop()


if __name__ == "__main__":
    main()
