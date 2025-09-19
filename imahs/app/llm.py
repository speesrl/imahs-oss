import os 
import logging 
logging.basicConfig(level=logging.INFO)
from nicegui import ui
from imahs.lib import clients

@ui.page("/")
def index():
    reranker = clients.ReRanker(
        url=os.environ.get("url_infinity"), model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    )

    logging.info(
        reranker("hello there mr.", ["greetings", "salutations", "camels"])
    )
ui.run(host='0.0.0.0', port=8118)