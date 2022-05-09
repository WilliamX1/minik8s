import os
import random

default_ip = '-1.-1.-1.-1'
ip_dict = {}


def create_pod_ipaddr():
    ip = ''
    cnt = 1000
    while cnt > 0:
        num1, num2, num3, num4 = \
            '192', '168', \
            random.randint(0, 255), random.randint(0, 255)
        ip = '.'.join([str(num1), str(num2), str(num3), str(num4)])
        if ip not in ip_dict:
            break
        else:
            cnt -= 1
    if cnt > 0:
        print('INFO: pod ip address ' + ip + ' is in use...')
        return ip
    else:
        print('Error: No available ip address...')
        return default_ip
