from tkinter import filedialog
import requests
import warnings
import ttkbootstrap as ttk
from tkinter.filedialog import askopenfilename
from ttkbootstrap.constants import *
import yaml_loader
import json


def choose_file():
    print("please choose a file upload to api server")
    # yaml_path = askopenfilename(filetypes=[('YAML', '*.yaml')])

    yaml_path = askopenfilename()
    entry1.insert(0, yaml_path)


def upload_yaml():
    yaml_path = entry1.get()
    print('the yaml path is：', yaml_path)
    try:
        config: dict = yaml_loader.load(yaml_path)
        object_name = config['name']
    except Exception as e:
        print(e.__str__())
        return
    url = "http://127.0.0.1:5050/{}".format(config['kind'])
    try:
        json_data = json.dumps(config)
        r = requests.post(url=url, json=json_data)
        text1.insert(ttk.END, r.content.decode('utf-8'))
    except requests.exceptions.ConnectionError:
        text1.insert(ttk.END, "can not post to " + url + ", please check API Server")
    finally:
        text1.insert(ttk.END, '\n')
        text1.update()


def upload_python_script():
    python_path = entry1.get()
    print('the python path is：', python_path)
    try:
        url = "http://127.0.0.1:5050/Pod/"
        module_name = None
        with open(python_path) as f:
            for i in range(len(f.name) - 1, 0, -1):
                if f.name[i] == '/':
                    name = f.name[i + 1:]
                    break
            content = f.read()
        assert module_name
        config: dict = yaml_loader.load('./serverless/serverless-pod.yaml')
        config['name'] += module_name
        config['metadata']['labels']['module_name'] = module_name
        config['containers']['name'] = module_name
        config['containers']['image'] = "{}:latest".format(module_name)
        config['script_data'] = content
        r = requests.post(url=url, json=json.dumps(config))
        text1.insert(ttk.END, r.content.decode('utf-8'))
    except requests.exceptions.ConnectionError:
        text1.insert(ttk.END, "can not post to " + url + ", please check API Server")
    finally:
        text1.insert(ttk.END, '\n')
        text1.update()


if __name__ == '__main__':
    root = ttk.Window(themename="journal")
    frm = ttk.Frame(root)
    frm.grid(padx='20', pady='30')
    btn1 = ttk.Button(frm, text='choose file', command=choose_file)
    btn1.grid(row=0, column=0, ipadx='3', ipady='3', padx='10', pady='20')
    btn2 = ttk.Button(frm, text='upload', command=upload_yaml)
    btn2.grid(row=10, column=0, ipadx='3', ipady='3', padx='10', pady='20')
    btn3 = ttk.Button(frm, text='upload_python', command=upload_python_script)
    btn3.grid(row=20, column=0, ipadx='3', ipady='3', padx='10', pady='20')
    entry1 = ttk.Entry(frm, width='40')
    entry1.grid(row=0, column=1)
    text1 = ttk.Text(frm, width='55', height='15')
    text1.grid(row=1, column=1)
    root.mainloop()
