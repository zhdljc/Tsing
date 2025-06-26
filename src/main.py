from Tsin.core import *

if __name__ == '__main__':
    engine = Tsin()
    engine.init()
    while engine.update():
        pass
    engine.shutdown()