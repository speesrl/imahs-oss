import os
import asyncio 
import logging 
from lib.core2 import Ollama
from lib.utils import ExceptionFormatter


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'files')
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(levelname)s: %(message)s"))
    lm = Ollama(
        os.environ.get('redis_host'),
        os.environ.get('redis_client'),
        os.environ.get('redis_password'),
        os.environ.get('redis_channel')
    )
    asyncio.run(lm())
