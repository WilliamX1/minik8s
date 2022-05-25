


def main(event: dict, context: dict)->dict:
    return {"result": "hello {}{}!".format(event, context)}
