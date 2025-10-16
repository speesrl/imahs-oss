import os
import asyncio 
import logging 
from mop.core import Ollama, LibreTranslate
from mop.utils import ExceptionFormatter

async def main():
    lm = Ollama(
        redis_host=os.environ.get('redis_host'),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password'),
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:llm",
        host=os.environ.get('ollama_host')
    )
    mt = LibreTranslate(
        redis_host=os.environ.get('redis_host'),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password'),
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:mt",
        url=os.environ.get('libretranslate_host')
    )
    await asyncio.gather(
        lm.event_driven_loop(),
        mt.event_driven_loop()
    )

if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'files')
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    asyncio.run(main())
