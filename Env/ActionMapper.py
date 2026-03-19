class ActionMapper:
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4,
                     "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_cols = {"a": 0, "b": 1, "c": 2, "d": 3,
                     "e": 4, "f": 5, "g": 6, "h": 7}
    cols_to_files = {v: k for k, v in files_to_cols.items()}
    def __init__(self):
        # 8 hướng di chuyển: Bắc, Đông Bắc, Đông, Đông Nam, Nam, Tây Nam, Tây, Tây Bắc
        self.direction_offsets = [
            (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)
        ]

        # 8 nước nhảy của Mã
        self.knight_offsets = [
            (1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)
        ]

        # 3 loại phong cấp phụ (Underpromotion): Mã, Tượng, Xe (Hậu tính vào Queen moves)
        self.underpromotions = ['n', 'b', 'r']

        # Dictionary lưu trữ
        self.id_to_move = {}
        self.move_to_id = {}

        # Chạy hàm này ngay khi khởi tạo để điền đầy dictionary
        self._generate_mapping()

    def _generate_mapping(self):
        """
        Tạo ra bản đồ ánh xạ cho không gian hành động 8x8x73 (4672 actions)
        Cấu trúc: [From Square][Plane ID]
        """
        files = 'abcdefgh'

        # Duyệt qua từng ô trên bàn cờ (64 ô xuất phát)
        # square_idx đi từ 0 (a1) đến 63 (h8)
        for from_sq in range(64):
            col = from_sq % 8
            row = from_sq // 8
            from_str = f"{files[col]}{row + 1}"  # VD: "e2"

            # --- NHÓM 1: QUEEN MOVES (56 Planes) ---
            # Plane 0-6: Hướng Bắc (đi 1-7 ô)
            # Plane 7-13: Hướng Đông Bắc...
            for dir_idx, (dx, dy) in enumerate(self.direction_offsets):
                for dist in range(1, 8):  # Khoảng cách từ 1 đến 7
                    # Tính ô đích
                    to_col = col + (dx * dist)
                    to_row = row + (dy * dist)

                    # Tính Plane ID (0 đến 55)
                    # Công thức: Hướng * 7 + (Khoảng cách - 1)
                    plane_idx = dir_idx * 7 + (dist - 1)

                    # Tính Action ID tổng (Flat index)
                    action_id = from_sq * 73 + plane_idx

                    # Nếu ô đích nằm trong bàn cờ -> Lưu lại
                    if 0 <= to_col < 8 and 0 <= to_row < 8:
                        to_str = f"{files[to_col]}{to_row + 1}"
                        move_uci = from_str + to_str  # VD: "e2e4"

                        # Lưu ý: Nếu Tốt đi đến hàng cuối, mặc định là phong Hậu (Queen)
                        # Logic AlphaZero gộp Phong Hậu vào Queen Moves.
                        # Chúng ta cần check nếu là nước phong cấp thì thêm 'q'
                        is_promotion = (row == 6 and to_row == 7) or (row == 1 and to_row == 0)
                        # (Lưu ý: đây là check theo tọa độ, thực tế phải check quân cờ,
                        # nhưng ở mức mapping ta cứ lưu cả 2 dạng cho chắc ăn hoặc xử lý logic sau)

                        # Ở đây tui lưu dạng UCI thuần túy "e7e8", 
                        # việc nó là phong hậu hay không do Game Logic quyết định khi khớp lệnh.
                        # Nhưng để chính xác với thư viện cờ, nếu là nước từ hàng 2->1 hoặc 7->8,
                        # ta nên map thêm trường hợp phong hậu.

                        if is_promotion:
                            # Map riêng cho trường hợp phong hậu (thường thư viện cờ đòi "a7a8q")
                            self.id_to_move[action_id] = move_uci + 'q'
                            self.move_to_id[move_uci + 'q'] = action_id
                        else:
                            self.id_to_move[action_id] = move_uci
                            self.move_to_id[move_uci] = action_id

            # --- NHÓM 2: KNIGHT MOVES (8 Planes) ---
            # Plane 56-63
            for k_idx, (dx, dy) in enumerate(self.knight_offsets):
                to_col = col + dx
                to_row = row + dy

                plane_idx = 56 + k_idx
                action_id = from_sq * 73 + plane_idx

                if 0 <= to_col < 8 and 0 <= to_row < 8:
                    to_str = f"{files[to_col]}{to_row + 1}"
                    move_uci = from_str + to_str
                    self.id_to_move[action_id] = move_uci
                    self.move_to_id[move_uci] = action_id

            # --- NHÓM 3: UNDERPROMOTIONS (9 Planes) ---
            # Plane 64-72: Phong Mã, Tượng, Xe
            # Chỉ có ý nghĩa khi đi từ hàng 7->8 hoặc 2->1
            # 3 hướng: Chéo trái, Thẳng, Chéo phải (tương ứng với hướng Bắc của quân Tốt)
            # Lưu ý: Mapping này hơi phức tạp vì phụ thuộc màu quân (Tốt Trắng đi lên, Đen đi xuống)
            # Nhưng để đơn giản (Canonical form), ta giả định luôn đi lên (North).

            # Hướng di chuyển của tốt để phong cấp (tính theo hướng Bắc - North)
            # -1: Chéo trái, 0: Thẳng, 1: Chéo phải (theo trục X)
            promo_dirs = [-1, 0, 1]

            for d_idx, dx in enumerate(promo_dirs):
                for p_idx, promo_char in enumerate(self.underpromotions):
                    # Plane index: 64 + (Hướng * 3) + Loại quân
                    plane_idx = 64 + (d_idx * 3) + p_idx
                    action_id = from_sq * 73 + plane_idx

                    # Giả định đi lên (cho Trắng)
                    dy = 1
                    to_col = col + dx
                    to_row = row + dy

                    if 0 <= to_col < 8 and 0 <= to_row < 8:
                        to_str = f"{files[to_col]}{to_row + 1}"
                        move_uci = from_str + to_str + promo_char  # VD: "a7a8n"
                        self.id_to_move[action_id] = move_uci
                        self.move_to_id[move_uci] = action_id

                    # (Tùy chọn) Nếu muốn hỗ trợ cả Tốt Đen đi xuống trong mapping tĩnh
                    # Thì cần logic phức tạp hơn, nhưng thường ta xoay bàn cờ về Trắng
                    # nên chỉ cần tính hướng đi lên là đủ.

    def decode(self, action_id):
        """
        AI -> Game
        Input: 205
        Output: "e2e4"
        """

        return self.id_to_move.get(action_id, None)

    def encode(self, move_str):
        """
        Game -> AI (để tạo Mask)
        Input: "e2e4"
        Output: 205
        """
        return self.move_to_id.get(move_str, None)

    def move_to_position(self, uci_string):
        """
        Chuyển đổi UCI sang các vị trí riêng biệt
        Input: "e2e4" hoặc "a7a8q"
        Output: {
            'from': (start_row, start_col),
            'to': (end_row, end_col),
            'promotion': 'Q' hoặc None
        }
        """
        coords = self.uci_to_coords(uci_string)
        if coords is None:
            return None

        start_row, start_col, end_row, end_col, promo = coords

        return {
            'from': (start_row, start_col),
            'to': (end_row, end_col),
            'promotion': promo
        }

    def uci_to_coords(self,uci_string):
        """
        Input: "e2e4" hoặc "a7a8q"
        Output: (start_row, start_col, end_row, end_col, promotion_char)
        """
        if uci_string is None:
            return None

        # 1. Tách chuỗi
        # e2e4 -> start_file='e', start_rank='2', end_file='e', end_rank='4'
        s_file = uci_string[0]
        s_rank = uci_string[1]
        e_file = uci_string[2]
        e_rank = uci_string[3]

        # 2. Xử lý phong cấp (nếu có ký tự thứ 5)
        promo = None
        if len(uci_string) == 5:
            promo = uci_string[4].upper()  # 'q' -> 'Q' để khớp với logic game

        # 3. Chuyển đổi sang tọa độ số
        # Lưu ý: Phải dùng đúng dictionary trong Class Move của bạn
        # ranks_to_rows: {'1': 7, ... '8': 0}
        # files_to_cols: {'a': 0, ... 'h': 7}

        start_row = self.ranks_to_rows[s_rank]
        start_col = self.files_to_cols[s_file]

        end_row = self.ranks_to_rows[e_rank]
        end_col = self.files_to_cols[e_file]

        return start_row, start_col, end_row, end_col, promo
