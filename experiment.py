
class Atomic:
    def __init__(self, value, callback):
        self.value = value
        self.callback = callback(self)

    def __call__(self, *args, **kwds):
        self.callback(*args, **kwds)

class Host:
    def __init__(self):
        pass
    def wrapper(self, obj: Atomic):
        def callback(secondary):
            print(obj.value, secondary)
        return callback

    def __call__(self):
        atomic = Atomic(value=4567, callback=self.wrapper)
        atomic(secondary="yay")

host = Host()
host() 
