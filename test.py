from mop.clients import LibreTranslate

mt = LibreTranslate(url='http://127.0.0.1:8193')

print(mt('ciao, come stai?', src='it', tgt='en'))