import os 
import uuid
import json
import time 
import magic
import base64
import ollama
import hashlib 
import logging
import asyncio
import datetime
import chromadb
from typing import Dict, List
from imahs.lib.db import MYSQL, ChatsTable
from imahs.lib.clients import REDIS, Embedder, ReRanker, Marker
from imahs.lib.utils  import FilesLoader, moving_average, where_am_i, FileUpload, ContentLoader

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

class Provider:
    def __init__(self, *, channel: str, sleep:float=0.1):
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
        messages = []
        if prompt:
            messages += [{"role": "system", "content": prompt}]
        if context:
            messages += [{"role": "assistant", "content": context}]
        if conversation:
            messages += [{"role": "assistant", "content": conversation}]
        if question:
            messages += [{"role": "user", "content": question}]
        if not messages:
            self.respond(result={'token': 'Errore!'}, replyto=replyto)
            self.respond(result={'toksec': 0},        replyto=replyto)
            return
        stream = client.chat(
            model=model,  
            messages=messages,
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


class RAGProvider(Provider):
    def __init__(
            self,
            *,
            root,
            url_infinity,
            host_chroma,
            port_chroma
            , channel: str, sleep:float=0.1,
            embedder="intfloat/multilingual-e5-large-instruct",
            reranker="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        ):
        super().__init__(channel=channel, sleep=sleep)
        self.root        = root
        self.src         = os.path.abspath(os.path.join(self.root, "documents"))
        self.uid         = hashlib.blake2b('root documents'.encode(), digest_size=16, usedforsecurity=False).hexdigest()
        self.filesloader = FilesLoader()
        self.client      = chromadb.HttpClient(host=host_chroma, port=port_chroma, settings=chromadb.config.Settings(anonymized_telemetry=False))
        self.embedder    = Embedder(url=url_infinity, model=embedder)
        self.reranker    = ReRanker(url=url_infinity, model=reranker)
        if not os.path.exists(self.root):
            logging.warning(f"root {self.root} does not exist")
    async def list(self, replyto: str):
        REDIS().lpush(replyto, json.dumps({'function': 'list', 'result': self.filesloader.list(self.src)}))
    async def load(self):
        if not os.path.exists(self.src):
            logging.warning(f"source_directory {self.src} does not exist")
            return
        try:
            collection = self.client.get_or_create_collection(f"{self.uid}_docs", embedding_function=self.embedder)
            current = collection.get(
                where={"archived": False},
                include=['metadatas']
            )
            existing_files = list(set([metadata['checksum'] for metadata in current['metadatas']]))
        except Exception as e:
            logging.exception(e)
            existing_files = []
        documents = self.filesloader.load_all(self.src, existing_files=existing_files)
        if documents:
            collection = self.client.get_or_create_collection(f"{self.uid}_docs", embedding_function=self.embedder)
            collection.add(
                documents=[document.page_content for document in documents],
                ids=[uuid.uuid4().hex for _ in range(len(documents))],
                metadatas=[{**document.metadata, "archived": False} for document in documents]
            )       
    async def query(self, question, checksum: str, replyto):
        result = []
        try:
            collection = self.client.get_or_create_collection(f"{self.uid}_docs", embedding_function=self.embedder)
            response = collection.query(
                query_texts=[question],
                where={"archived": False}
            )
            try:
                keeps = self.reranker(question, response["documents"][0])
            except Exception as e:
                logging.exception(e)
                keeps = [*range(len(response["documents"][0]))]
            ids, metas, docs = [response["ids"][0][idx] for idx in keeps], [response["metadatas"][0][idx] for idx in keeps], [response["documents"][0][idx] for idx in keeps]
            
            logging.info(f"debugging rag, question {question}, docs: {docs}")
            for _id, meta, doc in zip(ids, metas, docs):
                result.append({
                    "id": _id,
                    "content": doc,
                    "metadata": meta
                })
            REDIS().lpush(replyto, json.dumps({'function': 'query', 'result': result, 'checksum': checksum}))
        except Exception as e:
            logging.exception(e)
    async def memory(self, replyto, checksum: str = ''):
        collection = self.client.get_or_create_collection(f"{self.uid}_docs", embedding_function=self.embedder)
        where=[{"archived": False}]
        if checksum:
            where += [{'checksum': checksum}]
        results = collection.get(
            where={"$and": where} if len(where) > 1 else where[0]
        )
        final = {}
        for _id, meta, doc in zip(results["ids"], results["metadatas"], results["documents"]):
            if meta.get('checksum') in final:
                final[meta.get('checksum')]['content'] += [doc]
            else:
                final[meta.get('checksum')] = {
                    "id": _id,
                    "content": [doc],
                    "metadata": meta
                }
        REDIS().lpush(replyto, json.dumps({'function': 'memory', 'result': final}))

class FileService(Provider):
    def __init__(
            self, 
            *, root, url, channel: str, sleep:float=0.1
        ):
        super().__init__(channel=channel, sleep=sleep)
        self.root    = root
        self.magic   = magic.Magic(mime=True)
        self.marker  = Marker(url = url)
        self.allowed = ['application/pdf']
    async def convert(self, files: List[FileUpload], replyto: str):
        try:
            for file in files:
                try:
                    mimetype = magic.from_buffer(file.file)
                    assert mimetype == file.content_type
                    if mimetype not in self.allowed:
                        continue 
                    converted = self.marker(file)
                    converted['metadata']['source'] = file.filename
                    converted['metadata']['mimetype'] = file.content_type
                    REDIS().push(replyto,  json.dumps({'function': 'memory', 'result': converted}))
                except Exception as e:
                    logging.exception(e)
                    continue
        except Exception as e:
            logging.exception(e)


class ChatService(Provider):
    def userid(self, username: str):
        return hashlib.blake2b(username.encode(), digest_size=16, usedforsecurity=False).hexdigest()
    def __init__(
            self, 
            url_infinity,
            host_chroma,
            port_chroma, host_mysql, port_mysql, channel: str, sleep:float=0.1,
            embedder="intfloat/multilingual-e5-large-instruct",
            reranker="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        ):
        super().__init__(channel=channel, sleep=sleep)
        self.host_mysql, self.port_mysql = host_mysql, port_mysql
        self.client      = chromadb.HttpClient(host=host_chroma, port=port_chroma, settings=chromadb.config.Settings(anonymized_telemetry=False))
        self.embedder    = Embedder(url=url_infinity, model=embedder)
        self.reranker    = ReRanker(url=url_infinity, model=reranker)
    async def update(self, username, chatid, title, replyto):
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            result = collection.get(
                where={"$and": [{"archived": False}, {'chatid': chatid}]},
                include=["metadatas"]
            )
            for idx, meta in zip(result['ids'], result['metadatas']):
                meta["title"] = title
                collection.update(
                    ids=[idx],
                    metadatas=[meta]
                )
        except Exception as e:
            logging.exception(e)
    
    async def add(self, username, chatid, docs: List[Dict[str, str]], replyto):
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            for doc in docs:
                if 'text' in doc:
                    timestamp = datetime.datetime.now().isoformat()
                    historical = {
                        'text': doc['text'],
                        "chatid": chatid,
                        'username': username,
                        'author': doc['author'],
                        'timestamp': timestamp,
                        'source': doc.get('metadata', {}).get('source', ''),
                        'checksum': doc.get('metadata', {}).get('checksum', ''),
                    }
                    if 'imageid' in doc:
                        metadata = {
                            "chatid": chatid,
                            'username': username,
                            'author': doc['author'],
                            'imageid': doc['imageid'],
                            'timestamp': timestamp,
                            'archived': False,
                            **doc['metadata'],
                        }
                        historical['otherid'] = doc['imageid']
                        collection.add(
                            documents=[doc['text']],
                            ids=[uuid.uuid4().hex],
                            metadatas=[
                                metadata
                            ]
                        )
                    elif 'fileid' in doc:
                        loader = ContentLoader(doc['text'])
                        tmp = [d.page_content for d in loader.lazy_load()]
                        metadata = {
                            "chatid": chatid,
                            'username': username,
                            'author': doc['author'],
                            'fileid': doc['fileid'],
                            'timestamp': timestamp,
                            'archived': False,
                            **doc['metadata'],
                            **loader.metadata
                        }
                        historical['otherid'] = doc['fileid']
                        collection.add(
                            documents=tmp,
                            ids=[uuid.uuid4().hex for _ in range(len(tmp))],
                            metadatas=[
                                metadata
                                for _ in range(len(tmp))
                            ]
                        )
                    else:
                        collection.add(
                            documents=[doc['text']],
                            ids=[uuid.uuid4().hex],
                            metadatas=[
                                {
                                    "chatid": chatid,
                                    'username': username,
                                    'author': doc['author'],
                                    'timestamp': timestamp,
                                    'archived': False,
                                    **doc.get('metadata', {})
                                }
                            ]
                        )
                        historical['otherid'] = ''
                REDIS().lpush(replyto, json.dumps({'function': 'add', 'result': doc})) 
                historical['msgid'] = hashlib.blake2b(json.dumps(historical).encode(), digest_size=16, usedforsecurity=False).hexdigest()
                with MYSQL(self.host_mysql, self.port_mysql, ...) as sql:
                    sql.session.execute(
                        sql.insert(ChatsTable).values(
                            **historical
                        )
                    )
        except Exception as e:
            logging.exception(e)      
    async def title(self, username, chatid: str):
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            result = collection.get(
                where={"$and": [{"archived": False}, {'chatid': chatid}]},
                include=["metadatas"]
            )
            for meta in result['metadatas']:
                return meta["title"]
        except Exception as e:
            logging.exception(e)
    async def archive(self, username, chatid: str, replyto:str):
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            result = collection.get(
                where={"$and": [{"archived": False}, {'chatid': chatid}]},
                include=["metadatas"]
            )
            for idx, meta in zip(result['ids'], result['metadatas']):
                meta["archived"] = True
                collection.update(
                    ids=[idx],
                    metadatas=[meta]
                )
        except Exception as e:
            logging.exception(e)
        REDIS().lpush(replyto, json.dumps({'function': 'archive', 'result': True}))
    async def query(self, username, chatid: str, question, checksum: str, replyto):
        res = {
            'messages': [],
            'title': await self.title(username, chatid)
        }
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            response = collection.query(
                query_texts=[question],
                where={"$and": [{"archived": False}, {'chatid': chatid}]},
                n_results=40
            )
            try:
                keeps = self.reranker(question, response["documents"][0], percentile=40, relevance=.001)
            except Exception as e:
                logging.exception(e)
                keeps = [*range(len(response["documents"][0]))]
            ids, metas, docs = [response["ids"][0][idx] for idx in keeps], [response["metadatas"][0][idx] for idx in keeps], [response["documents"][0][idx] for idx in keeps]
            for _id, meta, doc in zip(ids, metas, docs):
                res['messages'].append({
                    "id": _id,
                    "content": doc,
                    "timestamp": meta["timestamp"]
                })
        except Exception as e:
            logging.exception(e)
        REDIS().lpush(replyto, json.dumps({'function': 'query', 'result': res, 'checksum': checksum}))
    async def _history(self, username, chatid: str, replyto):
        history = {}
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            result = collection.get(
                where={"$and": [{"archived": False}, {'chatid': chatid}]}
            )
            history = {'title': await self.title(username, chatid), 'messages': {}}
            for _id, meta, doc in zip(result["ids"], result["metadatas"], result["documents"]):
                if 'fileid' in meta:
                    history['messages'][meta['fileid']] = {
                        "id": _id,
                        "content": doc,
                        "metadata": meta
                    }
                else:
                    history['messages'][_id] = {
                        "id": _id,
                        "content": doc,
                        "metadata": meta
                    }
            history['messages'] = [*history['messages'].values()]
        except Exception as e:
            logging.exception(e)
        return history
    async def history(self, username, chatid: str, replyto):
        res = await self._history(username, chatid, replyto)
        REDIS().lpush(replyto, json.dumps({'function': 'history', 'result': res}))
    async def export(self, username, chatid: str, replyto):
        res = await self._history( username, chatid, replyto)
        REDIS().lpush(replyto, json.dumps({'function': 'export', 'result': res}))
    async def histories(self, username: str, replyto, archived:bool=False):
        res = {}
        try:
            collection = self.client.get_or_create_collection(f"{self.userid(username)}_chat", embedding_function=self.embedder)
            result = collection.get(
                where={"archived": archived},
                include=["metadatas"]
            )
            for meta in result['metadatas']:
                if meta['chatid'] not in res:
                    res[meta['chatid']] = {
                        'chatid': meta['chatid'],
                        'title': meta.get('title', '')
                    }
        except Exception as e:
            logging.exception(e)
        REDIS().lpush(replyto, json.dumps({'function': 'histories', 'result': [*res.values()]}))

