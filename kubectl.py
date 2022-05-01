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
    yaml_path = askopenfilename(filetypes=[('YAML', '*.yaml')])
    entry1.insert(0, yaml_path)

def upload():
    yaml_path = entry1.get()
    print('the yaml path is：', yaml_path)
    try:
        config: dict = yaml_loader.load(yaml_path)
        object_name = config['name']
    except Exception as e:
        print(e.__str__())
        return
    url = "http://127.0.0.1:5050/pods"
    try:
        json_data = json.dumps(config)
        r = requests.post(url=url, json=json_data)
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
    btn2 = ttk.Button(frm, text='upload', command=upload)
    btn2.grid(row=10, column=0, ipadx='3', ipady='3', padx='10', pady='20')
    entry1 = ttk.Entry(frm, width='40')
    entry1.grid(row=0, column=1)
    text1 = ttk.Text(frm, width='55', height='15')
    text1.grid(row=1, column=1)
    root.mainloop()