import os
import random
import iptc
import subprocess
import utils

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


def print_all_filter_table():
    # This function has to be run in root,
    # so I try to not use this one
    table = iptc.Table(iptc.Table.FILTER)
    for chain in table.chains:
        print("======================")
        print("Chain ", chain.name)
        for rule in chain.rules:
            print("Rule", "proto:", rule.protocol, "src:", rule.src, "dst:", \
                  rule.dst, "in:", rule.in_interface, "out:", rule.out_interface, )
            print("Matches:")
            for match in rule.matches:
                print(match.name)
            print("Target:")
            print(rule.target.name)
    print("=====================")


def test_insert_rule():
    rule = iptc.Rule()
    rule.src = '127.0.0.1'
    rule.protocol = 'udp'
    rule.target = rule.create_target('ACCEPT')
    match = rule.create_match('comment')
    match.comment = 'This is a test comment'
    chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), 'INPUT')
    chain.insert_rule(rule)


def test_insert_forward_rule():
    pass


def util_create_chain_by_name(table, name):
    for chain in table.chains:
        # print(chain.name)
        if str(chain.name) == str(name):
            return False, chain
    chain = table.create_chain(name)
    print("INFO: Create " + name + " Chain in NAT Table...")
    return True, chain


def util_insert_rule_by_name(chain, target_rule):
    for rule in chain.rules:
        if str(rule.target.name) == str(target_rule.target.name):
            return False
    chain.insert_rule(target_rule)
    print("INFO: Insert " + target_rule.target.name + " Rule in " + chain.name + " Chain...")
    return True


def insert_single_forward_rule(clusterIP, podIps):
    """ Go into NAT table """
    table = iptc.Table(iptc.Table.NAT)

    # set `MINI-KUBE-SERVICES` rule in `OUTPUT` chain in `nat` table
    util_create_chain_by_name(table, "MINI-KUBE-SERVICES")

    rule = iptc.Rule()
    rule.src = "0.0.0.0/0"
    rule.dst = "0.0.0.0/0"
    rule.target = rule.create_target("MINI-KUBE-SERVICES")

    match = rule.create_match("comment")
    match.comment = "mini kubernetes service portals"

    chain = iptc.Chain(table, "OUTPUT")
    util_insert_rule_by_name(chain, rule)

    # set specific svc rule in MINI-KUBE-SERVICES chain
    suffix = utils.generate_random_str(12, 1)
    kubesvc_name = "MINI-KUBE-SVC-" + suffix
    util_create_chain_by_name(table, kubesvc_name)

    rule = iptc.Rule()
    rule.src = "0.0.0.0/0"
    rule.dst = clusterIP
    rule.protocol = 'tcp'
    rule.target = rule.create_target(kubesvc_name)

    match = rule.create_match("comment")
    match.comment = "mini kubernetes service: cluster IP"

    chain = iptc.Chain(table, "MINI-KUBE-SERVICES")
    chain.insert_rule(rule)

    # set one or more sep rule in KUBE-SVC- chain
    suffix = utils.generate_random_str(12, 1)
    kubesep_name = "MINI-KUBE-SEP-" + suffix
    util_create_chain_by_name(table, kubesep_name)

    rule = iptc.Rule()
    rule.src = "0.0.0.0/0"
    rule.dst = "0.0.0.0/0"
    rule.target = rule.create_target(kubesep_name)

    # match = rule.create_match("statistic mode random probability")
    # match.possibility = "0.3333333349"

    match = rule.create_match("comment")
    match.comment = "default mini kubernetes service"

    chain = iptc.Chain(table, kubesvc_name)
    chain.insert_rule(rule)

    # set DNAT rule in KUBE-SEP- chain
    util_create_chain_by_name(table, "DNAT")

    rule = iptc.Rule()
    rule.src = '0.0.0.0'
    rule.dst = podIps
    rule.target = rule.create_target("DNAT")

    match = rule.create_match("comment")
    match.comment = "mini kubernetes bind clusterIP to podIP"

    chain = iptc.Chain(table, kubesep_name)
    chain.insert_rule(rule)

    # set KUBE-MARK-MASQ rule in KUBE-SEP- chain
    util_create_chain_by_name(table, "MINI-KUBE-MARK-MASQ")

    rule = iptc.Rule()
    rule.src = podIps
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("MINI-KUBE-MARK-MASQ")

    match = rule.create_match("comment")
    match.comment = "mini kubernetes pod visit itself"

    chain = iptc.Chain(table, kubesep_name)
    chain.insert_rule(rule)

    """ Go into FILTER table """
    table = iptc.Table(iptc.Table.FILTER)

    # set KUBE-SERVICES rule in OUTPUT chain in FILTER table
    util_create_chain_by_name(table, "MINI-KUBE-SERVICES")

    rule = iptc.Rule()
    rule.src = '0.0.0.0/0'
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("MINI-KUBE-SERVICES")

    match = rule.create_match("comment")
    match.comment = "mini kubernetes service portals"

    chain = iptc.Chain(table, "OUTPUT")
    util_insert_rule_by_name(chain, rule)

    # set KUBE-FIREWALL rule in OUTPUT
    util_create_chain_by_name(table, "MINI-KUBE-FIREWALL")

    rule = iptc.Rule()
    rule.src = '0.0.0.0/0'
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("MINI-KUBE-FIREWALL")

    chain = iptc.Chain(table, "OUTPUT")
    util_insert_rule_by_name(chain, rule)

    # set DROP rule in KUBE-FIREWALL
    rule = iptc.Rule()
    rule.src = '0.0.0.0/0'
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("DROP")

    match = rule.create_match("mark")
    match.mark = "0x8000"

    match = rule.create_match("comment")
    match.comment = "mini kubernetes firewall for dropping marked packets"

    chain = iptc.Chain(table, "MINI-KUBE-FIREWALL")
    util_insert_rule_by_name(chain, rule)

    # set KUBE-POSTROUTING rule in POSTROUTING chain in nat table


def set_iptables(cluster_ip, pod_ip_list):
    # reference to: https://www.cnblogs.com/charlieroro/p/9588019.html
    """ set kube-proxy iptables, mainly for pod visit service using ClusterIP """
    utils.create_chain("nat", "KUBE-SERVICES")
    utils.insert_rule("nat", "OUTPUT", 1,
                      utils.make_rulespec(comment="minik8s service portals",
                                          jump="KUBE-SERVICES"),
                      utils.make_target_extensions())
    kubesvc = "KUBE-SVC-" + utils.generate_random_str(12, 1)
    utils.create_chain("nat", kubesvc)
    utils.insert_rule("nat", "KUBE-SERVICES", 1,
                      utils.make_rulespec(protocol='tcp', dport=80,
                                          destination=cluster_ip,
                                          comment="default/nginx-service: cluster IP",
                                          jump=kubesvc),
                      utils.make_target_extensions())
    # KUBE-SEP- chain might be several for load balancing
    kubesep = "KUBE-SEP-" + utils.generate_random_str(12, 1)
    utils.create_chain("nat", kubesep)
    utils.insert_rule("nat", kubesvc, 1,
                      utils.make_rulespec(jump=kubesep,
                                          comment="default/nginx-service"),
                      utils.make_target_extensions(match="statistic",
                                                   mode="random",
                                                   probability=1.0))
    utils.create_chain("nat", "KUBE-MARK-MASQ")
    utils.insert_rule("nat", kubesep, 1,
                      utils.make_rulespec(source=pod_ip_list,
                                          comment="default/nginx-service",
                                          jump="KUBE-MARK-MASQ"),
                      utils.make_target_extensions())
    utils.insert_rule("nat", kubesep, 2,
                      utils.make_rulespec(jump="DNAT",
                                          protocol="tcp",
                                          comment="default/nginx-service"),
                      utils.make_target_extensions(to_destination=pod_ip_list + ":80"))

    utils.create_chain("filter", "KUBE-SERVICES")
    utils.insert_rule("filter", "OUTPUT", 1,
                      utils.make_rulespec(jump="KUBE-SERVICES",
                                          comment="minik8s service portals"),
                      utils.make_target_extensions(ctstate="NEW"))

    utils.create_chain("filter", "KUBE-FIREWALL")
    utils.insert_rule("filter", "OUTPUT", 2,
                      utils.make_rulespec(jump="KUBE-FIREWALL"),
                      utils.make_target_extensions())
    utils.insert_rule("filter", "KUBE-FIREWALL", 1,
                      utils.make_rulespec(jump="DROP",
                                          comment="minik8s firewall for dropping marked packets"),
                      utils.make_target_extensions(mark="0x8000"))

    utils.create_chain("nat", "KUBE-POSTROUTING")
    utils.insert_rule("nat", "POSTROUTING", 1,
                      utils.make_rulespec(jump="KUBE-POSTROUTING",
                                          comment="minik8s postrouting rules"),
                      utils.make_target_extensions())
    utils.delete_rule("nat", "POSTROUTING",
                      utils.make_rulespec(jump="MASQUERADE"),
                      utils.make_target_extensions())
    utils.insert_rule("nat", "POSTROUTING", 2,
                      utils.make_rulespec(jump="MASQUERADE",
                                          out_interface="!docker0",
                                          source="192.168.1.0/24"),
                      utils.make_target_extensions())

    utils.insert_rule("nat", "KUBE-POSTROUTING", 1,
                      utils.make_rulespec(jump="MASQUERADE",
                                          comment="minik8s service traffic requiring SNAT"),
                      utils.make_target_extensions(mark="0x4000"))


def init_iptables():
    # reference to: https://www.bookstack.cn/read/source-code-reading-notes/kubernetes-kube_proxy_iptables.md
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


def set_iptables_clusterIP(cluster_ip, service_name, dport, ip_prefix_len, pod_ip_list):
    # reference to: https://www.bookstack.cn/read/source-code-reading-notes/kubernetes-kube_proxy_iptables.md
    kubesvc = 'KUBE-SVC-' + utils.generate_random_str(12, 1)
    utils.create_chain('nat', kubesvc)
    utils.insert_rule('nat', 'KUBE-SERVICES', 1,
                      utils.make_rulespec(
                          jump=kubesvc,
                          destination='/'.join([cluster_ip, str(ip_prefix_len)]),
                          protocol='tcp',
                          comment=service_name + ': cluster IP',
                          dport=dport
                      ),
                      utils.make_target_extensions())

    pod_num = len(pod_ip_list)
    for i in range(0, pod_num):
        kubesep = 'KUBE-SEP-' + utils.generate_random_str(12, 1)
        utils.create_chain('nat', kubesep)
        prob = 1 / (pod_num - i)
        if i == 1:
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
                              to_destination=':'.join([pod_ip_list[i], str(dport)])
                          ))


if __name__ == '__main__':
    # test_insert_rule()
    # print_all_filter_table()
    # insert_single_forward_rule('100.100.100.100', '192.168.1.2')
    init_iptables()
    set_iptables_clusterIP(cluster_ip='10.0.0.0',
                           service_name='nginx-service',
                           dport=80,
                           ip_prefix_len=32,
                           pod_ip_list=['172.17.0.2', '172.17.0.3'])
