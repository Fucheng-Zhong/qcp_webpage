import yaml
import pathlib


class IncludeLoader(yaml.SafeLoader):
    """Yaml loader that can handle include statements

    This allows any yaml object to be put into a separate file.
    Syntax:

    .. code-block:: yaml

        extensions:
          - !include primary.yml
          - !include qxp-z.yml

    """

    def __init__(self, stream):
        self._root = pathlib.Path(stream.name).parent
        super(IncludeLoader, self).__init__(stream)

    def include(self, node):
        filepath = self._root / self.construct_scalar(node)
        with open(filepath, "r") as f:
            return yaml.load(f, IncludeLoader)


IncludeLoader.add_constructor("!include", IncludeLoader.include)
