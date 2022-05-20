import subprocess
import utils
import logging


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


def util_create_chain_by_name(table, name):
    """
    create user-defined chain in specified table, if the chain already exists just return
    :param table: target table to create user-defined train
    :param name: the name of user-defined train
    :return: the first is a flag indicating if the chain already exists, False means it exists before your creation
            the second is the chain itself
    """
    for chain in table.chains:
        if str(chain.name) == str(name):
            return False, chain
    chain = table.create_chain(name)
    logging.info("Create [%s] Chain in NAT Table..."
                 % name)
    return True, chain


def util_insert_rule_by_name(chain, target_rule):
    """
    insert user-defined rule into some chain
    :param chain: target chain to insert your rule
    :param target_rule: user-defined rule
    :return: a flag indicating whether the rule already exists, False means it exists before your insertion
    """
    for rule in chain.rules:
        if str(rule.target.name) == str(target_rule.target.name):
            return False
    chain.insert_rule(target_rule)
    logging.info("Insert [%s] Rule in [%s] Chain..."
                 % (target_rule.target.name, chain.name))
    return True


def init_iptables():
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
    utils.create_chain('nat', 'KUBE-SERVICES')
    utils.create_chain('nat', 'KUBE-NODEPORTS')
    utils.create_chain('nat', 'KUBE-POSTROUTING')
    utils.create_chain('nat', 'KUBE-MARK-MASQ')
    utils.create_chain('nat', 'KUBE-MARK-DROP')

    """ In table `nat`, add some rule into chains """
    utils.insert_rule('nat', 'PREROUTING', 1,
                      utils.make_rulespec(
                          jump='KUBE-SERVICES',
                          comment='kubernetes service portals'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('nat', 'OUTPUT', 1,
                      utils.make_rulespec(
                          jump='KUBE-SERVICES',
                          comment='kubernetes service portals'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('nat', 'POSTROUTING', 1,
                      utils.make_rulespec(
                          jump='KUBE-POSTROUTING',
                          comment='kubernetes postrouting rules'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('nat', 'KUBE-MARK-DROP', 1,
                      utils.make_rulespec(
                          jump='MARK'
                      ),
                      utils.make_target_extensions(
                          ormark='0x8000'
                      ))
    utils.insert_rule('nat', 'KUBE-MARK-MASQ', 1,
                      utils.make_rulespec(
                          jump='MARK'
                      ),
                      utils.make_target_extensions(
                          ormark='0x4000'
                      ))
    utils.insert_rule('nat', 'KUBE-POSTROUTING', 1,
                      utils.make_rulespec(
                          jump='MASQUERADE',
                          comment='kubernetes service traffic requiring SNAT'
                      ),
                      utils.make_target_extensions(
                          mark='0x4000/0x4000'
                      ))
    utils.insert_rule('nat', 'KUBE-SERVICES', 1,
                      utils.make_rulespec(
                          jump='KUBE-NODEPORTS',
                          comment='kubernetes service nodeports; NOTE: this must be the last rule in this chain'
                      ),
                      utils.make_target_extensions(
                          addrtype='ADDRTYPE',
                          dst_type="LOCAL"
                      ))

    """ In table `filter`, set policy for some chains """
    utils.policy_chain('filter', 'INPUT', ['ACCEPT'])
    utils.policy_chain('filter', 'FORWARD', ['ACCEPT'])
    utils.policy_chain('filter', 'OUTPUT', ['ACCEPT'])

    """ In table `filter`, create some chains """
    utils.create_chain('filter', 'KUBE-EXTERNAL-SERVICES')
    utils.create_chain('filter', 'KUBE-FIREWALL')
    utils.create_chain('filter', 'KUBE-FORWARD')
    utils.create_chain('filter', 'KUBE-SERVICES')

    """ In table `filter`, add some rule into chains """
    utils.insert_rule('filter', 'INPUT', 1,
                      utils.make_rulespec(
                          jump='KUBE-SERVICES',
                          comment='kubernetes service portals'
                      ),
                      utils.make_target_extensions(
                          ctstate='NEW'
                      ))
    utils.insert_rule('filter', 'INPUT', 2,
                      utils.make_rulespec(
                          jump='KUBE-EXTERNAL-SERVICES',
                          comment='kubernetes externally-visible servie portals'
                      ),
                      utils.make_target_extensions(
                          ctstate='NEW'
                      ))
    utils.insert_rule('filter', 'INPUT', 3,
                      utils.make_rulespec(
                          jump='KUBE-FIREWALL'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('filter', 'FORWARD', 1,
                      utils.make_rulespec(
                          jump='KUBE-FORWARD',
                          comment='kubernetes forwarding rules'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('filter', 'FORWARD', 2,
                      utils.make_rulespec(
                          jump='KUBE-SERVICES',
                          comment='kubernetes service portals'
                      ),
                      utils.make_target_extensions(
                          ctstate='NEW'
                      ))
    utils.insert_rule('filter', 'OUTPUT', 1,
                      utils.make_rulespec(
                          jump='KUBE-SERVICES',
                          comment='kubernetes service portals'
                      ),
                      utils.make_target_extensions(
                          ctstate='NEW'
                      ))
    utils.insert_rule('filter', 'OUTPUT', 2,
                      utils.make_rulespec(
                          jump='KUBE-FIREWALL'
                      ),
                      utils.make_target_extensions())
    utils.insert_rule('filter', 'KUBE-FIREWALL', 1,
                      utils.make_rulespec(
                          jump='DROP',
                          comment='kubernetes firewall for dropping marked packets'
                      ),
                      utils.make_target_extensions(
                          mark='0x8000/0x8000'
                      ))
    utils.insert_rule('filter', 'KUBE-FORWARD', 1,
                      utils.make_rulespec(
                          jump='DROP',
                      ),
                      utils.make_target_extensions(
                          ctstate='INVALID'
                      ))
    utils.insert_rule('filter', 'KUBE-FORWARD', 2,
                      utils.make_rulespec(
                          jump='ACCEPT',
                          comment='kubernetes forwarding rules'
                      ),
                      utils.make_target_extensions(
                          mark='0x4000/0x4000'
                      ))


def set_iptables_clusterIP(cluster_ip, service_name, port, target_port, pod_ip_list, strategy='random', ip_prefix_len=32):
    """
    used for set service clusterIP
    reference to: https://www.bookstack.cn/read/source-code-reading-notes/kubernetes-kube_proxy_iptables.md
    :param cluster_ip: service clusterIP, which should be like xx.xx.xx.xx,
                        don't forget to set security group for that ip address
    :param service_name: service name, only used for comment here
    :param port: exposed service port, which can be visited by other pods by cluster_ip:port
    :param target_port: container runs on target_port actually, must be matched with `pod port`
                        if not matched, we can reject this request or just let it go depending on me
    :param pod_ip_list: a list of pod ip address, which belongs to the service target pod
    :param strategy: service load balance strategy, which should be random/roundrobin
    :param ip_prefix_len: must be 32 here, so use default value please
    :return:
    """
    """
    init iptables first, create some necessary chain and rules 
    init_iptables is an idempotent function, which means the effect of
    execute several times equals to the effect of execute one time
    """
    init_iptables()

    kubesvc = 'KUBE-SVC-' + utils.generate_random_str(12, 1)
    utils.create_chain('nat', kubesvc)
    utils.insert_rule('nat', 'KUBE-SERVICES', 1,
                      utils.make_rulespec(
                          jump=kubesvc,
                          destination='/'.join([cluster_ip, str(ip_prefix_len)]),
                          protocol='tcp',
                          comment=service_name + ': cluster IP',
                          dport=port
                      ),
                      utils.make_target_extensions())

    pod_num = len(pod_ip_list)
    for i in range(0, pod_num):
        kubesep = 'KUBE-SEP-' + utils.generate_random_str(12, 1)
        utils.create_chain('nat', kubesep)

        if strategy == 'random':
            prob = 1 / (pod_num - i)
            if i == pod_num - 1:
                utils.append_rule('nat', kubesvc,
                                  utils.make_rulespec(
                                      jump=kubesep
                                  ),
                                  utils.make_target_extensions())
            else:
                utils.append_rule('nat', kubesvc,
                                  utils.make_rulespec(
                                      jump=kubesep,
                                  ),
                                  utils.make_target_extensions(
                                      statistic=True,
                                      mode='random',
                                      probability=prob
                                  ))
        elif strategy == 'roundrobin':
            if i == pod_num - 1:
                utils.append_rule('nat', kubesvc,
                                  utils.make_rulespec(
                                      jump=kubesep
                                  ),
                                  utils.make_target_extensions())
            else:
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
        else:
            logging.error("Strategy Not Found! Use `random` or `roundrobin` Please")

        utils.append_rule('nat', kubesep,
                          utils.make_rulespec(
                              jump='KUBE-MARK-MASQ',
                              source='/'.join([pod_ip_list[i], str(ip_prefix_len)])
                          ),
                          utils.make_target_extensions())
        utils.append_rule('nat', kubesep,
                          utils.make_rulespec(
                              jump='DNAT',
                              protocol='tcp',
                          ),
                          utils.make_target_extensions(
                              match='tcp',
                              to_destination=':'.join([pod_ip_list[i], str(target_port)])
                          ))
    logging.info("Service [%s] Cluster IP: [%s] Port: [%s] Strategy: [%s]"
                 % (service_name, cluster_ip, port, strategy))


default_iptables_path = "./iptables-script"


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
