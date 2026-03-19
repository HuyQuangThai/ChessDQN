import numpy as np

class EncodeBoard:
    """
    119-channel AlphaZero encoding.

    Channels 0..111  : 8 timesteps × 14 planes
      t*14 + 0..5  : White pieces (P,N,B,R,Q,K)
      t*14 + 6..11 : Black pieces (P,N,B,R,Q,K)
      t*14 + 12    : repetition >= 1
      t*14 + 13    : repetition >= 2
    Channels 112..118: metadata
      [112] colour (1 = Black to move)
      [113] total move count (raw)
      [114] P1 kingside castling
      [115] P1 queenside castling
      [116] P2 kingside castling
      [117] P2 queenside castling
      [118] half-move clock / 100
    """

    HISTORY_LENGTH = 8
    PLANES_PER_STEP = 14
    PIECE_MAP = {"p": 0, "N": 1, "B": 2, "R": 3, "Q": 4, "K": 5}

    def encode_board_full(self, game_state, history_length: int = 8) -> np.ndarray:
        state = np.zeros((119, 8, 8), dtype=np.float32)
        flip  = not game_state.white_to_move

        # ── Piece + Repetition planes (ch 0..111) ───────────────────
        hist = list(getattr(game_state, 'history', [game_state.board]))
        while len(hist) < history_length:
            hist.insert(0, [["--"] * 8 for _ in range(8)])
        hist = hist[-history_length:]

        position_counts = getattr(game_state, 'position_counts', {})

        for t, board_snap in enumerate(hist):
            base = t * self.PLANES_PER_STEP
            for r in range(8):
                for c in range(8):
                    piece = board_snap[r][c]
                    if piece == "--":
                        continue
                    p_color, p_type = piece[0], piece[1]
                    is_own = (p_color == 'b') if flip else (p_color == 'w')
                    ch = self.PIECE_MAP[p_type] + (0 if is_own else 6)
                    fr, fc = (7 - r, 7 - c) if flip else (r, c)
                    state[base + ch, fr, fc] = 1.0

            # Repetition planes
            snap_key = str(board_snap)
            rep = position_counts.get(snap_key, 0)
            if rep >= 1:
                state[base + 12] = 1.0
            if rep >= 2:
                state[base + 13] = 1.0

        # ── Metadata (ch 112..118) ───────────────────────────────────
        meta = 112
        rights = game_state.current_castling_rights

        if flip:
            my_ks, my_qs   = rights.bks, rights.bqs
            opp_ks, opp_qs = rights.wks, rights.wqs
        else:
            my_ks, my_qs   = rights.wks, rights.wqs
            opp_ks, opp_qs = rights.bks, rights.bqs

        if flip:
            state[meta + 0] = 1.0                               # colour
        state[meta + 1] = getattr(game_state, 'move_count', 0)  # total moves
        if my_ks:  state[meta + 2] = 1.0                        # P1 K-side
        if my_qs:  state[meta + 3] = 1.0                        # P1 Q-side
        if opp_ks: state[meta + 4] = 1.0                        # P2 K-side
        if opp_qs: state[meta + 5] = 1.0                        # P2 Q-side
        state[meta + 6] = min(getattr(game_state, 'half_move_clock', 0), 100) / 100.0

        return state

