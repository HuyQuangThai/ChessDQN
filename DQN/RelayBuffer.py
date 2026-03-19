from dataclasses import dataclass
import torch
import numpy as np
import random
from collections import deque


@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    legal_mask: np.ndarray
    next_legal_mask: np.ndarray

class ReplayBuffer:
    def __init__ (self, capacity):
        self.buffer = deque(maxlen=capacity)
        
    def push(self, state, action, reward, next_state, done, legal_mask, next_legal_mask):
        self.buffer.append(
            Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                legal_mask=legal_mask,
                next_legal_mask=next_legal_mask,
            )
        )
        
    def sample(self, batch_size):
        if len(self.buffer) < batch_size:
            raise ValueError("Not enough samples in buffer to sample a batch.")
        
        batch = random.sample(self.buffer, batch_size)
        states = np.stack([t.state for t in batch])
        actions = np.array([t.action for t in batch], dtype=np.int64)
        rewards = np.array([t.reward for t in batch], dtype=np.float32)
        next_states = np.stack([t.next_state for t in batch])
        dones = np.array([t.done for t in batch], dtype=np.float32)
        legal_masks = np.stack([t.legal_mask for t in batch]).astype(np.bool_)
        next_legal_masks = np.stack([t.next_legal_mask for t in batch]).astype(np.bool_)

        return states, actions, rewards, next_states, dones, legal_masks, next_legal_masks
    
    def __len__(self):
        return len(self.buffer)