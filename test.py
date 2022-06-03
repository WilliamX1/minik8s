import  requests, json

if __name__ == '__main__':
    r = requests.post('http://20.20.71.6:5054/submit',
                      json=json.dumps({'module_name': 'add'}))
    json_data = json.loads(r.content.decode('UTF-8'))
    print(json_data)