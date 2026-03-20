import os
import random
import math
import time
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.optim as optim
import chess
import chess.engine

@dataclass
class TrainConfig:
    stockfish_path = "/usr/game/stockfish"
    stockfish_depth = 5
    stockfish_random_move_prob = 0.15
    
    buffer_size = 100_000
    batch_size = 256
    min_buffer_size = 2_000
    
    num_episodes = 50_000
    max_steps_per_episode = 200
    gamma = 0.99
    
    target_update_freq = 1_000
    
    eps_start = 1.0
    eps_end = 0.05
    eps_decay = 50_000
    
    lr = 1e-4
    weight_decay = 1e-4
    
    lr_step_size = 10_000
    lr_gamma = 0.5
    lr_min = 1e-6
    
    checkpoint_dir = "./checkpoints"
    save_every = 500
    resume_from = None
    
    log_every = 50
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    in_channels = 119
    num_filters = 144
    num_blocks = 10
    num_actions = 4672
    
    