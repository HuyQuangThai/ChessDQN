from .CastleRights import CastleRights
from .Move import Move

class GameState:  #trạng thái và luật chơi cờ vuaaaaa
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
        
        self.white_to_move = True  #(quân trắng đi trước)
        self.move_log = []
        self.white_king_location = (7, 4) 
        self.black_king_location = (0, 4)   
        self.stalemate = False # (cờ hòa)
        self.checkmate = False 
        self.in_check = False  # vua đang bị chiếu 
        self.pins = [] #danh sách quân bị ghim 
        self.checks = [] #danh sách quân chiếu vua
        self.enpassant_possible = () #luu vi tri co the bat tot qua duong 
        self.enpassant_possible_log = [self.enpassant_possible] #nhat ky bat tot qua duong 
        self.current_castling_rights = CastleRights(True, True, True, True)
        self.history = []
        self.castle_rights_log = [CastleRights(self.current_castling_rights.wks, 
                                               self.current_castling_rights.bks,
                                                self.current_castling_rights.wqs, 
                                                self.current_castling_rights.bqs)]

    def makeMove(self, move, piecePromotion = "Q"):
        #Mục tiêu là thực hiện 1 move và cập nhật trạng thái trò chơi
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved  #cap nhat lai o di chuyen
        self.move_log.append(move)
        self.white_to_move = not self.white_to_move
        # cập nhật vị trí vua nếu cần
        if move.piece_moved == "wK":
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == "bK":
            self.black_king_location = (move.end_row, move.end_col)

        #pawn promotion / tot thang cap
        if move.is_pawn_promotion:
            self.board[move.end_row][move.end_col] = move.piece_moved[0] + piecePromotion
            # mặc định thăng cấp lên hậu

        # xoa tot bi bat sang duong
        if move.is_enpassant_move:
            self.board[move.start_row][move.end_col] = "--"

        # cập nhật biến enpassant_possible / điều kiện để đối phương bắt tốt qua đường tại vị trí đã setup
        if move.piece_moved[1] == "p" and abs(move.start_row - move.end_row) == 2:
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_col)
        else:
            self.enpassant_possible = ()  # chỉ nhận trạng thái qua đường đầu tiên nếu tiếp theo thì xóa khỏi

        # Nhập thành
        if move.is_castle_move:
            if move.end_col - move.start_col == 2:   # di chuyen nhap thanh king-side
                self.board[move.end_row][move.end_col - 1] = self.board[move.end_row][move.end_col + 1]  #moves the rook to its new square
                self.board[move.end_row][move.end_col + 1] = "--"
            else: #di chuyen nhap thanh queen-side
                self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 2]
                self.board[move.end_row][move.end_col - 2] = "--" #erase old rook

        #luu nhung nuoc bat tot qua duong
        self.enpassant_possible_log.append(self.enpassant_possible)

        # update quyen nhat thanh
        self.updateCastleRights(move)
        self.castle_rights_log.append(CastleRights(self.current_castling_rights.wks, self.current_castling_rights.bks,
                                                   self.current_castling_rights.wqs, self.current_castling_rights.bqs))
        self.history.append([row[:] for row in self.board])

    def undoMove(self):
        if len(self.move_log) != 0: # hoan tac lai di chuyen
            self.history.pop()
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move
            
            # update the king's position if needed
            if move.piece_moved == "wK":  
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == "bK":
                self.black_king_location = (move.start_row, move.start_col)
            
            # undo en passant move
            if move.is_enpassant_move:
                self.board[move.end_row][move.end_col] = "--"  # leave landing square blank
                self.board[move.start_row][move.end_col] = move.piece_captured

            self.enpassant_possible_log.pop()
            self.enpassant_possible = self.enpassant_possible_log[-1]

            # undo castle rights
            self.castle_rights_log.pop()  # get rid of the new castle rights from the move we are undoing
            self.current_castling_rights = self.castle_rights_log[-1]  # set the current castle rights to the last one in the list
            
            # undo the castle move
            if move.is_castle_move:
                if move.end_col - move.start_col == 2:  # king-side
                    self.board[move.end_row][move.end_col + 1] = self.board[move.end_row][move.end_col - 1]
                    self.board[move.end_row][move.end_col - 1] = '--'
                else:  # queen-side
                    self.board[move.end_row][move.end_col - 2] = self.board[move.end_row][move.end_col + 1]
                    self.board[move.end_row][move.end_col + 1] = '--'
            
            self.checkmate = False
            self.stalemate = False

    def updateCastleRights(self, move):
        """
        Update the castle rights given the move
        """
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

    def get_state_id(self):
        """
        Tạo ra một chuỗi string đại diện duy nhất cho trạng thái hiện tại.
        Bao gồm: Bàn cờ, lượt đi, quyền nhập thành, en_passant.
        """
        # Nối chuỗi bàn cờ (flatten)
        board_str = "".join(["".join(row) for row in self.board])

        # Quyền nhập thành (ws: white short, wl: white long...)
        castling = f"{int(self.current_castling_rights.wks)}{int(self.current_castling_rights.wqs)}{int(self.current_castling_rights.bks)}{int(self.current_castling_rights.bqs)}"

        # En passant target
        ep = str(self.enpassant_possible) if self.enpassant_possible else "-"

        # Lượt đi
        turn = "w" if self.white_to_move else "b"

        return f"{board_str}|{turn}|{castling}|{ep}"
    def getValidMoves(self):
        """
        Mục tiêu trả về toàn bộ nước đi hợp lệ
        """
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
            if len(self.checks) == 1:  # chỉ có 1 chiếu, chặn chiếu hoặc di chuyển vua
                moves = self.getAllPossibleMoves()
                # để chặn chiếu, bạn phải đặt một quân vào một trong các ô giữa quân địch và vua của bạn
                check = self.checks[0]  # thông tin chiếu
                check_row = check[0]
                check_col = check[1]
                piece_checking = self.board[check_row][check_col]
                valid_squares = []  # squares that pieces can move to

                if piece_checking[1] == "N":
                    valid_squares = [(check_row, check_col)]
                else:
                    for i in range(1, 8):
                        valid_square = (king_row + check[2] * i,
                                        king_col + check[3] * i)
                        valid_squares.append(valid_square)
                        if valid_square[0] == check_row and valid_square[1] == check_col:  # một khi bạn đến quân và chiếu
                            break

                # loại bỏ bất kỳ nước đi nào không chặn chiếu hoặc di chuyển vua
                for i in range(len(moves) - 1, -1, -1):  # duyệt qua danh sách ngược khi loại bỏ phần tử
                    if moves[i].piece_moved[1] != "K":  # nước đi không di chuyển vua nên phải chặn hoặc bắt
                        if not (moves[i].end_row, moves[i].end_col) in valid_squares:  # move doesn't block or capture piece
                            moves.remove(moves[i])
            else:  # double check, king has to move
                self.getKingMoves(king_row, king_col, moves)
        else:  # not in check - all moves are fine
            moves = self.getAllPossibleMoves()
            if self.white_to_move:
                self.getCastleMoves(self.white_king_location[0], self.white_king_location[1], moves)
            else:
                self.getCastleMoves(self.black_king_location[0], self.black_king_location[1], moves)

        if len(moves) == 0:
            if self.inCheck():
                self.checkmate = True
            else:
                # TODO stalemate on repeated moves
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        self.current_castling_rights = temp_castle_rights
        return moves
    
    def get_valid_moves_for_square(self, row: int, col: int):
        piece = self.board[row][col]
        if piece == "--":
            return []

        valid_moves = self.getValidMoves()
        return [
            move for move in valid_moves
            if move.start_row == row and move.start_col == col
        ]

    def inCheck(self):
        if self.white_to_move:
            return self.squareUnderAttack(self.white_king_location[0], self.white_king_location[1])
        else:
            return self.squareUnderAttack(self.black_king_location[0], self.black_king_location[1])
 
    def squareUnderAttack(self, row, col): 
        self.white_to_move = not self.white_to_move
        opponents_moves = self.getAllPossibleMoves()  # lấy tất cả nước đi của đối thủ
        self.white_to_move = not self.white_to_move # đổi ngược lại của mình 
        for move in opponents_moves:
            if move.end_row == row and move.end_col == col:  # vua bị tấn công
                return True
        return False 

    def getAllPossibleMoves(self):
        moves = []
        for row in range(len(self.board)):
            for col in range(len(self.board[row])):
                turn = self.board[row][col][0]
                if (turn == "w" and self.white_to_move) or (turn == "b" and not self.white_to_move):
                    piece = self.board[row][col][1]
                    self.moveFunctions[piece](row, col, moves)  # ham di chuyen cua quan co dua vao // tham chieu gia tri ten quan co 
        return moves 

    def checkForPinsAndChecks(self):
        pins = []  # squares pinned and the direction its pinned from
        checks = []  # squares where enemy is applying a check
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
        # check outwards from king for pins and checks, keep track of pins
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for j in range(len(directions)):
            direction = directions[j]
            possible_pin = ()  # reset possible pins
            for i in range(1, 8):
                end_row = start_row + direction[0] * i
                end_col = start_col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] == ally_color and end_piece[1] != "K":
                        if possible_pin == ():  # first allied piece could be pinned
                            possible_pin = (end_row, end_col, direction[0], direction[1])
                        else:  # 2nd allied piece - no check or pin from this direction
                            break
                    elif end_piece[0] == enemy_color:
                        enemy_type = end_piece[1]
                        # 5 possibilities in this complex conditional
                        # 1.) orthogonally away from king and piece is a rook
                        # 2.) diagonally away from king and piece is a bishop
                        # 3.) 1 square away diagonally from king and piece is a pawn
                        # 4.) any direction and piece is a queen
                        # 5.) any direction 1 square away and piece is a king
                        if (0 <= j <= 3 and enemy_type == "R") or (4 <= j <= 7 and enemy_type == "B") or (
                                i == 1 and enemy_type == "p" and (
                                (enemy_color == "w" and 6 <= j <= 7) or (enemy_color == "b" and 4 <= j <= 5))) or (
                                enemy_type == "Q") or (i == 1 and enemy_type == "K"):
                            if possible_pin == ():    # no piece blocking, so check
                                in_check = True
                                checks.append((end_row, end_col, direction[0], direction[1]))
                                break
                            else:  # piece blocking so pin
                                pins.append(possible_pin)
                                break
                        else:  # enemy piece not applying checks
                            break
                else:
                    break  # off board
        # check for knight checks
        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2), (1, -2))
        for move in knight_moves:
            end_row = start_row + move[0]
            end_col = start_col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] == enemy_color and end_piece[1] == "N":  # enemy knight attacking a king
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

        if self.board[row + move_amount][col] == "--":  # 1 square pawn advance
            if not piece_pinned or pin_direction == (move_amount, 0):
                moves.append(Move((row, col), (row + move_amount, col), self.board))
                if row == start_row and self.board[row + 2 * move_amount][col] == "--":  # 2 square pawn advance
                    moves.append(Move((row, col), (row + 2 * move_amount, col), self.board))
        if col - 1 >= 0:  # capture to the left
            if not piece_pinned or pin_direction == (move_amount, -1):
                if self.board[row + move_amount][col - 1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col - 1), self.board))
                if (row + move_amount, col - 1) == self.enpassant_possible:
                    attacking_piece = blocking_piece = False
                    if king_row == row:
                        if king_col < col:  # king is left of the pawn
                            # inside: between king and the pawn;
                            # outside: between pawn and border;
                            inside_range = range(king_col + 1, col - 1)
                            outside_range = range(col + 1, 7)
                        else:  # king right of the pawn
                            inside_range = range(king_col - 1, col, -1)
                            outside_range = range(col - 2, -1, -1)
                        for i in inside_range:
                            if self.board[row][i] != "--":  # some piece beside en-passant pawn blocks
                                blocking_piece = True
                        for i in outside_range:
                            square = self.board[row][i]
                            if square[0] == enemy_color and (square[1] == "R" or square[1] == "Q"):
                                attacking_piece = True
                            elif square != "--":
                                blocking_piece = True
                    if not attacking_piece or blocking_piece:
                        moves.append(Move((row, col), (row + move_amount, col - 1), self.board, is_enpassant_move=True))
        if col + 1 <= 7:  # capture to the right
            if not piece_pinned or pin_direction == (move_amount, +1):
                if self.board[row + move_amount][col + 1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col + 1), self.board))
                if (row + move_amount, col + 1) == self.enpassant_possible:
                    attacking_piece = blocking_piece = False
                    if king_row == row:
                        if king_col < col:  # king is left of the pawn
                            # inside: between king and the pawn;
                            # outside: between pawn and border;
                            inside_range = range(king_col + 1, col)
                            outside_range = range(col + 2, 8)
                        else:  # king right of the pawn
                            inside_range = range(king_col - 1, col + 1, -1)
                            outside_range = range(col - 1, -1, -1)
                        for i in inside_range:
                            if self.board[row][i] != "--":  # some piece beside en-passant pawn blocks
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
        """
        Get all the rook moves for the rook located at row, col and add the moves to the list.
        """
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                if self.board[row][col][
                    1] != "Q":  # can't remove queen from pin on rook moves, only remove it on bishop moves
                    self.pins.remove(self.pins[i])
                break

        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))  # up, left, down, right
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:  # check for possible moves only in boundaries of the board
                    if not piece_pinned or pin_direction == direction or pin_direction == (
                            -direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--":  # empty space is valid
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:  # capture enemy piece
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:  # friendly piece
                            break
                else:  # off board
                    break

    def getKnightMoves(self, row, col, moves):
        """
        Get all the knight moves for the knight located at row col and add the moves to the list.
        """
        piece_pinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break

        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2),
                        (1, -2))  # up/left up/right right/up right/down down/left down/right left/up left/down
        ally_color = "w" if self.white_to_move else "b"
        for move in knight_moves:
            end_row = row + move[0]
            end_col = col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                if not piece_pinned:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] != ally_color:  # so its either enemy piece or empty square
                        moves.append(Move((row, col), (end_row, end_col), self.board))

    def getBishopMoves(self, row, col, moves):
        """
        Get all the bishop moves for the bishop located at row col and add the moves to the list.
        """
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break

        directions = ((-1, -1), (-1, 1), (1, 1), (1, -1))  # diagonals: up/left up/right down/right down/left
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:  # check if the move is on board
                    if not piece_pinned or pin_direction == direction or pin_direction == (
                            -direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--":  # empty space is valid
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:  # capture enemy piece
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:  # friendly piece
                            break
                else:  # off board
                    break

    def getQueenMoves(self, row, col, moves):
        """
        Get all the queen moves for the queen located at row col and add the moves to the list.
        """
        self.getBishopMoves(row, col, moves)
        self.getRookMoves(row, col, moves)

    def getKingMoves(self, row, col, moves):
        """
        Get all the king moves for the king located at row col and add the moves to the list.
        """
        row_moves = (-1, -1, -1, 0, 0, 1, 1, 1)
        col_moves = (-1, 0, 1, -1, 1, -1, 0, 1)
        ally_color = "w" if self.white_to_move else "b"
        for i in range(8):
            end_row = row + row_moves[i]
            end_col = col + col_moves[i]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] != ally_color:  # not an ally piece - empty or enemy
                    # place king on end square and check for checks
                    if ally_color == "w":
                        self.white_king_location = (end_row, end_col)
                    else:
                        self.black_king_location = (end_row, end_col)
                    in_check, pins, checks = self.checkForPinsAndChecks()
                    if not in_check:
                        moves.append(Move((row, col), (end_row, end_col), self.board))
                    # place king back on original location
                    if ally_color == "w":
                        self.white_king_location = (row, col)
                    else:
                        self.black_king_location = (row, col)

    def getCastleMoves(self, row, col, moves):
        """
        Generate all valid castle moves for the king at (row, col) and add them to the list of moves.
        """
        if self.squareUnderAttack(row, col):
            return  # can't castle while in check
        if (self.white_to_move and self.current_castling_rights.wks) or (
                not self.white_to_move and self.current_castling_rights.bks):
            self.getKingsideCastleMoves(row, col, moves)
        if (self.white_to_move and self.current_castling_rights.wqs) or (
                not self.white_to_move and self.current_castling_rights.bqs):
            self.getQueensideCastleMoves(row, col, moves)

    def getKingsideCastleMoves(self, row, col, moves):
        if self.board[row][col + 1] == '--' and self.board[row][col + 2] == '--':
            if not self.squareUnderAttack(row, col + 1) and not self.squareUnderAttack(row, col + 2):
                moves.append(Move((row, col), (row, col + 2), self.board, is_castle_move=True))

    def getQueensideCastleMoves(self, row, col, moves):
        if self.board[row][col - 1] == '--' and self.board[row][col - 2] == '--' and self.board[row][col - 3] == '--':
            if not self.squareUnderAttack(row, col - 1) and not self.squareUnderAttack(row, col - 2):
                moves.append(Move((row, col), (row, col - 2), self.board, is_castle_move=True))

    def ReverseBoard(self,board):
        """
        Reverse the board for the opponent's perspective.
        """
        reversed_board = []
        for row in range(7, -1, -1):
            reversed_row = []
            for col in range(7, -1, -1):
                piece = board[row][col]
                if piece == "--":
                    reversed_row.append("--")
                else:
                    color = "w" if piece[0] == "b" else "b"
                    reversed_row.append(color + piece[1])
            reversed_board.append(reversed_row)
        return reversed_board

    def cloneState(self):
        """
        Tạo một bản sao hoàn chỉnh của trạng thái game hiện tại.
        Sử dụng deep copy để đảm bảo thay đổi trên bản sao không ảnh hưởng bản gốc.
        """
        import copy  # Import thư viện copy để dùng deepcopy

        # 1. Khởi tạo đối tượng mới (Chạy hàm __init__ để tạo khung sườn chuẩn)
        new_state = GameState()

        # 2. Sao chép Bàn cờ (Deep Copy thủ công cho nhanh hơn copy.deepcopy)
        # List comprehension tạo list mới cho từng hàng -> cắt đứt tham chiếu
        new_state.board = [row[:] for row in self.board]

        # 3. Sao chép các biến nguyên thủy (Boolean, Tuple, String...)
        # Các biến này là immutable nên gán trực tiếp là an toàn
        new_state.white_to_move = self.white_to_move
        new_state.white_king_location = self.white_king_location
        new_state.black_king_location = self.black_king_location
        new_state.checkmate = self.checkmate
        new_state.stalemate = self.stalemate
        new_state.in_check = self.in_check
        new_state.enpassant_possible = self.enpassant_possible

        # 4. Sao chép Quyền Nhập Thành (Castle Rights)
        # PHẢI tạo object CastleRights MỚI, không được gán bằng (=)
        new_state.current_castling_rights = CastleRights(
            self.current_castling_rights.wks,
            self.current_castling_rights.bks,
            self.current_castling_rights.wqs,
            self.current_castling_rights.bqs
        )

        # 5. Sao chép các Logs và Lists

        # Move Log: Nên dùng deepcopy để tách biệt hoàn toàn các object Move
        new_state.move_log = copy.deepcopy(self.move_log)

        # Enpassant Log: List chứa tuple (immutable) nên copy nông list là đủ
        new_state.enpassant_possible_log = list(self.enpassant_possible_log)

        # Castle Rights Log: List chứa object -> Phải tạo List mới chứa các Object mới
        new_state.castle_rights_log = [
            CastleRights(cr.wks, cr.bks, cr.wqs, cr.bqs)
            for cr in self.castle_rights_log
        ]

        # Pins & Checks: List chứa tuple
        new_state.pins = list(self.pins)
        new_state.checks = list(self.checks)

        # 6. Sao chép lịch sử ván đấu (History)
        # History là list chứa các board (mảng 2 chiều), cần deepcopy
        new_state.history = copy.deepcopy(self.history)

        # Lưu ý: moveFunctions là tham chiếu đến hàm, không cần copy
        new_state.moveFunctions = self.moveFunctions

        return new_state

    def getGameEnded(self,state):
        if not state.checkmate and not state.stalemate:
            _=state.getValidMoves()
        if state.checkmate:
            if state.white_to_move:
                return 1
            else:
                return -1
        if state.stalemate:
            return 1e-4

        return None