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
                  rule.dst, "in:", rule.in_interface, "out:", rule.out_interface,)
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
    chain.insert_rule(rule)

    # set KUBE-FIREWALL rule in OUTPUT
    util_create_chain_by_name(table, "MINI-KUBE-FIREWALL")

    rule = iptc.Rule()
    rule.src = '0.0.0.0/0'
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("MINI-KUBE-FIREWALL")

    chain = iptc.Chain(table, "OUTPUT")
    chain.insert_rule(rule)

    # set DROP rule in KUBE-FIREWALL
    util_create_chain_by_name(table, "DROP")

    rule = iptc.Rule()
    rule.src = '0.0.0.0/0'
    rule.dst = '0.0.0.0/0'
    rule.target = rule.create_target("DROP")

    match = rule.create_match("mark")
    match.mark = "0x8000"

    match = rule.create_match("comment")
    match.comment = "mini kubernetes firewall for dropping marked packets"

    chain = iptc.Chain(table, "MINI-KUBE-FIREWALL")
    chain.insert_rule(rule)

    # set KUBE-POSTROUTING rule in POSTROUTING chain in nat table





def clear_nat_table():
    pass


if __name__ == '__main__':
    '''
    p = subprocess.Popen(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "-m", "tcp", "--dport", "22", "-j", "ACCEPT"],
                         stdout=subprocess.PIPE)
    output, err = p.communicate()
    print(output, err)
    '''
    # test_insert_rule()
    # print_all_filter_table()
    insert_single_forward_rule('100.100.100.100', '192.168.1.2')
