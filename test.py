
class Atomic:
    def __init__(self, value, callback):
        self.value = value
        self.callback = callback

    def __call__(self, *args, **kwds):
        self.callback(*args, **kwds)

class Host:
    def __init__(self):
        self.atomic = Atomic(value=4567, callback=self.callback)

    def callback(self, secondary):
        print(self.atomic.value, secondary)

    def __call__(self):
        self.atomic(secondary="yay")

host = Host()
host() 
