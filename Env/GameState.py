class GameState:  #trạng thái và luật chơi cờ vua
    def __init__ (self):
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]]
        self.moveFunctions = {"p": self.getPawnMoves, 
                              "R": self.getRookMoves, 
                              "N": self.getKnightMoves, 
                              "B": self.getBishopMoves, 
                              "Q": self.getQueenMoves, 
                              "K": self.getKingMoves}
        
        self.white_to_move = True  # quân trắng đi trước
        self.move_log = []
        self.white_king_location = (7, 4) 
        self.black_king_location = (0, 4)   
        self.stalemate = False  # cờ hòa
        self.checkmate = False 
        self.in_check = False  # vua đang bị chiếu 
        self.pins = []   # danh sách quân bị ghim 
        self.checks = [] # danh sách quân chiếu vua
        self.enpassant_possible = ()  # lưu vị trí có thể bắt tốt qua đường
        self.enpassant_possible_log = [self.enpassant_possible]
        self.current_castling_rights = CastleRights(True, True, True, True)
        self.castle_rights_log = [CastleRights(self.current_castling_rights.wks, 
                                               self.current_castling_rights.bks,
                                               self.current_castling_rights.wqs, 
                                               self.current_castling_rights.bqs)]

        # -------------------------------------------------------
        # Luật hòa: 50 nước & lặp lại vị trí 3 lần
        # -------------------------------------------------------
        self.fifty_move_counter = 0          # đếm số nửa-nước (half-move) không ăn quân và không đi tốt
        self.fifty_move_counter_log = [0]    # nhật ký để undo
        self.threefold_repetition = False    # hòa do lặp 3 lần
        # lưu lịch sử vị trí: key -> số lần xuất hiện
        self.position_history = {}
        # ghi nhận vị trí ban đầu
        initial_key = self._get_position_key()
        self.position_history[initial_key] = 1

    # ------------------------------------------------------------------
    # Tạo khóa định danh trạng thái bàn cờ (dùng cho luật lặp 3 lần)
    # ------------------------------------------------------------------
    def _get_position_key(self):
        """
        Tạo khóa duy nhất cho trạng thái bàn cờ hiện tại.
        Bao gồm: bàn cờ, lượt đi, quyền nhập thành, ô bắt tốt qua đường.
        """
        board_str = "".join("".join(row) for row in self.board)
        turn_str = "w" if self.white_to_move else "b"
        castle_str = (f"{int(self.current_castling_rights.wks)}"
                      f"{int(self.current_castling_rights.bks)}"
                      f"{int(self.current_castling_rights.wqs)}"
                      f"{int(self.current_castling_rights.bqs)}")
        ep_str = str(self.enpassant_possible)
        return f"{board_str}|{turn_str}|{castle_str}|{ep_str}"

    def makeMove(self, move, piecePromotion="Q"):
        # Thực hiện 1 move và cập nhật trạng thái trò chơi
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved
        self.move_log.append(move) 
        self.white_to_move = not self.white_to_move  # chuyển quyền cho đối phương

        # cập nhật vị trí vua nếu cần
        if move.piece_moved == "wK":
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == "bK":
            self.black_king_location = (move.end_row, move.end_col)
        
        # tốt thăng cấp
        if move.is_pawn_promotion: 
            self.board[move.end_row][move.end_col] = move.piece_moved[0] + piecePromotion
        
        # xoá tốt bị bắt sang đường
        if move.is_enpassant_move:
            self.board[move.start_row][move.end_col] = "--"
        
        # cập nhật biến enpassant_possible
        if move.piece_moved[1] == "p" and abs(move.start_row - move.end_row) == 2:
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_col)
        else:
            self.enpassant_possible = ()
        
        # nhập thành
        if move.is_castle_move: 
            if move.end_col - move.start_col == 2:   # king-side
                self.board[move.end_row][move.end_col - 1] = self.board[move.end_row][move.end_col + 1]
                self.board[move.end_row][move.end_col + 1] = "--"
            else:  # queen-side
                self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 2]
                self.board[move.end_row][move.end_col - 2] = "--"
        
        self.enpassant_possible_log.append(self.enpassant_possible)
        
        # cập nhật quyền nhập thành
        self.updateCastleRights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_rights.wks,
                                                   self.current_castling_rights.bks,
                                                   self.current_castling_rights.wqs,
                                                   self.current_castling_rights.bqs))

        # -------------------------------------------------------
        # Cập nhật bộ đếm 50 nước
        # Reset nếu đi tốt hoặc ăn quân; ngược lại tăng thêm 1
        # -------------------------------------------------------
        if move.piece_moved[1] == "p" or move.is_capture:
            self.fifty_move_counter = 0
        else:
            self.fifty_move_counter += 1
        self.fifty_move_counter_log.append(self.fifty_move_counter)

        # -------------------------------------------------------
        # Ghi nhận vị trí mới vào lịch sử (luật lặp 3 lần)
        # -------------------------------------------------------
        position_key = self._get_position_key()
        self.position_history[position_key] = self.position_history.get(position_key, 0) + 1

    def undoMove(self):
        if len(self.move_log) != 0:
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move
            
            # cập nhật lại vị trí vua
            if move.piece_moved == "wK":  
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == "bK":
                self.black_king_location = (move.start_row, move.start_col)
            
            # hoàn tác bắt tốt qua đường
            if move.is_enpassant_move:
                self.board[move.end_row][move.end_col] = "--"
                self.board[move.start_row][move.end_col] = move.piece_captured

            self.enpassant_possible_log.pop()
            self.enpassant_possible = self.enpassant_possible_log[-1]

            # hoàn tác quyền nhập thành
            self.castle_rights_log.pop()
            self.current_castling_rights = self.castle_rights_log[-1]
            
            # hoàn tác nước nhập thành
            if move.is_castle_move:
                if move.end_col - move.start_col == 2:  # king-side
                    self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 1]
                    self.board[move.end_row][move.end_col - 1] = '--'
                else:  # queen-side
                    self.board[move.end_row][move.end_col - 2] = self.board[move.end_row][move.end_col + 1]
                    self.board[move.end_row][move.end_col + 1] = '--'
            
            self.checkmate = False
            self.stalemate = False
            self.threefold_repetition = False

            # -------------------------------------------------------
            # Hoàn tác bộ đếm 50 nước
            # -------------------------------------------------------
            self.fifty_move_counter_log.pop()
            self.fifty_move_counter = self.fifty_move_counter_log[-1]

            # -------------------------------------------------------
            # Hoàn tác lịch sử vị trí (luật lặp 3 lần)
            # Xoá vị trí SAU KHI undo (tức vị trí hiện tại sau khi đã lùi quân)
            # -------------------------------------------------------
            position_key = self._get_position_key()
            if position_key in self.position_history:
                self.position_history[position_key] -= 1
                if self.position_history[position_key] <= 0:
                    del self.position_history[position_key]

    def updateCastleRights(self, move):
        """Cập nhật quyền nhập thành sau mỗi nước đi."""
        if move.piece_captured == "wR":
            if move.end_col == 0: 
                self.current_castling_rights.wqs = False
            elif move.end_col == 7:
                self.current_castling_rights.wks = False
        elif move.piece_captured == "bR":
            if move.end_col == 0: 
                self.current_castling_rights.bqs = False
            elif move.end_col == 7:  
                self.current_castling_rights.bks = False

        if move.piece_moved == "wK":
            self.current_castling_rights.wqs = False
            self.current_castling_rights.wks = False
        elif move.piece_moved == 'bK':
            self.current_castling_rights.bqs = False
            self.current_castling_rights.bks = False
        elif move.piece_moved == 'wR':
            if move.start_row == 7:
                if move.start_col == 0:  
                    self.current_castling_rights.wqs = False
                elif move.start_col == 7: 
                    self.current_castling_rights.wks = False
        elif move.piece_moved == 'bR':
            if move.start_row == 0:
                if move.start_col == 0:  
                    self.current_castling_rights.bqs = False
                elif move.start_col == 7:  
                    self.current_castling_rights.bks = False

    def getValidMoves(self):
        """Trả về toàn bộ nước đi hợp lệ."""
        temp_castle_rights = CastleRights(self.current_castling_rights.wks, self.current_castling_rights.bks,
                                          self.current_castling_rights.wqs, self.current_castling_rights.bqs)
        moves = []
        self.in_check, self.pins, self.checks = self.checkForPinsAndChecks()

        if self.white_to_move:
            king_row = self.white_king_location[0]
            king_col = self.white_king_location[1]
        else:
            king_row = self.black_king_location[0]
            king_col = self.black_king_location[1]
        
        if self.in_check:
            if len(self.checks) == 1:  # chỉ 1 chiếu: chặn hoặc di vua
                moves = self.getAllPossibleMoves()
                check = self.checks[0]
                check_row = check[0]
                check_col = check[1]
                piece_checking = self.board[check_row][check_col]
                valid_squares = []
                
                if piece_checking[1] == "N":
                    valid_squares = [(check_row, check_col)]
                else:
                    for i in range(1, 8):
                        valid_square = (king_row + check[2] * i, king_col + check[3] * i)
                        valid_squares.append(valid_square)
                        if valid_square[0] == check_row and valid_square[1] == check_col:
                            break
                
                for i in range(len(moves) - 1, -1, -1):
                    if moves[i].piece_moved[1] != "K":
                        if not (moves[i].end_row, moves[i].end_col) in valid_squares:
                            if moves[i].is_enpassant_move and (moves[i].start_row, moves[i].end_col) in valid_squares:
                                pass
                            else:
                                moves.remove(moves[i])
            else:  # double check: vua phải di chuyển
                self.getKingMoves(king_row, king_col, moves)
        else:
            moves = self.getAllPossibleMoves()
            if self.white_to_move:
                self.getCastleMoves(self.white_king_location[0], self.white_king_location[1], moves)
            else:
                self.getCastleMoves(self.black_king_location[0], self.black_king_location[1], moves)

        # Kiểm tra chiếu hết / hết nước
        if len(moves) == 0:
            if self.inCheck():
                self.checkmate = True
            else:
                self.stalemate = True  # hòa do hết nước đi
        else:
            self.checkmate = False
            self.stalemate = False
            self.threefold_repetition = False

        # -------------------------------------------------------
        # Kiểm tra hòa do luật 50 nước
        # 100 nửa-nước = 50 nước mỗi bên
        # -------------------------------------------------------
        if self.fifty_move_counter >= 100:
            self.stalemate = True

        # -------------------------------------------------------
        # Kiểm tra hòa do lặp lại vị trí 3 lần
        # -------------------------------------------------------
        position_key = self._get_position_key()
        if self.position_history.get(position_key, 0) >= 3:
            self.threefold_repetition = True
            self.stalemate = True

        self.current_castling_rights = temp_castle_rights
        return moves

    def get_valid_moves_for_square(self, row: int, col: int):
        piece = self.board[row][col]
        if piece == "--":
            return []
        valid_moves = self.getValidMoves()
        return [move for move in valid_moves if move.start_row == row and move.start_col == col]

    def inCheck(self):
        if self.white_to_move:
            return self.squareUnderAttack(self.white_king_location[0], self.white_king_location[1])
        else:
            return self.squareUnderAttack(self.black_king_location[0], self.black_king_location[1])
 
    def squareUnderAttack(self, row, col): 
        self.white_to_move = not self.white_to_move
        opponents_moves = self.getAllPossibleMoves()
        self.white_to_move = not self.white_to_move
        for move in opponents_moves:
            if move.end_row == row and move.end_col == col:
                return True
        return False 

    def getAllPossibleMoves(self):
        moves = []
        for row in range(len(self.board)):
            for col in range(len(self.board[row])):
                turn = self.board[row][col][0]
                if (turn == "w" and self.white_to_move) or (turn == "b" and not self.white_to_move):
                    piece = self.board[row][col][1]
                    self.moveFunctions[piece](row, col, moves)
        return moves 

    def checkForPinsAndChecks(self):
        pins = []
        checks = []
        in_check = False
        if self.white_to_move:
            enemy_color = "b"
            ally_color = "w"
            start_row = self.white_king_location[0]
            start_col = self.white_king_location[1]
        else:
            enemy_color = "w"
            ally_color = "b"
            start_row = self.black_king_location[0]
            start_col = self.black_king_location[1]

        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for j in range(len(directions)):
            direction = directions[j]
            possible_pin = ()
            for i in range(1, 8):
                end_row = start_row + direction[0] * i
                end_col = start_col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] == ally_color and end_piece[1] != "K":
                        if possible_pin == ():
                            possible_pin = (end_row, end_col, direction[0], direction[1])
                        else:
                            break
                    elif end_piece[0] == enemy_color:
                        enemy_type = end_piece[1]
                        if (0 <= j <= 3 and enemy_type == "R") or \
                           (4 <= j <= 7 and enemy_type == "B") or \
                           (i == 1 and enemy_type == "p" and (
                               (enemy_color == "w" and 6 <= j <= 7) or
                               (enemy_color == "b" and 4 <= j <= 5))) or \
                           (enemy_type == "Q") or \
                           (i == 1 and enemy_type == "K"):
                            if possible_pin == ():
                                in_check = True
                                checks.append((end_row, end_col, direction[0], direction[1]))
                                break
                            else:
                                pins.append(possible_pin)
                                break
                        else:
                            break
                else:
                    break

        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2), (1, -2))
        for move in knight_moves:
            end_row = start_row + move[0]
            end_col = start_col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] == enemy_color and end_piece[1] == "N":
                    in_check = True
                    checks.append((end_row, end_col, move[0], move[1]))
        return in_check, pins, checks

    def getPawnMoves(self, row, col, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        if self.white_to_move:
            move_amount = -1
            start_row = 6
            enemy_color = "b"
            king_row, king_col = self.white_king_location
        else:
            move_amount = 1
            start_row = 1
            enemy_color = "w"
            king_row, king_col = self.black_king_location

        if self.board[row + move_amount][col] == "--":
            if not piece_pinned or pin_direction == (move_amount, 0):
                moves.append(Move((row, col), (row + move_amount, col), self.board))
                if row == start_row and self.board[row + 2 * move_amount][col] == "--":
                    moves.append(Move((row, col), (row + 2 * move_amount, col), self.board))
        if col - 1 >= 0:
            if not piece_pinned or pin_direction == (move_amount, -1):
                if self.board[row + move_amount][col - 1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col - 1), self.board))
                if (row + move_amount, col - 1) == self.enpassant_possible:
                    attacking_piece = blocking_piece = False
                    if king_row == row:
                        if king_col < col:
                            inside_range = range(king_col + 1, col - 1)
                            outside_range = range(col + 1, 8)
                        else:
                            inside_range = range(king_col - 1, col, -1)
                            outside_range = range(col - 2, -1, -1)
                        for i in inside_range:
                            if self.board[row][i] != "--":
                                blocking_piece = True
                        for i in outside_range:
                            square = self.board[row][i]
                            if square[0] == enemy_color and (square[1] == "R" or square[1] == "Q"):
                                attacking_piece = True
                            elif square != "--":
                                blocking_piece = True
                    if not attacking_piece or blocking_piece:
                        moves.append(Move((row, col), (row + move_amount, col - 1), self.board, is_enpassant_move=True))
        if col + 1 <= 7:
            if not piece_pinned or pin_direction == (move_amount, +1):
                if self.board[row + move_amount][col + 1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col + 1), self.board))
                if (row + move_amount, col + 1) == self.enpassant_possible:
                    attacking_piece = blocking_piece = False
                    if king_row == row:
                        if king_col < col:
                            inside_range = range(king_col + 1, col)
                            outside_range = range(col + 2, 8)
                        else:
                            inside_range = range(king_col - 1, col + 1, -1)
                            outside_range = range(col - 1, -1, -1)
                        for i in inside_range:
                            if self.board[row][i] != "--":
                                blocking_piece = True
                        for i in outside_range:
                            square = self.board[row][i]
                            if square[0] == enemy_color and (square[1] == "R" or square[1] == "Q"):
                                attacking_piece = True
                            elif square != "--":
                                blocking_piece = True
                    if not attacking_piece or blocking_piece:
                        moves.append(Move((row, col), (row + move_amount, col + 1), self.board, is_enpassant_move=True))

    def getRookMoves(self, row, col, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                if self.board[row][col][1] != "Q":
                    self.pins.remove(self.pins[i])
                break

        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--":
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:
                            break
                else:
                    break

    def getKnightMoves(self, row, col, moves):
        piece_pinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break

        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2), (1, -2))
        ally_color = "w" if self.white_to_move else "b"
        for move in knight_moves:
            end_row = row + move[0]
            end_col = col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                if not piece_pinned:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] != ally_color:
                        moves.append(Move((row, col), (end_row, end_col), self.board))

    def getBishopMoves(self, row, col, moves):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        directions = ((-1, -1), (-1, 1), (1, 1), (1, -1))
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--":
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:
                            break
                else:
                    break

    def getQueenMoves(self, row, col, moves):
        self.getBishopMoves(row, col, moves)
        self.getRookMoves(row, col, moves)

    def getKingMoves(self, row, col, moves):
        row_moves = (-1, -1, -1, 0, 0, 1, 1, 1)
        col_moves = (-1, 0, 1, -1, 1, -1, 0, 1)
        ally_color = "w" if self.white_to_move else "b"
        for i in range(8):
            end_row = row + row_moves[i]
            end_col = col + col_moves[i]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] != ally_color:
                    if ally_color == "w":
                        self.white_king_location = (end_row, end_col)
                    else:
                        self.black_king_location = (end_row, end_col)
                    in_check, pins, checks = self.checkForPinsAndChecks()
                    if not in_check:
                        moves.append(Move((row, col), (end_row, end_col), self.board))
                    if ally_color == "w":
                        self.white_king_location = (row, col)
                    else:
                        self.black_king_location = (row, col)

    def getCastleMoves(self, row, col, moves):
        if self.squareUnderAttack(row, col):
            return
        if (self.white_to_move and self.current_castling_rights.wks) or \
           (not self.white_to_move and self.current_castling_rights.bks):
            self.getKingsideCastleMoves(row, col, moves)
        if (self.white_to_move and self.current_castling_rights.wqs) or \
           (not self.white_to_move and self.current_castling_rights.bqs):
            self.getQueensideCastleMoves(row, col, moves)

    def getKingsideCastleMoves(self, row, col, moves):
        if self.board[row][col + 1] == '--' and self.board[row][col + 2] == '--':
            if not self.squareUnderAttack(row, col + 1) and not self.squareUnderAttack(row, col + 2):
                moves.append(Move((row, col), (row, col + 2), self.board, is_castle_move=True))

    def getQueensideCastleMoves(self, row, col, moves):
        if self.board[row][col - 1] == '--' and self.board[row][col - 2] == '--' and self.board[row][col - 3] == '--':
            if not self.squareUnderAttack(row, col - 1) and not self.squareUnderAttack(row, col - 2):
                moves.append(Move((row, col), (row, col - 2), self.board, is_castle_move=True))

    def ReverseBoard(self):
        """Lật bàn cờ theo góc nhìn đối phương."""
        reversed_board = []
        for row in range(7, -1, -1):
            reversed_row = []
            for col in range(7, -1, -1):
                piece = self.board[row][col]
                if piece == "--":
                    reversed_row.append("--")
                else:
                    color = "w" if piece[0] == "b" else "b"
                    reversed_row.append(color + piece[1])
            reversed_board.append(reversed_row)
        return reversed_board

    # ------------------------------------------------------------------
    # Tiện ích: lấy loại hòa để hiển thị thông báo từ main.py
    # ------------------------------------------------------------------
    def getDrawReason(self):
        """
        Trả về chuỗi mô tả lý do hòa, hoặc None nếu chưa hòa.
        Dùng trong main.py để hiển thị thông báo phù hợp.
        """
        if not self.stalemate:
            return None
        if self.threefold_repetition:
            return "Hòa - Lặp lại vị trí 3 lần!"
        if self.fifty_move_counter >= 100:
            return "Hòa - Quy tắc 50 nước!"
        return "Hòa - Hết nước đi!"


class CastleRights:
    def __init__(self, wks, bks, wqs, bqs):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs


class Move:
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4,
                     "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_cols = {"a": 0, "b": 1, "c": 2, "d": 3,
                     "e": 4, "f": 5, "g": 6, "h": 7}
    cols_to_files = {v: k for k, v in files_to_cols.items()}

    def __init__(self, start_square, end_square, board, is_enpassant_move=False, is_castle_move=False):
        self.start_row = start_square[0]
        self.start_col = start_square[1]
        self.end_row = end_square[0]
        self.end_col = end_square[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        # tốt thăng cấp
        self.is_pawn_promotion = (self.piece_moved == "wp" and self.end_row == 0) or \
                                  (self.piece_moved == "bp" and self.end_row == 7)
        self.promotion_choice = 'Q'
        # bắt tốt qua đường
        self.is_enpassant_move = is_enpassant_move
        if self.is_enpassant_move:
            self.piece_captured = "wp" if self.piece_moved == "bp" else "bp"
        # nhập thành
        self.is_castle_move = is_castle_move

        self.is_capture = self.piece_captured != "--"
        self.moveID = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col

    def __eq__(self, other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False

    def getChessNotation(self):
        if self.is_pawn_promotion:
            return self.getRankFile(self.end_row, self.end_col) + "Q"
        if self.is_castle_move:
            if self.end_col == 1:
                return "0-0-0"
            else:
                return "0-0"
        if self.is_enpassant_move:
            return self.getRankFile(self.start_row, self.start_col)[0] + "x" + \
                   self.getRankFile(self.end_row, self.end_col) + " e.p."
        if self.piece_captured != "--":
            if self.piece_moved[1] == "p":
                return self.getRankFile(self.start_row, self.start_col)[0] + "x" + \
                       self.getRankFile(self.end_row, self.end_col)
            else:
                return self.piece_moved[1] + "x" + self.getRankFile(self.end_row, self.end_col)
        else:
            if self.piece_moved[1] == "p":
                return self.getRankFile(self.end_row, self.end_col)
            else:
                return self.piece_moved[1] + self.getRankFile(self.end_row, self.end_col)

    def getRankFile(self, row, col):
        return self.cols_to_files[col] + self.rows_to_ranks[row]

    def __str__(self):
        if self.is_castle_move:
            return "0-0" if self.end_col == 6 else "0-0-0"
        end_square = self.getRankFile(self.end_row, self.end_col)
        if self.piece_moved[1] == "p":
            if self.is_capture:
                return self.cols_to_files[self.start_col] + "x" + end_square
            else:
                return end_square + "Q" if self.is_pawn_promotion else end_square
        move_string = self.piece_moved[1]
        if self.is_capture:
            move_string += "x"
        return move_string + end_square