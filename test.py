from clients import Marker, REDIS
import logging
import json
import magic
from utils import FileUpload, DataclassJSONEncoder, fileupload_decoder
logging.basicConfig(level=logging.INFO)



marker = Marker(url='http://127.0.0.1:8192')

from nicegui import ui

def on_upload(e):
    f = FileUpload(filename=e.name, file=e.content.read(), content_type=e.type)
    REDIS('localhost', 'imahs', 'password').lpush('test', json.dumps([f], cls=DataclassJSONEncoder))
    l = REDIS('localhost', 'imahs', 'password').lpop('test')
    l = json.loads(l, object_hook=fileupload_decoder)
    l = l[0]
    mmagic   = magic.Magic(mime=True)
    print(l.file == f.file, mmagic.from_buffer(l.file))

ui.upload(on_upload=on_upload).classes('max-w-full')

ui.run(reconnect_timeout=300)