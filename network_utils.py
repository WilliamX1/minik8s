import os
import random
import iptc
import subprocess


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


def insert_rule():
    rule = iptc.Rule()
    rule.src = '127.0.0.1'
    rule.protocol = 'udp'
    rule.target = rule.create_target('ACCEPT')
    match = rule.create_match('comment')
    match.comment = 'This is a test comment'
    chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), 'INPUT')
    chain.insert_rule(rule)


if __name__ == '__main__':
    p = subprocess.Popen(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "-m", "tcp", "--dport", "22", "-j", "ACCEPT"],
                         stdout=subprocess.PIPE)
    output, err = p.communicate()
    print(output, err)
