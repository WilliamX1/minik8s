import random
import subprocess


def generate_random_str(randomlength=16, opts=0):
    """
    :param randomlength: the length of return string value
    :param opts: 0 for char + num, 1 for char only, 2 for num only
    :return: a random string with fixed length
    """
    random_str = ''
    base_str_upper_char = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    base_str_lower_char = 'abcdefghijklmnopqrstuvwxyz'
    base_str_num = '0123456789'
    base_str = ''
    if opts == 0:
        base_str = base_str_upper_char + base_str_lower_char + base_str_num
    elif opts == 1:
        base_str = base_str_upper_char + base_str_lower_char
    elif opts == 2:
        base_str = base_str_num
    else:
        print("Warn: in function generate_random_str() parameter opts should be 0/1/2...")
    base_length = len(base_str) - 1
    for i in range(randomlength):
        random_str += base_str[random.randint(0, base_length)]
    return random_str


def exec_command(command):
    print("> " + ' '.join(command))
    p = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, err = p.communicate()
    if str(output, 'utf-8') != "":
        print("output: " + str(output))
    if err is not None:
        print("err: " + str(err))


def append_rule(table, chain, rulespec, target_extension):
    """ sudo iptables -t <table> -I <chain> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-I", chain] + rulespec + target_extension
    exec_command(command)


def delete_rule(table, chain, rulespec, target_extension):
    """ sudo iptables -t <table> -D <chain> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-D", chain] + rulespec + target_extension
    exec_command(command)


def insert_rule(table, chain, rulenum, rulespec, target_extension):
    """ sudo iptables -t <table> -I <chain> <rulenum> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-I", chain, str(rulenum)] + rulespec + target_extension
    exec_command(command)


def append_rule(table, chain, rulespec, target_extension):
    """ sudo iptables -t <table> -A <chain> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-A", chain] + rulespec + target_extension
    exec_command(command)


def replace_rule(table, chain, rulenum, rulespec, target_extension):
    """sudo iptables -t <table> -R <chain> <rulenum> <rule-specification>"""
    command = ["sudo", "iptables", "-t", table, "-R", chain, rulenum] + rulespec + target_extension
    exec_command(command)


def list_chain(table, chain=""):
    """sudo iptables -t <table> -n -L <chain>"""
    command = ["sudo", "iptables", "-t", table, "-L", chain]
    exec_command(command)


def flush_chain(table, chain=""):
    command = ["sudo", "iptables", "-t", table, "-F", chain]
    exec_command(command)


def create_chain(table, chain):
    """ sudo iptables -t <table> -N <chain> """
    command = ["sudo", "iptables", "-t", table, "-N", chain]
    exec_command(command)


def delete_chain(table, chain):
    """ sudo iptables -t <table> -X <chain> """
    command = ["sudo", "iptables", "-t", table, "-X", chain]
    exec_command(command)


def policy_chain(table, chain, target):
    """sudo iptables -t <table> -P <chain> <target>"""
    command = ["sudo", "iptables", "-t", table, "-P", chain] + target
    exec_command(command)


def rename_chain(table, old_chain, new_chain):
    """sudo iptables -t <table> -E <old-chain> <new-chain>"""
    command = ["sudo", "iptables", "-t", table, "-E", old_chain, new_chain]
    exec_command(command)


def get_help():
    """sudo iptables -h"""
    command = ["sudo", "iptables", "-h"]
    exec_command(command)


def make_rulespec(protocol=None, dport=None, sport=None,
                  source=None, destination=None, jump=None, goto=None,
                  in_interface=None, out_interface=None, fragment=None, set_counters=None, comment=None):
    """
    Make up a rule specification ( as used in the add, delete, insert, replace and append command )
    :param protocol: default: all, tcp/udp/icmp/all
    :param dport:
    :param sport:
    :param source: default: 0.0.0.0/0, a network name, a hostname, a network IP address or a plain IP address
    :param destination: default: 0.0.0.0/0, destination specification
    :param jump: a user-defined chain or one of the special builtin targets (ACCEPT, DROP...)
    :param goto: continue in a user specified chain
    :param in_interface: name of an interface via which a packet was received, INPUT/FORWARD/PREROUTING
    :param fragment:
    :param set_counters:
    :param comment:
    :return: A format rule-specification string like '-p tcp -s 10.0.0.0'
    """
    rulespec = []
    if protocol is not None:
        rulespec.append("-p")
        rulespec.append(protocol)
        if dport is not None:
            rulespec.append("--dport")
            rulespec.append(str(dport))
        if sport is not None:
            rulespec.append("--sport")
            rulespec.append(str(sport))
    if source is not None:
        rulespec.append("-s")
        rulespec.append(source)
    if destination is not None:
        rulespec.append("-d")
        rulespec.append(destination)
    if jump is not None:
        rulespec.append("-j")
        rulespec.append(jump)
    if goto is not None:
        rulespec.append("-g")
        rulespec.append(goto)
    if in_interface is not None:
        rulespec.append("-i")
        rulespec.append(in_interface)
    if out_interface is not None:
        rulespec.append("-o")
        rulespec.append(out_interface)
    if fragment is not None:
        rulespec.append("-f")
        rulespec.append(fragment)
    if set_counters is not None:
        rulespec.append("-c")
        rulespec.append(set_counters)
    if comment is not None:
        rulespec.append("-m")
        rulespec.append("comment")
        rulespec.append("--comment")
        rulespec.append(comment)
    return rulespec


def make_target_extensions(to_destination=None, mark=None, match=None, mode=None,
                           probability=None, ctstate=None, ormark=None, addrtype=None,
                           dst_type=None, statistic=None):
    """
    Make target extensions limit to --to-destination ans --set-mark
    :param to_destination: This allows you to DNAT connections in a round robin way
                            over a given range of destination address
    :param mark: Set connection mark
    :param mode: policy mode, random
    :param possibility:
    :return: a format target extension string like '--to-destination 192.168.1.1:80 --set-mark 0x8888'
    """
    target = []
    if to_destination is not None:
        target.append("--to-destination")
        target.append(to_destination)
    if mark is not None:
        target.append("-m")
        target.append("mark")
        target.append("--mark")
        target.append(mark)
    if match is not None:
        target.append("-m")
        target.append(match)
    if statistic is not None:
        target.append('-m')
        target.append('statistic')
    if mode is not None:
        target.append("--mode")
        target.append(mode)
        if probability is not None:
            target.append("--probability")
            target.append(str(probability))
    if ctstate is not None:
        target.append("-m")
        target.append("conntrack")
        target.append("--ctstate")
        target.append(ctstate)
    if ormark is not None:
        target.append("--or-mark")
        target.append(ormark)
    if addrtype is not None:
        target.append("-m")
        target.append("addrtype")
        if dst_type is not None:
            target.append("--dst-type")
            target.append(dst_type)

    return target

