import os 

from imahs.lib.clients import ReRanker

reranker = ReRanker(
    url=os.environ.get("url_infinity"), model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

print(
    reranker("hello there mr.", ["greetings", "salutations", "camels"])
)