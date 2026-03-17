from __future__ import annotations

import asyncio
import logging

from app.services.telegram.config import TelegramSettings
from app.services.telegram.bot import run_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    settings = TelegramSettings.from_env()
    asyncio.run(run_bot(settings))


if __name__ == "__main__":
    main()

