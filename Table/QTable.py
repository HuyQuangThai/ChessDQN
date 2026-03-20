import numpy as np

class QTable(dict):
    def __init__(self, default):
        dict.__init__(self)
        self.default = default
        self.nCounts = {}
        
    def __getitem__(self, key):
        if super.__contains__(key):
            v = super.__getitem__(key)
            return v / self.nCounts[key]
        return self.default
    
    def __setitem__(self, key, value):
        if super.__contains__(key):
            old_value = super.__getitem__(key)
        else:
            old_value = 0
            self.nCounts[key] = 0
        
        super.__setitem__(key, old_value + value)
        self.nCounts[key] += 1