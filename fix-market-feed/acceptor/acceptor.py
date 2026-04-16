import quickfix as fix
import logging
import sys
import time
import os
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ACCEPTOR] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional RT publishing — only imported when RT_ENABLED=true
# ---------------------------------------------------------------------------
RT_ENABLED = os.environ.get("RT_ENABLED", "false").lower() == "true"

if RT_ENABLED:
    try:
        import pykx as kx
        from rtpy import Publisher, RTParams
        logger.info("RT publishing enabled (rtpy + pykx loaded)")
    except ImportError as e:
        logger.error(f"RT_ENABLED=true but import failed: {e}")
        sys.exit(1)
else:
    logger.info("RT publishing disabled — running in log-only mode (set RT_ENABLED=true to enable)")


class MarketDataAcceptor(fix.Application):
    """
    FIX Acceptor — receives Trade (AE) and Quote (S) messages
    from the initiator, parses them, and optionally publishes to KDB Insights
    Reliable Transport via the rtpy Publisher.

    RT publishing is controlled by the RT_ENABLED environment variable.
    When disabled, messages are parsed and logged only — useful for local dev/testing.
    """

    def __init__(self, rt_publisher=None):
        super().__init__()
        self.pub = rt_publisher   # None when RT is disabled

    def onCreate(self, sessionID):
        logger.info(f"Session created: {sessionID}")

    def onLogon(self, sessionID):
        logger.info(f"Logon: {sessionID}")

    def onLogout(self, sessionID):
        logger.info(f"Logout: {sessionID}")

    def toAdmin(self, message, sessionID):
        pass

    def fromAdmin(self, message, sessionID):
        pass

    def toApp(self, message, sessionID):
        pass

    def fromApp(self, message, sessionID):
        msgType = fix.MsgType()
        message.getHeader().getField(msgType)

        if msgType.getValue() == fix.MsgType_Quote:   # 'S'
            self._parse_quote(message)
        elif msgType.getValue() == "AE":              # Trade Capture Report
            self._parse_trade(message)
        else:
            logger.warning(f"Unhandled message type: {msgType.getValue()}")

    # ------------------------------------------------------------------
    # Quote (S) -> RT stream "quote"
    # ------------------------------------------------------------------

    def _parse_quote(self, message):
        try:
            symbol    = fix.Symbol();    message.getField(symbol)
            bidPx     = fix.BidPx();     message.getField(bidPx)
            offerPx   = fix.OfferPx();   message.getField(offerPx)
            bidSize   = fix.BidSize();   message.getField(bidSize)
            offerSize = fix.OfferSize(); message.getField(offerSize)
        except fix.FieldNotFound as e:
            logger.error(f"[QUOTE] Missing required field — dropping message: {e}")
            return

        now = datetime.now(timezone.utc)

        logger.info(
            f"[QUOTE] sym={symbol.getValue()} time={now.isoformat()} "
            f"bid={bidPx.getValue():.4f} bsize={bidSize.getValue()} "
            f"ask={offerPx.getValue():.4f} asize={offerSize.getValue()}"
        )

        if self.pub is not None:
            try:
                data = kx.Table(
                    [[kx.TimestampAtom(now),
                      symbol.getValue(),
                      bidPx.getValue(),
                      offerPx.getValue(),
                      bidSize.getValue(),
                      offerSize.getValue()]],
                    columns=['time', 'sym', 'bid', 'ask', 'bsize', 'asize']
                )
                self.pub("quote", data)
                logger.info("[QUOTE] Published to RT stream topic 'quote'")
            except Exception as e:
                logger.error(f"[QUOTE] RT publish failed — message dropped: {e}")

    # ------------------------------------------------------------------
    # Trade (AE) -> RT stream "rawTrade"
    # ------------------------------------------------------------------

    def _parse_trade(self, message):
        try:
            symbol  = fix.Symbol();   message.getField(symbol)
            lastPx  = fix.LastPx();   message.getField(lastPx)
            lastQty = fix.LastQty();  message.getField(lastQty)
            side    = fix.Side();     message.getField(side)
        except fix.FieldNotFound as e:
            logger.error(f"[TRADE] Missing required field — dropping message: {e}")
            return

        now      = datetime.now(timezone.utc)
        side_str = "buy" if side.getValue() == fix.Side_BUY else "sell"

        logger.info(
            f"[TRADE] sym={symbol.getValue()} time={now.isoformat()} "
            f"px={lastPx.getValue():.4f} qty={lastQty.getValue()} side={side_str}"
        )

        if self.pub is not None:
            try:
                data = kx.Table(
                    [[kx.TimestampAtom(now),
                      symbol.getValue(),
                      side_str,
                      lastPx.getValue(),
                      lastQty.getValue()]],
                    columns=['time', 'sym', 'side', 'price', 'size']
                )
                self.pub("rawTrade", data)
                logger.info("[TRADE] Published to RT stream topic 'rawTrade'")
            except Exception as e:
                logger.error(f"[TRADE] RT publish failed — message dropped: {e}")


def main():
    config_file     = os.environ.get("FIX_CONFIG_FILE", "/app/config/acceptor.cfg")
    rt_config_file  = os.environ.get("RT_CONFIG_FILE",  "/app/config/rt_client.json")
    rt_state_dir    = os.environ.get("RT_STATE_DIR",    "/tmp/rt")

    if RT_ENABLED:
        if not os.path.exists(rt_config_file):
            logger.error(f"RT config not found: {rt_config_file} (set RT_CONFIG_FILE env var to override)")
            sys.exit(1)

        rt_params = RTParams(
            config_url=f"file://{rt_config_file}",
            rt_dir=rt_state_dir
        )

        with Publisher(rt_params) as pub:
            logger.info("Connecting to RT")
            _run_acceptor(config_file, rt_publisher=pub)
    else:
        logger.info("Starting acceptor in log-only mode (RT publishing disabled)")
        _run_acceptor(config_file, rt_publisher=None)


def _run_acceptor(config_file: str, rt_publisher):
    acceptor = None
    try:
        settings     = fix.SessionSettings(config_file)
        application  = MarketDataAcceptor(rt_publisher)
        storeFactory = fix.FileStoreFactory(settings)
        logFactory   = fix.FileLogFactory(settings)
        acceptor     = fix.SocketAcceptor(application, storeFactory, settings, logFactory)

        logger.info("Starting FIX acceptor...")
        acceptor.start()

        while True:
            time.sleep(1)

    except (fix.ConfigError, fix.RuntimeError) as e:
        logger.error(f"FIX error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down acceptor...")
    finally:
        if acceptor is not None:
            acceptor.stop()


if __name__ == "__main__":
    main()
