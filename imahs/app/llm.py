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
            logging.FileHandler(os.path.join(root, 'imahs.log'), mode='a'),
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(levelname)s: %(message)s"))
    lm = Ollama()
    asyncio.run(lm())
