from imahs.lib.core2 import Ollama
import json 

print(
    json.loads(json.dumps({'name': '["a", 1]'}))
)