import chess
import chess.engine
import math
import copy
import random
import numpy as np
from .GameState import GameState
from .ActionMapper import ActionMapper
from .EncodeBoard import EncodeBoard
from .Move import Move

class ChessEnv:
    def __init__(self, stockfish_path):
        self.state = GameState()
        self.mapper = ActionMapper()
        self.encoder = EncodeBoard()
        
        # Engine Stockfish để tính reward
        # self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.engine = None
        self._engine_call_count = 0
        
        # Lịch sử các state_id để phạt lặp nước
        self.state_history = []
        
    def reset(self):
        self.state = GameState()
        self.state_history.clear()
        return self.getState()
        
    def isTerm(self):
        _ = self.state.getValidMoves() 
        return self.state.checkmate or self.state.stalemate
        
    def getState(self):
        """Encode bàn cờ thành tensor 119-channels cho Neural Network"""
        # state tensor: [119, 8, 8]
        return self.encoder.encode_board_full(self.state)

    def _game_state_to_chess_board(self, game_state):
        """
        Hàm helper DỊCH từ GameState sang chess.Board CHỈ ĐỂ đút vào Stockfish.
        """
        board = chess.Board(None) # Bàn cờ trống
        piece_map = {
            'wp': chess.Piece(chess.PAWN, chess.WHITE),
            'wN': chess.Piece(chess.KNIGHT, chess.WHITE),
            'wB': chess.Piece(chess.BISHOP, chess.WHITE),
            'wR': chess.Piece(chess.ROOK, chess.WHITE),
            'wQ': chess.Piece(chess.QUEEN, chess.WHITE),
            'wK': chess.Piece(chess.KING, chess.WHITE),
            'bp': chess.Piece(chess.PAWN, chess.BLACK),
            'bN': chess.Piece(chess.KNIGHT, chess.BLACK),
            'bB': chess.Piece(chess.BISHOP, chess.BLACK),
            'bR': chess.Piece(chess.ROOK, chess.BLACK),
            'bQ': chess.Piece(chess.QUEEN, chess.BLACK),
            'bK': chess.Piece(chess.KING, chess.BLACK)
        }
        
        # Map vị trí quân
        for r in range(8):
            for c in range(8):
                piece_str = game_state.board[r][c]
                if piece_str != "--":
                    # chess.SQUARES: 0=a1, 63=h8. 
                    # GameState: r=0 là rank 8, r=7 là rank 1.
                    square = chess.square(c, 7 - r)
                    board.set_piece_at(square, piece_map[piece_str])
                    
        # Map lượt đi
        board.turn = chess.WHITE if game_state.white_to_move else chess.BLACK
        
        return board
    
    def _restart_engine(self):
        try:
            if hasattr(self, 'engine'):
                self.engine.quit()
        except Exception as e:
            pass
        self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        self._engine_call_count = 0

    def _get_stockfish_eval(self, game_state: GameState, depth: int = 5) -> int:
        """Lấy điểm Centipawn từ góc nhìn của Trắng"""
        py_board = self._game_state_to_chess_board(game_state)
        info = self.engine.analyse(py_board, chess.engine.Limit(depth=depth))
        score = info["score"].white()
        
        if score.is_mate():
            return 10000 if score.mate() > 0 else -10000
        return score.score()

    def reward(self, state_before: GameState, state_after: GameState, move: Move) -> float:
        # 1. Terminal State
        if state_after.checkmate:
            return 1.0
        if state_after.stalemate:
            return -0.05
            
        current_id = state_after.get_state_id()
        occurrence_penalty = self.state_history.count(current_id)
        if occurrence_penalty >= 2:
            return -0.3
        
        def material_score(state: GameState) -> int:
            piece_values = {'p': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}
            score = 0
            for r in state.board:
                for c in r:
                    piece_str = state.board[r][c]
                    if piece_str != "--":
                        value = piece_values[piece_str[1].lower()]
                        score += value if piece_str[0] == 'w' else -value
            return score if state_after.white_to_move else -score
        
        delta = material_score(state_after) - material_score(state_before)
        r_material = float(np.tanh(delta / 9.0)) * 0.1
        return r_material

    def _flip_uci(self, uci_str):
        """Lật tọa độ UCI nếu là Đen đi"""
        if len(uci_str) < 4: return uci_str
        file_map = {'a':'h', 'b':'g', 'c':'f', 'd':'e', 'e':'d', 'f':'c', 'g':'b', 'h':'a'}
        new_from = file_map[uci_str[0]] + str(9 - int(uci_str[1]))
        new_to = file_map[uci_str[2]] + str(9 - int(uci_str[3]))
        promo = uci_str[4:] if len(uci_str) > 4 else ""
        return new_from + new_to + promo

    def _apply_uci_move(self, move_uci_real):
        """Apply a real-board UCI move to GameState and return (state, reward, done)."""
        pos_dict = self.mapper.move_to_position(move_uci_real)
        if pos_dict is None:
            return self.getState(), -1.0, True

        move_obj = Move(pos_dict["from"], pos_dict["to"], self.state.board)
        promo = pos_dict['promotion']

        if move_obj.piece_moved[1] == 'K' and abs(move_obj.start_col - move_obj.end_col) == 2:
            move_obj.is_castle_move = True
        if move_obj.piece_moved[1] == 'p' and abs(move_obj.start_row - move_obj.end_row) == 1 and abs(move_obj.start_col - move_obj.end_col) == 1:
            move_obj.is_enpassant_move = True

        valid_moves = self.state.getValidMoves()
        valid_ucis = [m.get_uci() for m in valid_moves]
        move_uci_test = move_obj.get_uci()

        if move_uci_test not in valid_ucis:
            return self.getState(), -1.0, True

        actual_move_obj = None
        for vm in valid_moves:
            if vm.get_uci() == move_uci_test:
                actual_move_obj = vm
                break

        if actual_move_obj is None:
            return self.getState(), -1.0, True

        state_before = self.state.cloneState()
        self.state_history.append(self.state.get_state_id())

        if promo:
            self.state.makeMove(actual_move_obj, piecePromotion=promo)
        else:
            self.state.makeMove(actual_move_obj)

        done = self.isTerm()
        r = self.reward(state_before, self.state, actual_move_obj)
        return self.getState(), r, done

    def stockfish_step(self, depth=5, random_move_prob=0.0):
        self._engine_call_count += 1
        if self._engine_call_count > 1000:
            self._restart_engine()
        """Let Stockfish (or random fallback) play one legal move."""
        valid_moves = self.state.getValidMoves()
        if len(valid_moves) == 0:
            return self.getState(), 0.0, self.isTerm()

        if random.random() < random_move_prob:
            move_uci_real = random.choice(valid_moves).get_uci()
            return self._apply_uci_move(move_uci_real)

        py_board = self._game_state_to_chess_board(self.state)
        result = self.engine.play(py_board, chess.engine.Limit(depth=depth))

        if result.move is None:
            move_uci_real = random.choice(valid_moves).get_uci()
        else:
            move_uci_real = result.move.uci()

        return self._apply_uci_move(move_uci_real)

    def step(self, action_idx):
        """
        Thực thi 1 nước đi.
        Đầu vào: action_idx (int) từ AI
        """
        # 1. Decode lấy UCI
        move_uci_ai = self.mapper.decode(action_idx)
        if move_uci_ai is None:
            return self.getState(), -1.0, True
        
        # Lật bàn nếu là cờ đen (theo đúng logic Simulation)
        if not self.state.white_to_move:
            move_uci_real = self._flip_uci(move_uci_ai)
        else:
            move_uci_real = move_uci_ai

        return self._apply_uci_move(move_uci_real)
        
    def close(self):
        self.engine.quit()