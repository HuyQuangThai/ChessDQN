import numpy as np
import pickle

class QTable(dict):
    def __init__(self, default):
        dict.__init__(self)
        self.default = default
        self.nCounts = {}
        
    def __getitem__(self, key):
        if super().__contains__(key):
            v = super().__getitem__(key)
            return v / self.nCounts[key]
        return self.default
    
    def __setitem__(self, key, value):
        if super().__contains__(key):
            old_value = super().__getitem__(key)
        else:
            old_value = 0
            self.nCounts[key] = 0
        
        super().__setitem__(key, old_value + value)
        self.nCounts[key] += 1
        
    def __getstate__(self):
        return {
            'data': dict(self),
            'nCounts': self.nCounts,
            'default': self.default
        }
        
    def __setstate__(self, state):
        super().update(self, state['data'])
        self.nCounts = state['nCounts']
        self.default = state['default']
        
    def save(self, path="qtable.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"Saved {len(self)} states")

    @classmethod
    def load(cls, path="qtable.pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)