import subprocess
import utils
import logging
import random


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


backup = list()


def alloc_service_clusterIP(service_dict: dict):
    """
    use etcd to record all used ip and try to allocate an ip begin with
        `10.xx.xx.xx`, which is easy for the security group settings
    :return:
    """
    max_alloc_num = 1000  # if exceed this num, that might be not enough service ip
    ip_allocated = set()
    ip = ''
    for service_name in service_dict['services_list']:
        ip = service_dict[service_name].get('clusterIP')
        if ip is not None and ip != '':
            ip_allocated.add(ip)

    while max_alloc_num > 0:
        max_alloc_num -= 1
        num0 = 10 # service ip should be like '10.xx.xx.xx'
        num1 = random.randint(0, 255)
        num2 = random.randint(0, 255)
        num3 = random.randint(0, 255)
        ip = '.'.join([str(num0), str(num1), str(num2), str(num3)])
        if ip not in ip_allocated:
            break
    if max_alloc_num <= 0:
        logging.error('No available service cluster ip address')
        return ip, False
    return ip, True


def init_iptables(iptables: dict):
    """
    init iptables for minik8s, create some necessary chains and insert some necessary rules
    reference to: https://www.bookstack.cn/read/source-code-reading-notes/kubernetes-kube_proxy_iptables.md
    :return: None
    """
    """ In table `nat`, set policy for some chains """
    utils.policy_chain('nat', 'PREROUTING', ['ACCEPT'])
    utils.policy_chain('nat', 'INPUT', ['ACCEPT'])
    utils.policy_chain('nat', 'OUTPUT', ['ACCEPT'])
    utils.policy_chain('nat', 'POSTROUTING', ['ACCEPT'])

    """ In table `nat`, create some new chains """
    iptables['chains'].append(utils.create_chain('nat', 'KUBE-SERVICES'))
    iptables['chains'].append(utils.create_chain('nat', 'KUBE-NODEPORTS'))
    iptables['chains'].append(utils.create_chain('nat', 'KUBE-POSTROUTING'))
    iptables['chains'].append(utils.create_chain('nat', 'KUBE-MARK-MASQ'))
    iptables['chains'].append(utils.create_chain('nat', 'KUBE-MARK-DROP'))

    """ In table `nat`, add some rule into chains """
    iptables['rules'].append(
        utils.insert_rule('nat', 'PREROUTING', 1,
                          utils.make_rulespec(
                              jump='KUBE-SERVICES',
                              comment='kubernetes service portals'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'OUTPUT', 1,
                          utils.make_rulespec(
                              jump='KUBE-SERVICES',
                              comment='kubernetes service portals'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'POSTROUTING', 1,
                          utils.make_rulespec(
                              jump='KUBE-POSTROUTING',
                              comment='kubernetes postrouting rules'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'KUBE-MARK-DROP', 1,
                          utils.make_rulespec(
                              jump='MARK'
                          ),
                          utils.make_target_extensions(
                              ormark='0x8000'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'KUBE-MARK-MASQ', 1,
                          utils.make_rulespec(
                              jump='MARK'
                          ),
                          utils.make_target_extensions(
                              ormark='0x4000'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'KUBE-POSTROUTING', 1,
                          utils.make_rulespec(
                              jump='MASQUERADE',
                              comment='kubernetes service traffic requiring SNAT'
                          ),
                          utils.make_target_extensions(
                              mark='0x4000/0x4000'
                        ))
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'KUBE-SERVICES', 1,
                          utils.make_rulespec(
                              jump='KUBE-NODEPORTS',
                              comment='kubernetes service nodeports; NOTE: this must be the last rule in this chain'
                          ),
                          utils.make_target_extensions(
                              addrtype='ADDRTYPE',
                              dst_type="LOCAL"
                          ))
    )

    """ In table `filter`, set policy for some chains """
    utils.policy_chain('filter', 'INPUT', ['ACCEPT'])
    utils.policy_chain('filter', 'FORWARD', ['ACCEPT'])
    utils.policy_chain('filter', 'OUTPUT', ['ACCEPT'])

    """ In table `filter`, create some chains """
    iptables['chains'].append(
        utils.create_chain('filter', 'KUBE-EXTERNAL-SERVICES')
    )
    iptables['chains'].append(
        utils.create_chain('filter', 'KUBE-FIREWALL')
    )
    iptables['chains'].append(
        utils.create_chain('filter', 'KUBE-FORWARD')
    )
    iptables['chains'].append(
        utils.create_chain('filter', 'KUBE-SERVICES')
    )

    """ In table `filter`, add some rule into chains """
    iptables['rules'].append(
        utils.insert_rule('filter', 'INPUT', 1,
                          utils.make_rulespec(
                              jump='KUBE-SERVICES',
                              comment='kubernetes service portals'
                          ),
                          utils.make_target_extensions(
                              ctstate='NEW'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'INPUT', 2,
                          utils.make_rulespec(
                              jump='KUBE-EXTERNAL-SERVICES',
                              comment='kubernetes externally-visible servie portals'
                          ),
                          utils.make_target_extensions(
                              ctstate='NEW'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'INPUT', 3,
                          utils.make_rulespec(
                              jump='KUBE-FIREWALL'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'FORWARD', 1,
                          utils.make_rulespec(
                              jump='KUBE-FORWARD',
                              comment='kubernetes forwarding rules'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'FORWARD', 2,
                          utils.make_rulespec(
                              jump='KUBE-SERVICES',
                              comment='kubernetes service portals'
                          ),
                          utils.make_target_extensions(
                              ctstate='NEW'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'OUTPUT', 1,
                          utils.make_rulespec(
                              jump='KUBE-SERVICES',
                              comment='kubernetes service portals'
                          ),
                          utils.make_target_extensions(
                              ctstate='NEW'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'OUTPUT', 2,
                          utils.make_rulespec(
                              jump='KUBE-FIREWALL'
                          ),
                          utils.make_target_extensions())
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'KUBE-FIREWALL', 1,
                          utils.make_rulespec(
                              jump='DROP',
                              comment='kubernetes firewall for dropping marked packets'
                          ),
                          utils.make_target_extensions(
                              mark='0x8000/0x8000'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'KUBE-FORWARD', 1,
                          utils.make_rulespec(
                              jump='DROP',
                          ),
                          utils.make_target_extensions(
                              ctstate='INVALID'
                          ))
    )
    iptables['rules'].append(
        utils.insert_rule('filter', 'KUBE-FORWARD', 2,
                          utils.make_rulespec(
                              jump='ACCEPT',
                              comment='kubernetes forwarding rules'
                          ),
                          utils.make_target_extensions(
                              mark='0x4000/0x4000'
                          ))
    )


def create_service(service_config: dict, pods_dict: dict):
    """
    used for create a new service using original config file
    :param service_config: dict {'kind': str, 'name': str, 'type': str,
        'selector': dict, 'ports': list, 'instance_name': str,
        'pod_instances': list, 'clusterIP': str}
    :param pods_dict: dict {'chain': list, 'rule': list}
    :return: None
    """

    iptables = dict()
    iptables['chains'] = list()
    iptables['rules'] = list()
    init_iptables(iptables=iptables)

    cluster_ip = service_config['clusterIP']
    service_name = service_config['name']
    ports = service_config['ports']
    pod_ip_list = list()
    for pod_instance in service_config['pod_instances']:
        pod_ip_list.append(pods_dict[pod_instance]['ip'])
    strategy = 'random'  # 'random' or 'roundrobin'

    for eachports in ports:
        port = eachports['port']
        targetPort = eachports['targetPort']
        protocol = eachports['protocol']
        set_iptables_clusterIP(cluster_ip=cluster_ip, service_name=service_name,
                               port=port, target_port=targetPort, protocol=protocol,
                               pod_ip_list=pod_ip_list, strategy=strategy, iptables=iptables)
    service_config['iptables'] = iptables
    service_config['status'] = 'Running'
    service_config['iphash'] = hash('.'.join(pod_ip_list))  # used for restart service
    logging.info('Service [%s] ClusterIP [%s] Running Successfully!'
                 % (service_name, cluster_ip))


def update_service(config_map):
    """
    evaluate service's pods and flush iptables
    :param config_map: config stored in etcd
    :return:
    """
    # TODO: find pod config in etcd and match service selector with pod labels

    # TODO: delete original pod iptables chain and rules

    # TODO: set current pod iptables chain and rules
    pass


def stop_service(name):
    # TODO: delete original pod iptables chain and rules

    # TODO: set service state to `Stopped`
    pass


def restart_service(service_config: dict, pods_dict: dict, force=False):
    """
    used for restart an exist service, simply
    delete all of the original iptable chains and rules
    then use create_service..
    :param force:
    :param service_config: dict {'kind': str, 'name': str, 'type': str,
        'selector': dict, 'ports': list, 'instance_name': str,
        'pod_instances': list, 'clusterIP': str}
    :param pods_dict: dict {'chain': list, 'rule': list}
    :return: None
    """
    # compare iplist hash with current ip list
    pod_ip_list = list()
    for pod_instance in service_config['pod_instances']:
        pod_ip_list.append(pods_dict[pod_instance]['ip'])

    print(service_config['iphash'])
    print(hash('.'.join(pod_ip_list)))
    if force is False and service_config['iphash'] == hash('.'.join(pod_ip_list)):
        print('here')
        return
    # delete original chains and rules
    iptables = service_config['iptables']
    rules = iptables['rules']
    for rule in rules:
        utils.delete_rule_by_spec(table=rule['table'],
                                  chain=rule['chain'],
                                  rulespec=rule['rule-specification'])
    chains = iptables['chains']
    for chain in chains:
        utils.delete_chain(chain['table'], chain['chain'])
    service_config.pop('iptables')
    # restart this service using create_service
    create_service(service_config, pods_dict)
    return


def get_service(name):
    """
    get service running state by service name
    :param name: target service name
    :return: a list of service running state
    """
    pass


def rm_service(name):
    """
    stop service and remove service from etcd forever
    :param name:
    :return:
    """
    pass


def set_iptables_clusterIP(cluster_ip, service_name, port, target_port, protocol,
                           pod_ip_list, strategy='random', ip_prefix_len=32, iptables: dict = None):
    """
    used for set service clusterIP, only for the first create
    reference to: https://www.bookstack.cn/read/source-code-reading-notes/kubernetes-kube_proxy_iptables.md
    :param cluster_ip: service clusterIP, which should be like xx.xx.xx.xx,
                        don't forget to set security group for that ip address
    :param service_name: service name, only used for comment here
    :param port: exposed service port, which can be visited by other pods by cluster_ip:port
    :param target_port: container runs on target_port actually, must be matched with `pod port`
                        if not matched, we can reject this request or just let it go depending on me
    :param protocol: http
    :param pod_ip_list: a list of pod ip address, which belongs to the service target pod
    :param strategy: service load balance strategy, which should be random/roundrobin
    :param ip_prefix_len: must be 32 here, so use default value please
    :param iptables: a dict to record each iptable chain and rules create by user
    :return:
    """
    """
    init iptables first, create some necessary chain and rules 
    init_iptables is an idempotent function, which means the effect of
    execute several times equals to the effect of execute one time
    """
    kubesvc = 'KUBE-SVC-' + utils.generate_random_str(12, 1)

    iptables['chains'].append(
        utils.create_chain('nat', kubesvc)
    )
    iptables['rules'].append(
        utils.insert_rule('nat', 'KUBE-SERVICES', 1,
                          utils.make_rulespec(
                              jump=kubesvc,
                              destination='/'.join([cluster_ip, str(ip_prefix_len)]),
                              protocol=protocol,
                              comment=service_name + ': cluster IP',
                              dport=port
                          ),
                          utils.make_target_extensions())
    )

    pod_num = len(pod_ip_list)
    for i in range(0, pod_num):
        kubesep = 'KUBE-SEP-' + utils.generate_random_str(12, 1)
        iptables['chains'].append(
            utils.create_chain('nat', kubesep)
        )

        if strategy == 'random':
            prob = 1 / (pod_num - i)
            if i == pod_num - 1:
                iptables['rules'].append(
                    utils.append_rule('nat', kubesvc,
                                      utils.make_rulespec(
                                          jump=kubesep
                                      ),
                                      utils.make_target_extensions())
                )
            else:
                iptables['rules'].append(
                    utils.append_rule('nat', kubesvc,
                                      utils.make_rulespec(
                                          jump=kubesep,
                                      ),
                                      utils.make_target_extensions(
                                          statistic=True,
                                          mode='random',
                                          probability=prob
                                      ))
                )
        elif strategy == 'roundrobin':
            if i == pod_num - 1:
                iptables['rules'].append(
                    utils.append_rule('nat', kubesvc,
                                      utils.make_rulespec(
                                          jump=kubesep
                                      ),
                                      utils.make_target_extensions())
                )
            else:
                iptables['rules'].append(
                    utils.append_rule('nat', kubesvc,
                                      utils.make_rulespec(
                                          jump=kubesep
                                      ),
                                      utils.make_target_extensions(
                                          statistic=True,
                                          mode='nth',
                                          every=pod_num - i,
                                          packet=0
                                      ))
                )
        else:
            logging.error("Strategy Not Found! Use `random` or `roundrobin` Please")

        iptables['rules'].append(
            utils.append_rule('nat', kubesep,
                              utils.make_rulespec(
                                  jump='KUBE-MARK-MASQ',
                                  source='/'.join([pod_ip_list[i], str(ip_prefix_len)])
                              ),
                              utils.make_target_extensions())
        )
        iptables['rules'].append(
            utils.append_rule('nat', kubesep,
                              utils.make_rulespec(
                                  jump='DNAT',
                                  protocol=protocol,
                              ),
                              utils.make_target_extensions(
                                  match=protocol,
                                  to_destination=':'.join([pod_ip_list[i], str(target_port)])
                              ))
        )
    logging.info("Service [%s] Cluster IP: [%s] Port: [%s] TargetPort: [%s] Strategy: [%s]"
                 % (service_name, cluster_ip, port, target_port, strategy))


default_iptables_path = "./sources/iptables-script"


def save_iptables(path=default_iptables_path):
    """
    save current iptables to disk file, equals to the command:
    ```sudo iptables-save > path```
    :param path: saved file path
    :return: None
    """
    p = subprocess.Popen("iptables-save", stdout=subprocess.PIPE)
    f = open(path, "wb")
    f.write(p.stdout.read())
    f.close()
    logging.info("Save iptables successfully!")


def restore_iptables(path=default_iptables_path):
    """
    restore iptables from disk file, equals to the command:
    ```sudo iptables-restore < path```
    :param path: restored file path
    :return: None
    """
    f = open(path, "wb")
    p = subprocess.Popen("iptables-save", stdin=f)
    p.communicate()
    f.close()
    logging.info("Restore iptables successfully!")


def clear_iptables():
    """
    clear whole iptables, equals to the command:
    ```sudo iptables -F && sudo iptables -X```
    :return: None
    """
    utils.clear_rules()
    utils.dump_iptables()
    logging.info("Clear iptables successfully ...")


def example():
    set_iptables_clusterIP(cluster_ip='10.1.2.3',
                           service_name='you-service',
                           port=1111,
                           target_port=8080,
                           ip_prefix_len=32,
                           pod_ip_list=['172.17.0.2', '172.17.0.4'],
                           strategy='random')


if __name__ == '__main__':
    example()