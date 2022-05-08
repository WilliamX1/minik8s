import time
import entities
import kubelet
import random


def monitor():
    # 监听pod的在状态，后面需要加入service
    second = 5
    while 1 == 1:
        time.sleep(second)
        # 获取kubelet中的pods和configs
        pods = {}
        configs = {}
        for name in pods:
            the_pods = pods[name]
            config = configs[name]
            num_for_create = 0
            index_for_del = []
            for i in range(len(pods[name])):
                if pods[name][i].status() == entities.Status.KILLED:
                    num_for_create += 1
                    index_for_del.append(i)

            for i in range(len(index_for_del)):
                del the_pods[num_for_create - 1 - i]
            for i in range(num_for_create):
                config['suffix'] = kubelet.create_suffix()
                pod = entities.Pod(config)
                the_pods.append(pod)
            pods[name] = the_pods


# 随即负载均衡
def lb():
    the_pods = []
    return the_pods[random.randint(0, len(the_pods)-1)]
