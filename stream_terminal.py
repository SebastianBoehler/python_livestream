#!/usr/bin/env python3
"""Run the fixed-quality continuous HB terminal stream."""

import asyncio
import logging

from dotenv import load_dotenv

from broadcast.terminal_stream import (
    TerminalStreamConfigError,
    TerminalStreamRuntimeError,
    load_terminal_stream_config,
    run_terminal_stream_until_stopped,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv(override=False)
    try:
        config = load_terminal_stream_config()
        asyncio.run(run_terminal_stream_until_stopped(config))
    except TerminalStreamConfigError as error:
        logger.error("Terminal stream configuration rejected: %s", error)
        raise SystemExit(2) from None
    except TerminalStreamRuntimeError as error:
        logger.error("Terminal stream stopped: %s", error)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        logger.info("Terminal stream stopped by operator")


if __name__ == "__main__":
    main()
