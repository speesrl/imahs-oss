from clients import MarkerClient
import logging
from utils import FileUpload
logging.basicConfig(level=logging.INFO)


marker = MarkerClient(url='http://127.0.0.1:8192')

from nicegui import ui

def on_upload(e):
    res = marker(file=FileUpload(filename=e.name, file=e.content.read(), content_type=e.type))
    logging.info(res)

ui.upload(on_upload=on_upload).classes('max-w-full')

ui.run(reconnect_timeout=300)