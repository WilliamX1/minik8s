import numpy as np

def main(event: dict, context: dict)->dict:
    a = np.random.random(5)
    return {"result": "hello {}!".format(a)}

def loop(event: dict, context: dict)->dict:
    a = list()
    while True:
        a.append("asd")
        pass
    return {"result": "hello {}{}!".format(event, context)}