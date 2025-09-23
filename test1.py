def ping(url, timeout=5.0):
    try:
        import httpx
    except ImportError:
        raise ValueError(
            "The httpx python package is not installed. Please install it with `pip install httpx`"
        )
    with httpx.Client(timeout=timeout) as client:
        try:
            response = client.post(
                f"http://10.0.70.225:7997/rerank",
                json={"query": "hello", "documents": ["hi there", "goodbye"], "model": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"},
            )
            if response.status_code < 400:
                print(response.json())
                return True
            else:
                print(response.status_code)
                return False
        except httpx.RequestError as e:
            print(e)
            return False

print(
    ping("http://10.0.70.225:7997/rerank", timeout=30)
)