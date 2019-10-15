"""
This module should hold the top level components of pycrometer that are responsible for auto-registering metrics, as
well as for providing the high level APIs that devs will interact with
"""


class Pycrometer:
    auto_register_dict = dict()

    def __init__(self):
        pass

    @classmethod
    def initiate_monitors(cls) -> None:
        auto_register_keys = cls.auto_register_dict.keys()
        for key, value in globals().items():
            type_key = str(type(value))
            if type_key in auto_register_keys:
                globals()[key] = cls.auto_register_dict[type_key](globals()[key])
