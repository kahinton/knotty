"""
This module should hold the registries responsible for managing different metric groups
"""
from exporters import Exporter


class SubRegistry:
    def __init__(self, name: str):
        self.name = name


class MasterRegistry:
    sub_registries = dict()
    exporters = dict()
    push_interval: int = None
    
    def __init__(self):
        pass
    
    @classmethod
    def add_subregistry(cls, sub_registry: SubRegistry):
        cls.sub_registries[sub_registry.name] = sub_registry
        
    @classmethod
    def add_eporter(cls, exporter: Exporter):
        cls.exporters[exporter.name] = exporter
        
    @classmethod
    def set_push_interval(cls, interval: int):
        cls.push_interval = interval