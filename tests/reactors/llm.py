import os
import asyncio 
import logging 
from mop.core import Ollama
from mop.utils import ExceptionFormatter


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'files')
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    lm = Ollama(
        redis_host=os.environ.get('redis_host'),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password'),
        redis_channel_requests=os.environ.get('redis_channel_requests'),
        host=os.environ.get('ollama_host')
    )
    asyncio.run(lm.event_driven_loop())
