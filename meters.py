"""
This module is responsible for holding the base definitions of the different types of metric meters.
"""
from logging import getLogger


class Timer:
    def __init__(self):
        pass


class Counter:
    def __init__(self, name: str):
        self.name = name
        self.count = 0
        
    def increment(self, amount: int = 1) -> None:
        self.count += amount
        
    def value(self) -> int:
        return self.count


class Gauge:
    def __init__(self, name: str, value_function: callable()):
        self.name = name
        self.value_function = value_function
        self.logger = getLogger(self.name)
    
    def value(self):
        try:
            return int(self.value_function())
        except Exception as e:
            self.logger.error(e)
            
    
class Summary:
    def __init__(self):
        pass
