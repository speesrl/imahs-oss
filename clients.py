import uuid
import yaml
import hashlib
import redis
import logging
import numpy as np
from chromadb.api.types import Embeddings, Documents
from utils import Singleton, FileUpload


class Marker:
    def __init__(
        self,
        *,
        url: str
    ):
        try:
            import httpx
        except ImportError:
            raise ValueError(
                "The httpx python package is not installed. Please install it with `pip install httpx`"
            )
        self.url = url
        self._session = httpx.Client(timeout=300)
    def __call__(
            self, 
            file: FileUpload
        ) -> Embeddings:
        response = self._session.post(
            f"{self.url}/marker/upload",
            data={
                "force_ocr": True,
                "paginate_output": False,
                "output_format": "markdown"
            },
            files={
                "file": (file.filename, file.file, file.content_type)
            }
        ).json()
        text       = response.get('output', "")
        images     = response.get('images', {})
        checksum = hashlib.blake2b(text.encode(), digest_size=16, usedforsecurity=False).hexdigest()
        try:
            title = response.get('metadata', {}).get('table_of_contents')[0].get("title", f'not found #{checksum}')
        except:
            title = f'not found #{checksum}'
        metadata = {"title": title, 'source': ''}
        return {
            'images': images,
            'text': text,
            'metadata': metadata,
            'checksum': checksum
        }

class InfinityClient:
    def __init__(
        self,
        *,
        url: str,
        model: str
    ):
        try:
            import httpx
        except ImportError:
            raise ValueError(
                "The httpx python package is not installed. Please install it with `pip install httpx`"
            )
        self.url = url
        self.model = model
        self._session = httpx.Client(timeout=300)


class Embedder(InfinityClient):
    def __call__(self, input: Documents) -> Embeddings:
        response = self._session.post(
            f"{self.url}/embeddings",
            json={"input": input, "model": self.model},
        ).json()
        return [np.array(partial.get('embedding'), dtype=np.float32) for partial in response.get('data', [])]

class ReRanker(InfinityClient):
    def __call__(self, query: str, documents: Documents, relevance_min=0.1, relevance=0.4, percentile=80) -> Embeddings:
        relevance_min = min(relevance_min, relevance)
        response = self._session.post(
            f"{self.url}/rerank",
            json={"query": query, "documents": documents, "model": self.model},
        ).json()
        results = response.get('results', [])
        try:
            relevances = np.zeros((len(results,)), dtype=np.float64)
            for entry in results:
                if 'index' in entry:
                    relevances[entry.get('index')] = entry.get('relevance_score')
            if relevances.tolist():
                keeps = [idx for idx,(r, m, p) in enumerate(zip(relevances > relevance, relevances > relevance_min, relevances > np.percentile(relevances, percentile))) if (r or p) and m]
            else:
                keeps = [*range(len(documents))]
            return keeps
        except Exception as e:
            logging.exception(e)
            return []
    
class REDIS(metaclass=Singleton):
    def __new__(self, host, client_name, password):
        self = redis.Redis(
                host=host, 
                decode_responses=True,
                client_name=client_name,
                password=password
        )
        return self
