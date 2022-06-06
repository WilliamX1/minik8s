def add(event: dict, context: dict) -> dict:
    a = context.get('a')
    if not a:
        a = 0
    b = context.get('b')
    if not b:
        b = 0
    return {"result": a + b, 'a': a, 'b': b}
