import math
import copy
import numpy as np
#from classes import *


board_size = 20
n_squares = board_size * board_size

# Generate the board as a grid
board_as_grid = {}
grid_as_board = {}
for i in range(n_squares):
    board_as_grid[str(i)] = [math.floor(i / 20), i % 20]
    grid_as_board[str([math.floor(i / 20), i % 20])] = i

active_character_position = 82
current_player_num = 0

"""
board_content = []
for i in range(400):
    board_content.append(Square(position=i, is_terrain=False, character=False, env_effects=False))

char = OrcMelee(char_id=0, controlling_player=0)
char.size = 'large'
board_content[active_character_position] = Square(position=82, is_terrain=False, character=char,
                                                  env_effects=False, large=True)
"""

def distance_between_squares(start_position, end_position):
    # Helper function to calculate ranges and moves in the battlemap
    # x = vertical, y = horizontal
    start_xy = copy.copy(board_as_grid[str(start_position)])
    end_xy = copy.copy(board_as_grid[str(end_position)])

    path = []
    n_steps = 0
    current_xy = start_xy
    while current_xy != end_xy:
        if current_xy[0] > end_xy[0]:
            current_xy[0] -= 1
        elif current_xy[0] < end_xy[0]:
            current_xy[0] += 1
        if current_xy[1] > end_xy[1]:
            current_xy[1] -= 1
        elif current_xy[1] < end_xy[1]:
            current_xy[1] += 1
        path.append(copy.copy(grid_as_board[str(current_xy)]))
        n_steps += 1

    return n_steps, path

def surrounding_pos(target_pos, include_illegal_spots=False):
    latest_pos = copy.copy(board_as_grid[str(target_pos)])
    surrounding_pos = []
    for i, j in zip([1, 1, 1, 0, -1, -1, -1, 0], [-1, 0, 1, 1, 1, 0, -1, -1]):
        # Check surrounding steps
        x = latest_pos[0] - i
        y = latest_pos[1] - j
        # logger.debug([x, y])
        if 20 > x >= 0 and 20 > y >= 0:
            step_in_board = copy.copy(grid_as_board[str([x, y])])
            surrounding_pos.append(step_in_board)
        else:
            if include_illegal_spots:
                surrounding_pos.append(False)
    return surrounding_pos

def gather_large_positions(step):
    # Takes the one spot and returns all the other spots the large creature is occupying
    main_pos = step

    # up
    up_pos = copy.copy(board_as_grid[str(step)])
    up_pos = [up_pos[0] + 1, up_pos[1]]
    up_pos = copy.copy(grid_as_board[str(up_pos)])

    # up right
    up_right_pos = copy.copy(board_as_grid[str(step)])
    up_right_pos = [up_right_pos[0] + 1, up_right_pos[1] + 1]
    up_right_pos = copy.copy(grid_as_board[str(up_right_pos)])

    # right pos
    right_pos = copy.copy(board_as_grid[str(step)])
    right_pos = [right_pos[0], right_pos[1] + 1]
    right_pos = copy.copy(grid_as_board[str(right_pos)])
    return [main_pos, up_pos, up_right_pos, right_pos]


def is_legal_target(valid_targets=['enemy'], active_pos=2, target_pos=10, action_range=1):
    distance_to_active, path = distance_between_squares(active_pos,
                                                             target_pos)

    active_speed = 6

    can_move = True

    enough_range = False
    # Enough range, dont need the move. Legal
    if distance_to_active <= action_range:
        enough_range = True

    # action_range + active_speed
    range_and_speed = action_range + active_speed
    if distance_to_active <= range_and_speed and can_move:
        enough_range = True

    if not enough_range:
        return False

    for target in valid_targets:
        return True

    # Got here, so the target is not valid. Return False
    return False

def in_reach_of_characters(self, target_pos):
    in_reach_of = []
    surrounding_positions = surrounding_pos(target_pos)
    for pos in surrounding_positions:
        if board_content[pos].char:
            in_reach_of.append(pos)
    return in_reach_of

    # Update on the character dictionary
    #character_list[board_content[active_character_position].char.char_id] = end_pos

#print(shortest_path(100, 353))

#print(distance_between_squares(268, 164))
#print(distance_between_squares(268, 144))
#print(distance_between_squares(200, 287))

#print(is_legal_target())

#print(shortest_path_dj(199, 0, 6))

"""
occupied = gather_large_positions(82)

for i in occupied[1:]:
    board_content[i].set_character(board_content[occupied[0]].get_character(), large_main=False)

print(gather_large_positions(229))
"""
"""
occupied = gather_large_positions(212)
sur_pos = []
# Gather all surrounding positions
for pos in occupied:
    sur_pos += surrounding_pos(pos, include_illegal_spots=True)

surrounding_index = [191, 192, 193, 194, 211, 214, 231, 234, 251, 252, 253, 254]

#print([sur_pos.index(j) for j in surrounding_index])

for i in [2, 1, 0, 24, 3, 16, 4, 23, 12, 13, 14, 22]:
    print(sur_pos[i])

Corners1 = [[0, 11], [3, 8], [4, 5], [6, 7], [4, 7], [6, 5], [1, 9], [1, 10], [2, 9], [2, 10]]


corners = [0, 4], [2, 6], [3, 7], [1, 5]

print(surrounding_pos(212))
"""
in_reach_of = []
occupied = gather_large_positions(212)
melee_range = []
for pos in occupied:
    melee_range += in_reach_of_characters(pos)
melee_range = list(np.unique(melee_range))

print(melee_range)
# Remove occupied spots
for pos in occupied:
    del melee_range[melee_range.index(pos)]