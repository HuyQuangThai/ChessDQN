import numpy as np
from .QTable import QTable
from Env.ChessEnv import ChessEnv
from Env.TrainConfig import TrainConfig

class MCControl:
    def __init__(self, env, epsilon, defaultQ):
        self.env = env
        self.epsilon = epsilon
        self.table = QTable(defaultQ)
        self.cfg = TrainConfig()
        
    def firstVisit(self, steps):
        v = {}
        for s, a in set([(x[0], x[1]) for x in steps]):
            v[s, a] = []
            founded = False
            scores = 0
            
            for curS, curA, score in steps:
                if (curS, curA) == (s, a): founded = True
                if not founded: continue
                scores += score
            v[s, a].append(scores)
        
        return v
    
    def play(self, n=1):
        win = 0
        loss = 0
        draw = 0
        depth = 1

        def update_result_counts():
            nonlocal win, loss, draw
            if self.env.state.checkmate:
                if self.env.state.white_to_move:
                    loss += 1
                else:
                    win += 1
            else:
                draw += 1

        for _ in range(n):
            steps = []
            self.env.reset()
            
            done = False
            
            while not done:
                state = self.env.state.get_state_id()
                action = self.policy()
                action_str = action.get_uci()
                action_idx = self.env.mapper.encode(action_str)
                _, agent_reward, done = self.env.step(action_idx)
                
                score = agent_reward
                steps.append((state, action_str, score))
                
                if done:
                    update_result_counts()
                    break
                
                _, _, done = self.env.stockfish_step(
                    depth= depth,
                    random_move_prob=self.cfg.stockfish_random_move_prob,
                )

                if done:
                    update_result_counts()
                    break
                
            if done:
                self.improve(steps)
            
            total = win + loss + draw
            win_rate = win / total if total > 0 else 0
            
            if win_rate >= 0.35:
                depth = 1
            elif win_rate >= 0.45:
                depth = 2
            elif win_rate >= 0.55:
                depth = 3
            
            if total % 100 == 0 and total > 0:
                print(f"Episode {total} | Win rate: {win/total:.2%}")
                print(f"Win: {win}, Loss: {loss}, Draw: {draw}")
    
    def policy(self):
        s = self.env.state.get_state_id()
        qs = []
        actions = self.env.state.getValidMoves()
        for a in actions:
            a_str = a.get_uci()
            qs.append((a_str, self.table[s, a_str]))
        if len(qs) == 1:
            return actions[0]
        
        t = [x[1] for x in qs]
        indices = np.argwhere(t == np.max(t)).flatten()
        
        if len(indices) == len(qs):
            p = [1 / len(indices)] * len(indices)
        else:
            p = [(1 - self.epsilon) / len(indices) if i in indices else self.epsilon / (len(qs) - len(indices)) for i in range(len(qs))]
        return np.random.choice(actions, p=p)
    
    def improve(self, steps):
        v = self.firstVisit(steps)
        for s, a in v:
            for i in range(len(v[s, a])):
                self.table[s, a] = v[s, a][i]
                