import random


def generate_random_str(randomlength=16, opts=0):
    '''
    :param randomlength: the length of return string value
    :param opts: 0 for char + num, 1 for char only, 2 for num only
    :return: a random string with fixed length
    '''
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

