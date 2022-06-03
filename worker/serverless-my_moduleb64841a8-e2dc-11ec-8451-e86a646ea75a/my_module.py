

def main(event: dict, context: dict)->dict:
    a = context.get('a')
    if not a:
        a = 0
    return {"result": a}


def add(event: dict, context: dict)->dict:
    a = context.get('a')
    if not a:
        a = 0
    b = context.get('a')
    if not b:
        b = 0
    return {"result": a+b}

def loop(event: dict, context: dict)->dict:
    a = list()
    while True:
        a.append("asd")
        pass
    return {"result": "hello {}{}!".format(event, context)}