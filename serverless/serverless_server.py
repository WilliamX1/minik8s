from flask import Flask, request
import importlib

app = Flask(__name__)

@app.route('/function/<string:module>/<string:function>', methods=['GET', 'POST'])
def execute_function(module: str, function: str):
    module = importlib.import_module(module)  # 绝对导入
    event = {"method": "http"}
    context = request.form.to_dict()
    result = eval("module.{}".format(function))(event, context)
    return result, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4999, processes=True)
