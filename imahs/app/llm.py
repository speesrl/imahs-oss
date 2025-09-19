import os 
import logging 
logging.basicConfig(level=logging.INFO)
from nicegui import ui
from lib.clients import ReRanker

@ui.page("/")
def index():
    logging.info("connecting")
    try:
        reranker = ReRanker(
            url=os.environ.get("url_infinity"), model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        )

        logging.info(
            reranker("hello there mr.", ["greetings", "salutations", "camels"])
        )
    except Exception as e:
        logging.exception(e)
        logging.exception(os.environ.get("url_infinity"))
ui.run(host='0.0.0.0', port=8118)