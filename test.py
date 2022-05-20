import etcd3

etcd = etcd3.client()
for kvs in etcd.get_all_response().kvs:
    etcd.delete(kvs.key)

#
# import random
# import string
# import six
# import sys
# import entities
# import yaml_loader
#
# def create_suffix():
#     res = ''.join(random.choices(string.ascii_letters +
#                                  string.digits, k=10))
#     res = '-' + res
#     return res
#
#
# def _parse_bytes(s):
#     if not s or not isinstance(s, six.string_types):
#         return s
#     units = {'k': 1024,
#              'm': 1024 * 1024,
#              'g': 1024 * 1024 * 1024}
#     suffix = s[-1].lower()
#     if suffix not in units.keys():
#         if not s.isdigit():
#             sys.stdout.write('Unknown unit suffix {} in {}!'
#                              .format(suffix, s))
#             return 0
#         return int(s)
#     return int(s[:-1]) * units[suffix]
# config = yaml_loader.load('yaml_default/pod_default.yaml')
# config['containers'][0]['resource']['cpu'] = '0'
# config['containers'][1]['resource']['cpu'] = '1,2'
# config['suffix'] = create_suffix()
# pod = entities.Pod(config,False)
# print(pod.resource_status())
