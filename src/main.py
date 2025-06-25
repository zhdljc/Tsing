from Tsin.core import *

engine = Tsin()
engine.init()
while engine.update():
    pass
engine.shutdown()