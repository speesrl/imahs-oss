import uuid
import json
import logging
import asyncio
import ollama
import datetime
import traceback
import time 
import base64

from clients import REDIS

class Customer:
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


def moving_average(avg, x, alpha=.1):
    return alpha*x + (1-alpha)*avg


def where_am_i():
    stack = traceback.extract_stack()
    _, _, func, _ = stack[-2]
    return func

class Provider:
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
    async def respond(self, result, replyto, token=''):
        try:
            REDIS().lpush(replyto, json.dumps({'function': where_am_i(), 'result': result, 'timestamp': datetime.datetime.now().isoformat()}))
        except Exception as e:
            logging.exception(e)

class ModelProvider(Provider):
    def __init__(self, *, resources: dict, channel: str, sleep:float=0.1):
        super().__init__(channel=channel, sleep=sleep)
        self.resources = resources
    async def connect(self, url, ps_timeout=3):
        client = None
        try:
            client = ollama.Client(host=url, timeout=ps_timeout)
            client.ps()
            client = ollama.Client(host=url, timeout=300)
        except Exception as e:
            client = None
            logging.exception(e)
        return client
    async def capabilites(self, replyto):
        try:
            result = {}
            for url in self.resources.keys():
                client = await self.connect(url)
                if client is None:
                    continue
                models = [entry.model for entry in client.list().models]
                server = self.resources.get(url, {})
                for model_group in server:
                    result[model_group] = []
                    for model in server[model_group]:
                        if model in models:
                            result[model_group] += [model]
            self.respond(result={'capabilities': result}, replyto=replyto)
        except Exception as e:
            logging.exception(e)
    async def llm(self, url, model, prompt, context, conversation, question, replyto):
        client = await self.connect(url)
        stream = client.chat(
            model=model,  
            messages=[
                {"role": "system", "content": prompt}, 
                {"role": "assistant", "content": context},       
                {"role": "assistant", "content": conversation},       
                {"role": "user", "content": question},
            ],
            options= {
                "temperature": 0.0
            },
            stream=True
        )
        resp = ''
        toksec = 1
        timestamp = time.perf_counter()
        for chunk in stream:
            delta = 1.0/(time.perf_counter() - timestamp + 1e-9)
            timestamp = time.perf_counter()
            toksec = moving_average(toksec, delta)
            resp += chunk.message.content
            self.respond(result={'token': chunk.message.content}, replyto=replyto)
        self.respond(result={'toksec': int(toksec)}, replyto=replyto)
    async def title(self, url, model, prompt, context, conversation, current, replyto):
        messages =[
                {"role": "assistant", "content": conversation},
                {"role": "assistant", "content": context}
        ]
        if current:
            messages+=[
                {"role": "assistant", "content": f"Current Title: {current}"},
                {"role": "user", "content": prompt}
            ]
        else:
            messages+=[
                {"role": "user", "content": prompt}
            ]
        res = ''
        client = await self.connect(url)
        stream = client.chat(
            messages=messages,
            model=model,  
            options= {
                "temperature": 0.0
            },
            stream=True
        )
        for chunk in stream:
            res += chunk.message.content
        self.respond(result={'title': res}, replyto=replyto)
    async def vlm(self, url, model, prompt, image, replyto):
        client : ollama.Client = await self.connect(url)
        stream = client.generate(
            model=model,
            prompt=prompt,
            stream=True,
            images=[base64.b64decode(image.encode('ascii'))],
            options={
                "temperature": 0.0,
            }
        )
        resp = ''
        toksec = 1
        timestamp = time.perf_counter()
        for chunk in stream:
            delta = 1.0/(time.perf_counter() - timestamp + 1e-9)
            timestamp = time.perf_counter()
            toksec = moving_average(toksec, delta)
            resp += chunk.response
            self.respond(result={'token': chunk.response}, replyto=replyto)
        self.respond(result={'toksec': int(toksec)}, replyto=replyto)

    


