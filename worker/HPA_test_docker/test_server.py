import random

from flask import Flask

app = Flask(__name__)

stuck_flag = 0


def stuck():
    global stuck_flag
    while stuck_flag:
        print(random.randint(0, 5))


@app.route('/stuck')
def start_stuck():
    global stuck_flag
    if stuck_flag == 1:
        stuck_flag = 0
    else:
        stuck_flag = 1
        stuck()
    return "yes"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5053, processes=True)
