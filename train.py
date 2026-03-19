import os
import random
from typing import Dict, List

import numpy as np
import torch
import torch.nn.functional as F
from torch.optim import AdamW

from DQN.DQN import DQN
from DQN.RelayBuffer import ReplayBuffer
from Env.ChessEnv import ChessEnv
from Env.TrainConfig import TrainConfig


def build_legal_mask(env: ChessEnv, num_actions: int) -> np.ndarray:
    """Build legal action mask in the same action space used by the policy network."""
    mask = np.zeros(num_actions, dtype=np.bool_)
    valid_moves = env.state.getValidMoves()

    for mv in valid_moves:
        uci = mv.get_uci()
        # Env.step flips actions when black to move, so we flip here for mask consistency.
        if not env.state.white_to_move:
            uci = env._flip_uci(uci)

        action_id = env.mapper.encode(uci)
        if action_id is not None:
            mask[action_id] = True

    return mask


def select_action(
    policy_net: DQN,
    state: np.ndarray,
    legal_mask: np.ndarray,
    epsilon: float,
    device: torch.device,
) -> int:
    legal_actions = np.flatnonzero(legal_mask)
    if len(legal_actions) == 0:
        # Fallback to a random action if mask is unexpectedly empty.
        return random.randint(0, legal_mask.shape[0] - 1)

    if random.random() < epsilon:
        return int(random.choice(legal_actions))

    with torch.no_grad():
        state_t = torch.from_numpy(state).unsqueeze(0).to(device)
        legal_t = torch.from_numpy(legal_mask).unsqueeze(0).to(device)
        q_values = policy_net(state_t, legal_t)
        return int(torch.argmax(q_values, dim=1).item())


def optimize_step(
    policy_net: DQN,
    target_net: DQN,
    optimizer: AdamW,
    replay_buffer: ReplayBuffer,
    cfg: TrainConfig,
    device: torch.device,
) -> float:
    (
        states,
        actions,
        rewards,
        next_states,
        dones,
        legal_masks,
        next_legal_masks,
    ) = replay_buffer.sample(cfg.batch_size)

    states_t = torch.from_numpy(states).to(device)
    actions_t = torch.from_numpy(actions).to(device)
    rewards_t = torch.from_numpy(rewards).to(device)
    next_states_t = torch.from_numpy(next_states).to(device)
    dones_t = torch.from_numpy(dones).to(device)
    legal_masks_t = torch.from_numpy(legal_masks).to(device)
    next_legal_masks_t = torch.from_numpy(next_legal_masks).to(device)

    q_all = policy_net(states_t, legal_masks_t)
    q_sa = q_all.gather(1, actions_t.unsqueeze(1)).squeeze(1)

    with torch.no_grad():
        next_q_all = target_net(next_states_t, next_legal_masks_t)
        next_q_max = torch.max(next_q_all, dim=1).values
        target = rewards_t + cfg.gamma * (1.0 - dones_t) * next_q_max

    loss = F.smooth_l1_loss(q_sa, target)

    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(policy_net.parameters(), max_norm=1.0)
    optimizer.step()

    return float(loss.item())


def train_dqn(cfg: TrainConfig) -> Dict[str, List[float]]:
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)

    device = torch.device(cfg.device)
    env = ChessEnv(cfg.stockfish_path)

    policy_net = DQN(
        in_channels=cfg.in_channels,
        num_filters=cfg.num_filters,
        num_blocks=cfg.num_blocks,
        num_actions=cfg.num_actions,
    ).to(device)

    target_net = DQN(
        in_channels=cfg.in_channels,
        num_filters=cfg.num_filters,
        num_blocks=cfg.num_blocks,
        num_actions=cfg.num_actions,
    ).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = AdamW(policy_net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    replay_buffer = ReplayBuffer(cfg.buffer_size)

    global_step = 0
    rewards_history: List[float] = []
    loss_history: List[float] = []

    try:
        for ep in range(1, cfg.num_episodes + 1):
            state = env.reset()
            legal_mask = build_legal_mask(env, cfg.num_actions)
            ep_reward = 0.0

            for _ in range(cfg.max_steps_per_episode):
                epsilon = cfg.eps_end + (cfg.eps_start - cfg.eps_end) * np.exp(
                    -global_step / max(1.0, cfg.eps_decay)
                )

                action = select_action(policy_net, state, legal_mask, float(epsilon), device)
                _, agent_reward, done = env.step(action)

                reward = agent_reward
                depth = 1 if ep < 1_000 else 3 if ep < 10_000 else cfg.stockfish_depth
                if not done:
                    next_state, stockfish_reward, done = env.stockfish_step(
                        depth=depth,
                        random_move_prob=cfg.stockfish_random_move_prob,
                    )
                    # Opponent gain should reduce agent reward signal.
                    reward -= stockfish_reward
                else:
                    next_state = env.getState()

                next_legal_mask = (
                    build_legal_mask(env, cfg.num_actions)
                    if not done
                    else np.ones(cfg.num_actions, dtype=np.bool_)
                )

                replay_buffer.push(
                    state=state,
                    action=action,
                    reward=reward,
                    next_state=next_state,
                    done=done,
                    legal_mask=legal_mask,
                    next_legal_mask=next_legal_mask,
                )

                state = next_state
                legal_mask = next_legal_mask
                ep_reward += reward
                global_step += 1

                if len(replay_buffer) >= cfg.min_buffer_size:
                    loss = optimize_step(policy_net, target_net, optimizer, replay_buffer, cfg, device)
                    loss_history.append(loss)

                if global_step % cfg.target_update_freq == 0:
                    target_net.load_state_dict(policy_net.state_dict())

                if done:
                    break

            rewards_history.append(ep_reward)

            if ep % cfg.log_every == 0:
                avg_reward = float(np.mean(rewards_history[-cfg.log_every:]))
                avg_loss = float(np.mean(loss_history[-cfg.log_every:])) if len(loss_history) >= cfg.log_every else 0.0
                print(
                    f"[Episode {ep}] avg_reward={avg_reward:.4f} avg_loss={avg_loss:.4f} "
                    f"buffer={len(replay_buffer)} steps={global_step}"
                )

            if ep % cfg.save_every == 0:
                ckpt_path = os.path.join(cfg.checkpoint_dir, f"dqn_ep_{ep}.pt")
                torch.save(
                    {
                        "episode": ep,
                        "global_step": global_step,
                        "policy_state_dict": policy_net.state_dict(),
                        "target_state_dict": target_net.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "rewards_history": rewards_history,
                        "loss_history": loss_history,
                    },
                    ckpt_path,
                )
    finally:
        env.close()

    return {"rewards": rewards_history, "losses": loss_history}


if __name__ == "__main__":
    config = TrainConfig()
    train_dqn(config)
