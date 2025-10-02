import ollama 

client = ollama.Client(
        host='http://127.0.0.1:11434'
    )
print(client.list())