import itertools
from collections import namedtuple
from Shared.Consts import WHITE, BLACK, EMPTY

N = 19
NN = N ** 2
EMPTY_BOARD = EMPTY * NN

def swap_colors(color):
    if color == BLACK:
        return WHITE
    elif color == WHITE:
        return BLACK
    else:
        return color


def flatten(c):
    return N * c[0] + c[1]

# Convention: coords that have been flattened have a "f" prefix
def unflatten(fc):
    return divmod(fc, N)

def is_on_board(c):
    return c[0] % N == c[0] and c[1] % N == c[1]

def get_valid_neighbors(fc):
    x, y = unflatten(fc)
    possible_neighbors = ((x+1, y), (x-1, y), (x, y+1), (x, y-1))
    return [flatten(n) for n in possible_neighbors if is_on_board(n)]

# Neighbors are indexed by flat coordinates
NEIGHBORS = [get_valid_neighbors(fc) for fc in range(NN)]

def set_size(n):
    global N, NN, EMPTY_BOARD, NEIGHBORS
    N = n
    NN = N ** 2
    EMPTY_BOARD = EMPTY * NN
    NEIGHBORS = [get_valid_neighbors(fc) for fc in range(NN)]

def find_reached(board, fc):
    color = board[fc]
    chain = set([fc])
    reached = set()
    frontier = [fc]
    while frontier:
        current_fc = frontier.pop()
        chain.add(current_fc)
        for fn in NEIGHBORS[current_fc]:
            if board[fn] == color and not fn in chain:
                frontier.append(fn)
            elif board[fn] != color:
                reached.add(fn)
    return chain, reached

class IllegalMove(Exception): pass

def place_stone(color, board, fc):
    return board[:fc] + color + board[fc+1:]

def bulk_place_stones(color, board, stones):
    byteboard = bytearray(board, encoding='ascii') # create mutable version of board
    color = ord(color)
    for fstone in stones:
        byteboard[fstone] = color
    return byteboard.decode('ascii') # and cast back to string when done

def maybe_capture_stones(board, fc):
    chain, reached = find_reached(board, fc)
    if not any(board[fr] == EMPTY for fr in reached):
        board = bulk_place_stones(EMPTY, board, chain)
        return board, chain
    else:
        return board, []

def play_move_incomplete(board, fc, color):
    if board[fc] != EMPTY:
        raise IllegalMove
    board = place_stone(color, board, fc)

    opp_color = swap_colors(color)
    opp_stones = []
    my_stones = []
    for fn in NEIGHBORS[fc]:
        if board[fn] == color:
            my_stones.append(fn)
        elif board[fn] == opp_color:
            opp_stones.append(fn)

    for fs in opp_stones:
        board, _ = maybe_capture_stones(board, fs)

    for fs in my_stones:
        board, _ = maybe_capture_stones(board, fs)

    return board

def is_koish(board, fc):
    'Check if fc is surrounded on all sides by 1 color, and return that color'
    if board[fc] != EMPTY: return None
    neighbor_colors = {board[fn] for fn in NEIGHBORS[fc]}
    if len(neighbor_colors) == 1 and not EMPTY in neighbor_colors:
        return list(neighbor_colors)[0]
    else:
        return None

def board_to_str(board):
    s = ''
    for i in range(N):
        for j in range(N):
            s += board[i*N+j] + ' '
        s += '\n'
    return s

def find_move(board1, board2): 
    for i in range(len(board1)):
        if board1[i] == '.' and board2[i] != '.':
            return i
    return None

def find_ko_from_boards(board1, board2):
    move = find_move(board1, board2)
    if not move:
        return None
    _, captured = maybe_capture_stones(board1, move)
    if is_koish(board1, move) and len(captured) == 1:
        return captured.pop()
    return None


class Position(namedtuple('Position', ['board', 'ko'])):
    @staticmethod
    def initial_state():
        return Position(board=EMPTY_BOARD, ko=None)

    @staticmethod
    def set_board(board, ko):
        return Position(board=board, ko=ko)

    def __str__(self):
        return board_to_str(self.board)

    def print_illegal_move(self, fc):
        print('Original board:')
        print(self)
        print('Attempted position:')
        l = list(self.board)
        l[fc] = '#'
        print(board_to_str(''.join(l)))
        

    def get_legal_moves(self):
        board = [1 if x==EMPTY else 0 for x in self.board ]
        if self.ko:
            board[self.ko] = 0
        return board
    
    def play_move(self, fc, color):
        board, ko = self
        if fc == ko or board[fc] != EMPTY:
            self.print_illegal_move(fc)
            raise IllegalMove 

        possible_ko_color = is_koish(board, fc)
        new_board = place_stone(color, board, fc)

        opp_color = swap_colors(color)
        opp_stones = []
        my_stones = []
        my_stones.append(fc)
        for fn in NEIGHBORS[fc]:
            if new_board[fn] == color:
                my_stones.append(fn)
            elif new_board[fn] == opp_color:
                opp_stones.append(fn)

        opp_captured = []
        for fs in opp_stones:
            new_board, captured = maybe_capture_stones(new_board, fs)
            opp_captured += list(captured)

        for fs in my_stones:
            new_board, _ = maybe_capture_stones(new_board, fs)

        if len(opp_captured) == 1 and possible_ko_color == opp_color:
            new_ko = opp_captured[0]
        else:
            new_ko = None

        return Position(new_board, new_ko)

    def score(self):
        board = self.board
        while EMPTY in board:
            fempty = board.index(EMPTY)
            empties, borders = find_reached(board, fempty)
            if len(borders) == 0:
                # there is no stone on the board
                return 0
            possible_border_color = board[list(borders)[0]]
            if all(board[fb] == possible_border_color for fb in borders):
                board = bulk_place_stones(possible_border_color, board, empties)
            else:
                # if an empty intersection reaches both white and black,
                # then it belongs to neither player. 
                board = bulk_place_stones('?', board, empties)
        return board.count(BLACK) - board.count(WHITE) - 1 # komi of 1

    def get_liberties(self):
        board = self.board
        liberties = bytearray(NN)
        for color in (WHITE, BLACK):
            while color in board:
                fc = board.index(color)
                stones, borders = find_reached(board, fc)
                num_libs = len([fb for fb in borders if board[fb] == EMPTY])
                for fs in stones:
                    liberties[fs] = num_libs
                board = bulk_place_stones('?', board, stones)
        return list(liberties)