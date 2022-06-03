import re
from typing import List


class ServerlessFunction(object):
    def __init__(self, index, name, node_type, module_name=None, function_name=None):
        self.index = index
        self.name = name
        self.node_type = node_type
        self.module_name = module_name
        self.function_name = function_name
        self.out_edge: List[Edge] = list()
        print(self.__str__())

    @staticmethod
    def from_dict(init_dict: dict, node_name):
        node_id = init_dict['id']
        node_type = init_dict['type']

        if node_type == 'input' or node_type == 'output':
            return ServerlessFunction(node_id, node_name, node_type)
        else:
            match_ = re.fullmatch(r'(\w*)\.(\w*)', node_name.strip(), re.I)
            if match_:
                module_name = match_.group(1)
                function_name = match_.group(2)
                print("module_name = {}".format(module_name))
                print("function_name = {}".format(function_name))
                return ServerlessFunction(node_id, node_name, node_type, module_name, function_name)
            else:
                print("match error")
                return None

    def add_out_edge(self, edge):
        self.out_edge.append(edge)

    def __str__(self):
        return {'index': self.index, 'name': self.name, 'node_type': self.node_type, 'module_name': self.module_name, 'function_name': self.function_name, 'out_edge': self.out_edge}.__str__()

class Edge(object):
    def __init__(self, index, source: ServerlessFunction, target: ServerlessFunction, condition="True"):
        self.index = index
        self.source: ServerlessFunction = source
        self.target: ServerlessFunction = target
        self.condition = condition

    @staticmethod
    def from_dict(init_dict: dict, nodes: dict):
        edge_id = init_dict['id']
        source_node_id = init_dict['source']
        target_node_id = init_dict['target']
        if nodes.__contains__(source_node_id) and nodes.__contains__(target_node_id):
            print("edge links ", nodes[source_node_id].module_name, nodes[target_node_id].module_name)
            return Edge(edge_id, nodes[source_node_id], nodes[target_node_id], "True")
        else:
            return None

    def update_condition(self, condition:str):
        self.condition = condition
        print("Edge {} condition updated! {}".format(self.index, self.condition))

    def __str__(self):
        return {'index': self.index, 'source': self.source, 'target': self.target, 'condition': self.condition}.__str__()

class DAG(object):
    def __init__(self, start_node: ServerlessFunction, end_node: ServerlessFunction, node_list: List[ServerlessFunction], edge_list: List[Edge]):
        self.start_node = start_node
        self.end_node = end_node
        self.node_list = node_list
        self.edge_list = edge_list

    @staticmethod
    def from_node_list_and_edge_list(node_list: List[ServerlessFunction], edge_list: List[Edge]):
        start_node = None
        end_node = None
        for node in node_list:
            if node.node_type == 'input':
                start_node = node
            if node.node_type == 'output':
                end_node = node
        if start_node and end_node:
            return DAG(start_node, end_node, node_list, edge_list)
        else:
            return None

    def node_size(self):
        return len(self.node_list)

    def edge_size(self):
        return len(self.edge_list)

    def __str__(self):
        return {'start_node': self.start_node, 'end_node': self.end_node, 'node_list': self.node_list, 'edge_list': self.edge_list}.__str__()