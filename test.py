import traceback

def where_am_i():
    stack = traceback.extract_stack()
    filename, lineno, func, _ = stack[-2]
    return func

class A:
    def __call__(self):
        print(where_am_i())

a = A()
a()
