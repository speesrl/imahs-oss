import uuid
import json
import logging
import asyncio


from clients import REDIS

class ThinServer:
    def __init__(self, *, channel, sleep=.1):
        self.channel = channel
        self.sleep = max(sleep, .1)
    async def __call__(self):
        while True:
            await asyncio.sleep(self.sleep)
            data = REDIS().lpop(self.channel)
            if data is not None:
                try:
                    data = json.loads(data)
                    function, args = data.get('function'), data.get('args')
                    if function is None or args is None:
                        continue
                    assert isinstance(function, str) and isinstance(args, dict)
                    assert hasattr(self, function) and callable(getattr(self, function)), f'unknown function: {function}'
                    asyncio.create_task(getattr(self, function)(**args))
                except Exception as e:
                    logging.exception(e)

class ThinClient:
    def __init__(self, *, channel, function, args, sleep=.1):
        self.channel = channel
        self.function = function
        self.token = uuid.uuid4().hex
        self.sleep = max(sleep, .1)
        REDIS().lpush(self.channel, json.dumps({'function': self.function, 'args': {**args, 'token': self.token}}))
    async def __call__(self):
        while True:
            await asyncio.sleep(self.sleep)
            data = REDIS().rpop(self.channel)
            if data is not None:
                try:
                    data = json.loads(data)
                    _, result, token = data.get('function'), data.get('result'), data.get('token')
                    if result and token==self.token:
                        return result
                except Exception as e:
                    logging.exception(e)
