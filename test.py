from clients import REDIS

a = REDIS(
    client_name='test',
    password='',
    host='http://localhost:6379'
)
b = REDIS(
    client_name='test',
    password='',
    host='http://localhost:6379'
)

print(hex(id(a))==hex(id(b)))