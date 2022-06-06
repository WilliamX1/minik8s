import jinja2
import os
import yaml
import _yaml
from yaml.constructor import ConstructorError, SafeConstructor


class MaestroYamlConstructor(SafeConstructor):

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.nodes.MappingNode):
            raise ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        keys = set([])
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "found duplicate key (%s)" % key, key_node.start_mark)
            keys.add(key)
        return SafeConstructor.construct_mapping(self, node, deep)


class MaestroYamlLoader(_yaml.CParser, MaestroYamlConstructor,
                        yaml.resolver.Resolver):
    def __init__(self, stream):
        _yaml.CParser.__init__(self, stream)
        MaestroYamlConstructor.__init__(self)
        yaml.resolver.Resolver.__init__(self)


def load(filename):
    # 加载文件并返回yaml结构体
    base_dir = os.path.dirname(filename) if filename != '-' else os.getcwd()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(base_dir),
        auto_reload=False, )

    template = env.get_template(os.path.basename(filename))
    config = yaml.load(template.render(env=os.environ),
                       Loader=MaestroYamlLoader)
    return config
