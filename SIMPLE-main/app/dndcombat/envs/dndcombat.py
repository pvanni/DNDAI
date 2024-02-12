import gym
import numpy as np
import random
import math
import config
import copy

from stable_baselines import logger

from .classes import *


class DndCombatEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, verbose=False, manual=False):
        super(DndCombatEnv, self).__init__()
        self.name = 'dndcombat'
        self.n_players = 2
        self.manual = manual

        # Configure the size of the battlemap
        self.board_size = 20
        self.n_squares = self.board_size * self.board_size

        # Generate the board as a grid
        self.board_as_grid = {}
        self.grid_as_board = {}
        for i in range(self.n_squares):
            self.board_as_grid[str(i)] = [math.floor(i / 20), i % 20]
            self.grid_as_board[str([math.floor(i / 20), i % 20])] = i

        self.character_list = {}

        self.action_space = gym.spaces.Discrete(166)
        self.observation_space = gym.spaces.Box(0, 1, (130
                                                       + how_many_monsters(return_count=True) + self.action_space.n,))
        self.verbose = verbose

    def set_contents(self):
        self.board_content = []
        team1_positions = []
        team2_positions = []
        char_id1_iter = iter([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        char_id2_iter = iter([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])

        team1_composition = iter(['BrownBear', 'AnimatedArmor', 'Bugbear', 'DireWolf', 'Chuul'])
        team2_composition = iter(['BrownBear', 'AnimatedArmor', 'Bugbear', 'DireWolf', 'Chuul'])

        for i in range(self.n_squares):
            self.board_content.append(Square(position=i, is_terrain=False, character=False, env_effects=False))

        for j in range(5):
            team1_positions.append(self.spawn_char(monster_name=next(team1_composition), char_id=next(char_id1_iter),
                                                   controlling_player=0))
            team2_positions.append(self.spawn_char(monster_name=next(team2_composition), char_id=next(char_id2_iter),
                                                   controlling_player=1))

        starting_positions = team1_positions + team2_positions

        team1_names = []
        for pos in team1_positions:
            team1_names.append(self.board_content[pos].char.monster_name)

        team2_names = []
        for pos in team2_positions:
            team2_names.append(self.board_content[pos].char.monster_name)

        # Print team positions and char names.
        logger.debug(f'team1_positions = {team1_positions}')
        logger.debug(f'team2_positions = {team2_positions}')
        logger.debug(f'team1_names = {team1_names}')
        logger.debug(f'team2_names = {team2_names}')





        # Set the highest initiative character to be the active character
        highest_initiative = -100
        first_square = 0
        for i in starting_positions:
            if self.board_content[i].char.initiative > highest_initiative:
                highest_initiative = self.board_content[i].char.initiative
                first_square = i

        self.active_character_position = first_square
        self.current_player_num = self.board_content[first_square].char.controlling_player

    def spawn_char(self, monster_name, controlling_player, char_id, spawn_pos='random'):
        """Spawn the monster in a random location that is available
        returns the starting location of the monster"""
        spawned = False
        position = False
        monster_function = how_many_monsters(return_count=False, monster_name=monster_name)[1]
        monster = monster_function(char_id=char_id, controlling_player=controlling_player)
        if monster.size == 'large':
            while not spawned:
                random_spot = random.randint(0, 399)
                occupied = self.gather_large_positions(random_spot)
                found_spot = 0
                if occupied:
                    for pos in occupied:
                        if not self.board_content[pos].char:
                            found_spot += 1
                        else:
                            break
                if found_spot == 4:
                    monster.set_position(occupied[0])
                    self.character_list[monster.char_id] = monster.pos
                    self.board_content[occupied[0]].set_character(monster, large_main=True)
                    for pos in occupied[1:]:
                        self.board_content[pos].set_character(monster, large_main=False)
                    position = monster.pos
                    spawned = True
        else:
            while not spawned:
                random_spot = random.randint(0, 399)
                if not self.board_content[random_spot].char:
                    monster.set_position(random_spot)
                    self.character_list[monster.char_id] = monster.pos
                    self.board_content[random_spot].set_character(monster)
                    position = monster.pos
                    spawned = True
        return position

    def distance_between_squares(self, start_position, end_position):
        # Helper function to calculate ranges and moves in the battlemap
        # x = vertical, y = horizontal
        start_xy = copy.copy(self.board_as_grid[str(start_position)])
        end_xy = copy.copy(self.board_as_grid[str(end_position)])

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
            path.append(copy.copy(self.grid_as_board[str(current_xy)]))
            n_steps += 1

        return n_steps, path

    def is_path_viable(self, path):

        # For large sized
        if self.board_content[self.active_character_position].char.size == 'large':
            if path:
                occupied = self.gather_large_positions(path[-1])
                # Out of bounds of the map
                if not occupied:
                    return False
                for pos in occupied:
                    if self.board_content[pos].char:
                        if self.board_content[pos].char != self.board_content[self.active_character_position].char:
                            return False
            large_occupied = []
            for step in path:
                large_occupied.append(self.gather_large_positions(step))
            path = large_occupied

            for step in path:
                # Out of bounds of the map
                if not step:
                    return False
                for pos in step:
                    if self.board_content[pos].is_terrain:
                        return False
                    if self.board_content[pos].char:
                        if self.board_content[pos].char.controlling_player != self.current_player_num:
                            return False
        # For medium and small sized
        else:
            if path:
                if self.board_content[path[-1]].char:
                    return False
            for step in path:
                if self.board_content[step].is_terrain:
                    return False
                if self.board_content[step].char:
                    if self.board_content[step].char.controlling_player != self.current_player_num:
                        return False
        return True

    def surrounding_pos(self, target_pos, include_illegal_spots=False):
        latest_pos = copy.copy(self.board_as_grid[str(target_pos)])
        surrounding_pos = []
        for i, j in zip([1, 1, 1, 0, -1, -1, -1, 0], [-1, 0, 1, 1, 1, 0, -1, -1]):
            # Check surrounding steps
            x = latest_pos[0] - i
            y = latest_pos[1] - j
            # logger.debug([x, y])
            if 20 > x >= 0 and 20 > y >= 0:
                step_in_board = copy.copy(self.grid_as_board[str([x, y])])
                surrounding_pos.append(step_in_board)
            else:
                if include_illegal_spots:
                    surrounding_pos.append(False)
        return surrounding_pos

    def gather_large_positions(self, step):
        # Takes the one spot and returns all the other spots the large creature is occupying
        main_pos = step

        try:
            # up
            up_pos = copy.copy(self.board_as_grid[str(step)])
            up_pos = [up_pos[0] + 1, up_pos[1]]
            up_pos = copy.copy(self.grid_as_board[str(up_pos)])

            # up right
            up_right_pos = copy.copy(self.board_as_grid[str(step)])
            up_right_pos = [up_right_pos[0] + 1, up_right_pos[1] + 1]
            up_right_pos = copy.copy(self.grid_as_board[str(up_right_pos)])

            # right pos
            right_pos = copy.copy(self.board_as_grid[str(step)])
            right_pos = [right_pos[0], right_pos[1] + 1]
            right_pos = copy.copy(self.grid_as_board[str(right_pos)])

            return [main_pos, up_pos, up_right_pos, right_pos]

        except KeyError as e:
            #logger.debug(e)
            return False

    def move_active(self, path):
        # Move to each step and trigger potential reactions or terrain effects
        size = 'medium'
        large = False
        if self.board_content[self.active_character_position].char.size == 'large':
            size = 'large'
            large = True

        previous_in_reach_of = self.in_reach_of_characters(self.active_character_position, size=size)
        previous_step = self.active_character_position

        for step in path:
            # Gather all characters who are in reach
            in_reach_of = self.in_reach_of_characters(step, size=size)

            for char_pos in previous_in_reach_of:

                char_ccd = False
                if self.board_content[char_pos].char.spell_data_list:
                    for spell_data in self.board_content[char_pos].char.spell_data_list:
                        if spell_data['effect'] == 'skip_turn':
                            char_ccd = True
                # If active character left the reach of a hostile character
                if char_pos not in in_reach_of \
                        and self.board_content[char_pos].char.controlling_player != self.current_player_num \
                        and self.board_content[char_pos].char.reaction_available and not char_ccd:

                    logger.debug('Attack of opportunity triggered')

                    # Attack of opportunity
                    to_hit, damage, disa_or_adv, on_hit_effect, dmg_type = self.board_content[char_pos].char.attack_action1(distance=1)
                    self.board_content[char_pos].char.reset_actions()
                    self.board_content[char_pos].char.spend_reaction()
                    damage = self.board_content[self.active_character_position].char.did_attack_hit(damage, to_hit, disa_or_adv, distance=1)
                    if not isinstance(damage, bool):
                        self.char_take_damage(char_pos, self.active_character_position, damage, on_hit_effect, dmg_type)
                        # active character died. End turn
                        if not self.board_content[self.active_character_position].char:
                            return False

        # Move to new spot
        self.change_pos_active_character_on_board(path[-1], len(path), large=large)
        return True

    def change_pos_active_character_on_board(self, end_pos, distance_moved, large):

        # Move to new pos
        self.board_content[end_pos].set_character(self.board_content[self.active_character_position].get_character(), large_main=large)
        self.board_content[end_pos].char.reduce_speed(distance_moved)
        self.board_content[self.active_character_position].remove_char()

        # Remove old characters space
        if large:
            occupied_space = self.gather_large_positions(self.active_character_position)
            for pos in occupied_space[1:]:
                if not self.board_content[pos].char_main_pos:
                    self.board_content[pos].remove_char()

        # Update the active character pos
        self.active_character_position = end_pos

        # Set the new large characters occupied space
        if large:
            occupied_space = self.gather_large_positions(end_pos)
            for pos in occupied_space[1:]:
                self.board_content[pos].set_character(self.board_content[self.active_character_position].get_character(), large_main=False)

        try:
            # Update on the character dictionary
            self.character_list[self.board_content[self.active_character_position].char.char_id] = end_pos
        except:
            raise Exception(self.character_list, self.active_character_position, end_pos)

    def in_reach_of_characters(self, target_pos, size):
        # Enemy in reach
        if size == 'large':
            in_reach_of = []
            occupied = self.gather_large_positions(target_pos)
            melee_range = []
            for pos in occupied:
                melee_range += self.in_reach_of_characters(pos, size='medium')
            melee_range = list(np.unique(melee_range))

            # Remove occupied spots
            for pos in occupied:
                if pos in melee_range:
                    del melee_range[melee_range.index(pos)]

            for char in melee_range:
                if self.board_content[char].char:
                    in_reach_of.append(char)
            return in_reach_of
        else:
            in_reach_of = []
            surrounding_positions = self.surrounding_pos(target_pos)
            for pos in surrounding_positions:
                if self.board_content[pos].char:
                    in_reach_of.append(pos)
            return in_reach_of

    @property
    def observation(self):

        # Create the observation space
        final_obs = np.zeros(0)

        legal_actions = self.legal_actions

        # Distance to characters
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                char_pos = self.character_list[char_id]
                # If target is large
                if self.board_content[char_pos].char.size == 'large':
                    closest_pos = self.check_closest_pos_on_large(char_pos)
                    distance, path = self.distance_between_squares(self.active_character_position, closest_pos)
                else:
                    distance, path = self.distance_between_squares(self.active_character_position, char_pos)

                # If the active is large. Check if the other occupied spots are closer
                if self.board_content[self.active_character_position].char.size == 'large':
                    occupied = self.gather_large_positions(self.active_character_position)
                    for pos in occupied:
                        pos_distance, _ = self.distance_between_squares(pos, char_pos)
                        if pos_distance < distance:
                            distance -= 1

                obs[char_id] = distance / 20

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)

        # How much dmg received.
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                try:
                    char_pos = self.character_list[char_id]
                    obs[char_id] = self.board_content[char_pos].char.damage_received / 200
                except:
                    raise Exception(self.character_list, char_id)

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)

        # How much dmg done.
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                char_pos = self.character_list[char_id]
                obs[char_id] = self.board_content[char_pos].char.damage_done / 200

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)

        # Is char concentrating
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                char_pos = self.character_list[char_id]
                if self.board_content[char_pos].char.concentrating:
                    obs[char_id] = 1

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)


        # Round number
        final_obs = np.append(final_obs, [self.round_number / 100])

        # Speed left
        final_obs = np.append(final_obs, [self.board_content[self.active_character_position].char.max_move_distance() / 19])

        # Enemy in reach
        melee_range = self.in_reach_of_characters(self.active_character_position,
                                                  size=self.board_content[self.active_character_position].char.size)
        obs = [0]
        for char in melee_range:
            if self.board_content[char].char.controlling_player != self.current_player_num:
                obs = [1]
                break
            else:
                obs = [0]

        # Action available
        if self.board_content[self.active_character_position].char.actions_available > 0:
            final_obs = np.append(final_obs, [1])
        else:
            final_obs = np.append(final_obs, [0])

        # Bonus available
        if self.board_content[self.active_character_position].char.bonus_action_available > 0:
            final_obs = np.append(final_obs, [1])
        else:
            final_obs = np.append(final_obs, [0])

        final_obs = np.append(final_obs, obs)

        # character CR
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                char_pos = self.character_list[char_id]
                obs[char_id] = self.board_content[char_pos].char.cr / 5000

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)

        # Does char have debuffs that make it easier to hit?
        obs = np.zeros(20)
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                char_pos = self.character_list[char_id]
                for spell in self.board_content[char_pos].char.spell_data_list:
                    for modifier in spell['hit_modifier']:
                        if modifier in ['advantage_to_hit', 'melee_automatic_critical', 'melee_advantage_to_hit']:
                            obs[char_id] = 1

        if self.current_player_num == 0:
            # Swap enemies to first position
            obs = np.append(obs[10:], obs[:10])
        final_obs = np.append(final_obs, obs)

        # Am I prone?
        is_prone = [0]
        for spell_data in self.board_content[self.active_character_position].char.spell_data_list:
            if 'prone' == spell_data['effect']:
                is_prone = [1]
        final_obs = np.append(final_obs, is_prone)

        # Am I prone?
        is_grappled = [0]
        for spell_data in self.board_content[self.active_character_position].char.spell_data_list:
            if 'grappled' == spell_data['effect'] and \
                    spell_data['caster'] != self.board_content[self.active_character_position].char.char_id:
                is_grappled = [1]
        final_obs = np.append(final_obs, is_grappled)

        # Enemies left
        if self.current_player_num == 0:
            final_obs = np.append(final_obs, [self.team2_remaining / 10])
        else:
            final_obs = np.append(final_obs, [self.team1_remaining / 10])

        # Allies left
        if self.current_player_num == 0:
            final_obs = np.append(final_obs, [self.team1_remaining / 10])
        else:
            final_obs = np.append(final_obs, [self.team2_remaining / 10])

        # Can use attack or spell on a target?
        valid_targets = [0]
        for i in range(80, 160):
            if legal_actions[i] == 1:
                valid_targets = [1]
                break
        final_obs = np.append(final_obs, valid_targets)

        # Monster type
        obs = np.zeros(how_many_monsters(return_count=True))
        for i in range(how_many_monsters(return_count=True)):
            monster_name = self.board_content[self.active_character_position].char.monster_name
            if i == how_many_monsters(return_count=False, monster_name=monster_name)[0]:
                obs[i] = 1
            else:
                obs[i] = 0

        final_obs = np.append(final_obs, obs)

        final_obs = np.append(final_obs, legal_actions)

        return final_obs

    def char_is_dead(self, char_id):
        if self.character_list[char_id] == 'Dead':
            return True
        else:
            return False

    def side_step_cells(self, pos, next_pos, target_spot, left_or_right):
        # Determine the direction
        surrounding_positions = self.surrounding_pos(pos, include_illegal_spots=True)
        direction = 0
        for sur_pos in surrounding_positions:
            if sur_pos == next_pos:
                break
            else:
                direction += 1

        if left_or_right == 'left':
            # Examine positions 1-3 for possible spots
            for i in range(1, 4):
                if not surrounding_positions[i]:
                    continue
                distance, _ = self.distance_between_squares(surrounding_positions[i], target_spot)
                towards_distance, _ = self.distance_between_squares(pos, target_spot)
                if distance == towards_distance:
                    return surrounding_positions[i]
            return False
        elif left_or_right == 'right':
            # Examine 5-7 for possible spots
            for i in range(5, 8):
                if not surrounding_positions[i]:
                    continue
                distance, _ = self.distance_between_squares(surrounding_positions[i], target_spot)
                towards_distance, _ = self.distance_between_squares(pos, target_spot)
                if distance == towards_distance:
                    return surrounding_positions[i]
            return False
        elif left_or_right == 'back':
            if surrounding_positions[4]:
                return surrounding_positions[4]
            else:
                return False

    def is_flanked(self, attacker_pos_input, target_pos):
        # Determine if the attacked char is flanked
        attacker_pos_list = [attacker_pos_input]
        if self.board_content[attacker_pos_input].char.size == 'large':
            attacker_pos_list = self.gather_large_positions(self.character_list[self.board_content[attacker_pos_input].char.char_id])
        for attacker_pos in attacker_pos_list:
            if self.board_content[target_pos].char.size == 'large':
                occupied = self.gather_large_positions(self.character_list[self.board_content[target_pos].char.char_id])
                sur_pos = []
                # Gather all surrounding positions
                for pos in occupied:
                    sur_pos += self.surrounding_pos(pos, include_illegal_spots=True)

                # Index for all the surrounding positions on a large char
                sur_i = [2, 1, 0, 24, 3, 16, 4, 23, 12, 13, 14, 22]
                sur_pos = np.take(sur_pos, sur_i)

                flanking_pairs = [[0, 11], [3, 8], [4, 5], [6, 7], [4, 7], [6, 5], [1, 9], [1, 10], [2, 9], [2, 10]]
                for pair in flanking_pairs:
                    pair_in_pos = [sur_pos[pair[0]], sur_pos[pair[1]]]
                    if self.board_content[pair_in_pos[0]].char and self.board_content[pair_in_pos[1]].char:
                        if self.board_content[pair_in_pos[0]].char.controlling_player == self.current_player_num \
                                and self.board_content[pair_in_pos[1]].char.controlling_player == self.current_player_num:
                            if attacker_pos in pair_in_pos:
                                return True
                #return False
            else:
                sur_pos = self.surrounding_pos(target_pos, include_illegal_spots=True)
                flanking_pairs = [[0, 4], [2, 6], [3, 7], [1, 5]]
                for pair in flanking_pairs:
                    pair_in_pos = [sur_pos[pair[0]], sur_pos[pair[1]]]
                    if self.board_content[pair_in_pos[0]].char and self.board_content[pair_in_pos[1]].char:
                        if self.board_content[pair_in_pos[0]].char.controlling_player == self.current_player_num \
                                and self.board_content[pair_in_pos[1]].char.controlling_player == self.current_player_num:
                            if attacker_pos in pair_in_pos:
                                return True
                #return False
        return False

    @property
    def legal_actions(self):

        #legal_actions = np.zeros(self.action_space.n)

        legal_actions = np.zeros(0)

        active_square = self.board_content[self.active_character_position]

        # active character is cc'd. Everything else but end turn is invalid
        if active_square.char.spell_data_list:
            for spell in active_square.char.spell_data_list:
                if spell['effect'] == 'skip_turn':
                    #logger.debug('CCd. Only end turn is legal')
                    legal_actions = np.zeros(self.action_space.n)
                    legal_actions[-1] = 1
                    return legal_actions

        # Side step left
        actions = np.zeros(20)
        n_legal = 0
        for char_id in self.character_list:
            char_pos = self.character_list[char_id]

            # Cant move closer to self
            if char_pos == self.active_character_position or self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                speed_left = self.board_content[self.active_character_position].char.max_move_distance()

                distance, path = self.distance_between_squares(self.active_character_position, char_pos)

                if distance < 1:
                    actions[char_id] = 0
                else:
                    side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='left',
                                                         target_spot=char_pos)
                    if side_step_pos:
                        if self.is_path_viable([side_step_pos]):
                            if speed_left == 0 or self.board_content[side_step_pos].char:
                                actions[char_id] = 0
                            else:
                                n_legal += 1
                                actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        # Side step right
        actions = np.zeros(20)
        for char_id in self.character_list:
            char_pos = self.character_list[char_id]

            # Cant move closer to self
            if char_pos == self.active_character_position or self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                speed_left = self.board_content[self.active_character_position].char.max_move_distance()

                distance, path = self.distance_between_squares(self.active_character_position, char_pos)

                if distance < 1:
                    actions[char_id] = 0
                else:
                    side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='right',
                                                         target_spot=char_pos)
                    if side_step_pos:
                        if self.is_path_viable([side_step_pos]):
                            if speed_left == 0 or self.board_content[side_step_pos].char:
                                actions[char_id] = 0
                            else:
                                actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        # move away from target
        actions = np.zeros(20)
        for char_id in self.character_list:
            char_pos = self.character_list[char_id]

            # Cant move closer to self
            if char_pos == self.active_character_position or self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                speed_left = self.board_content[self.active_character_position].char.max_move_distance()

                distance, path = self.distance_between_squares(self.active_character_position, char_pos)

                if distance < 1:
                    actions[char_id] = 0
                else:
                    side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='back',
                                                         target_spot=char_pos)
                    if side_step_pos:
                        if self.is_path_viable([side_step_pos]):
                            if speed_left == 0 or self.board_content[side_step_pos].char:
                                actions[char_id] = 0
                            else:
                                actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)


        # move closer character
        actions = np.zeros(20)
        n_legal = 0
        for char_id in self.character_list:
            char_pos = self.character_list[char_id]

            # Cant move closer to self
            if char_pos == self.active_character_position or self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                speed_left = self.board_content[self.active_character_position].char.max_move_distance()
                distance, path = self.distance_between_squares(self.active_character_position, char_pos)

                if distance <= 1:
                    actions[char_id] = 0
                else:

                    if self.is_path_viable(path[:1]):
                        if speed_left == 0 or self.board_content[path[0]].char:
                            actions[char_id] = 0
                        else:
                            n_legal += 1
                            actions[char_id] = 1

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        #logger.debug(f'Legal moves towards {n_legal}')

        # Attack1
        actions = np.zeros(20)
        n_legal = 0
        for char_id in self.character_list:

            char_pos = self.character_list[char_id]
            # Character dead. Add a zero
            if self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                # Does not have this action
                is_legal = active_square.char.attack_action1(check=True)

                if not is_legal:
                    actions[char_id] = 0
                else:
                    # Determine if its out of range
                    if self.is_legal_target(valid_targets=is_legal,
                                            active_pos=active_square.position,
                                            target_pos=char_pos,
                                            action_range=active_square.char.attack_action1_range):
                        n_legal += 1
                        actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        #logger.debug(f'Attacks legal: {n_legal}')

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)
        # Attack2
        actions = np.zeros(20)
        n_legal = 0
        for char_id in self.character_list:

            char_pos = self.character_list[char_id]
            # Character dead. Add a zero
            if self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                # Does not have this action
                is_legal = active_square.char.attack_action2(check=True)

                if not is_legal:
                    actions[char_id] = 0
                else:
                    # Determine if its out of range
                    if self.is_legal_target(valid_targets=is_legal,
                                            active_pos=active_square.position,
                                            target_pos=char_pos,
                                            action_range=active_square.char.attack_action2_range):
                        actions[char_id] = 1
                        n_legal += 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        # Targeted Spell 1
        actions = np.zeros(20)

        for char_id in self.character_list:

            char_pos = self.character_list[char_id]
            # Character dead. Add a zero
            if self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                # Does not have this action
                is_legal = active_square.char.spell_action1(check=True)

                if not is_legal:
                    actions[char_id] = 0
                else:
                    # Determine if its out of range
                    current_square = self.board_content[char_pos]
                    if self.is_legal_target(valid_targets=is_legal,
                                            active_pos=active_square.position,
                                            target_pos=char_pos,
                                            action_range=active_square.char.spell_action1_range):
                        actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        # Targeted Spell 2
        actions = np.zeros(20)

        for char_id in self.character_list:

            char_pos = self.character_list[char_id]
            # Character dead. Add a zero
            if self.char_is_dead(char_id):
                actions[char_id] = 0
            else:

                # Does not have this action
                is_legal = active_square.char.spell_action2(check=True)

                if not is_legal:
                    actions[char_id] = 0
                else:
                    # Determine if its out of range
                    current_square = self.board_content[char_pos]
                    if self.is_legal_target(valid_targets=is_legal,
                                            active_pos=active_square.position,
                                            target_pos=char_pos,
                                            action_range=active_square.char.spell_action2_range):
                        actions[char_id] = 1
                    else:
                        actions[char_id] = 0

        if self.current_player_num == 0:
            # Swap enemies to first position
            actions = np.append(actions[10:], actions[:10])
        legal_actions = np.append(legal_actions, actions)

        # Ability 1
        if not active_square.char.special_ability1(check=True):
            legal_actions = np.append(legal_actions, [0])

        # Ability 2
        if not active_square.char.special_ability2(check=True):
            legal_actions = np.append(legal_actions, [0])

        grapple_legal = [0]
        # Remove grapple or other conditions with an action
        if active_square.char.actions_available >= 1:
            for spell_data in active_square.char.spell_data_list:
                if 'grappled' == spell_data['effect']:
                    if spell_data['caster'] != active_square.char.char_id:
                        grapple_legal = [1]
        legal_actions = np.append(legal_actions, grapple_legal)

        # Stand up from prone
        stand_up_legal = [0]
        if active_square.char.speed_left >= math.floor(active_square.char.speed / 2):
            for spell_data in active_square.char.spell_data_list:
                if 'prone' == spell_data['effect']:
                    #logger.debug('Stand up is legal')
                    stand_up_legal = [1]
                    break

        legal_actions = np.append(legal_actions, stand_up_legal)

        # Dodge
        if active_square.char.dodge(check=True):
            legal_actions = np.append(legal_actions, [1])
        else:
            legal_actions = np.append(legal_actions, [0])

        # End turn is always legal
        legal_actions = np.append(legal_actions, [1])

        return legal_actions

    def is_legal_target(self, valid_targets, active_pos, target_pos, action_range):

        distance_to_active, path = self.distance_between_squares(active_pos, target_pos)

        # If one of the occupied spots of a large character is closer than the main spot.
        # Reduce path by one and distance by one
        if self.board_content[self.active_character_position].char.size == 'large':
            occupied = self.gather_large_positions(self.active_character_position)
            for pos in occupied:
                pos_distance, _ = self.distance_between_squares(pos, target_pos)
                if pos_distance < distance_to_active:
                    distance_to_active -= 1
                    path = path[:-1]

        # If target is large, determine if a closer position is already a viable spot
        if self.board_content[target_pos].char.size == 'large':
            occupied = self.gather_large_positions(target_pos)
            for pos in occupied:
                pos_distance, pos_path = self.distance_between_squares(self.active_character_position, pos)
                if pos_distance < distance_to_active:
                    target_pos = pos
                    path = pos_path
                    distance_to_active = pos_distance
                    break

        active_speed = self.board_content[active_pos].char.max_move_distance()

        if distance_to_active > active_speed:
            can_move = self.is_path_viable(path[:active_speed])
        else:
            can_move = self.is_path_viable(path[:-1])

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
            if target == 'any':
                return True
            elif self.board_content[target_pos].char:
                if target == 'enemy' and self.current_player_num != self.board_content[target_pos].char.controlling_player:
                    if 'grappled_by' in valid_targets:
                        for spell_data in self.board_content[target_pos].char.spell_data_list:
                            if spell_data['effect'] == 'grappled' and spell_data['caster'] == \
                                    self.board_content[active_pos].char.char_id:
                                return True
                    else:
                        return True
                elif target == 'friendly' and self.current_player_num == self.board_content[target_pos].char.controlling_player:
                    return True
                elif target == 'friendly_healing' and self.current_player_num == self.board_content[target_pos].char.controlling_player:
                    if self.board_content[target_pos].char.start_hp != self.board_content[target_pos].char.hp:
                        return True
                else:
                    return False
            else:
                return False

    def move_closer_to_target(self, active_pos, attack_pos, attack_range):
        # Returns true or false depending on if the character is alive after the move.
        # First value is means if the active moved to attack, second is if he survived

        distance, path = self.distance_between_squares(active_pos, attack_pos)


        # If one of the occupied spots of a large character is closer than the main spot.
        # Reduce path by one and distance by one
        if self.board_content[self.active_character_position].char.size == 'large':
            occupied = self.gather_large_positions(self.active_character_position)
            for pos in occupied:
                pos_distance, _ = self.distance_between_squares(pos, attack_pos)
                if pos_distance < distance:
                    distance -= 1
                    path = path[:-1]

        if distance <= attack_range:
            return False, True

        speed_left = self.board_content[active_pos].char.max_move_distance()

        # If distance is shorter than the move left
        if speed_left >= distance:
            # Debug info
            logger.debug(f'Moving closer to {attack_pos} into {path[:-1][-1]}')
            if not self.is_path_viable(path[:-1]):
                raise Exception(f'Error1 {path[:-1]}')

            return True, self.move_active(path[:-1])

        # Debug info
        logger.debug(f'Moving closer to {attack_pos} into {path[speed_left - 1]}')

        if not self.is_path_viable(path[:speed_left]):
            raise Exception('Error2', path[:speed_left])
        return True, self.move_active(path[:speed_left])

    def check_closest_pos_on_large(self, target_pos):
        # If target is large, determine if a closer position is already a viable spot
        if self.board_content[target_pos].char.size == 'large':
            occupied = self.gather_large_positions(target_pos)
            closest_distance = 99
            closest_pos = False
            for pos in occupied:
                pos_distance, pos_path = self.distance_between_squares(self.active_character_position, pos)
                if pos_distance < closest_distance:
                    closest_distance = pos_distance
                    closest_pos = pos
            #logger.debug(closest_pos)
            return closest_pos
        else:
            return False

    def flip_char_positions(self, action, constant):
        """Makes it so that in each action type the 1-10 spots are always enemies and 11-20 are always friends"""
        if self.current_player_num == 0:
            if action - constant < 10:
                pos = self.character_list[action - constant + 10]
            else:
                pos = self.character_list[action - constant - 10]
        else:
            pos = self.character_list[action - constant]

        return pos

    def stack_dis_and_adv(self, disa_or_adv, addition):
        if disa_or_adv == 'advantage':
            if addition == 'advantage':
                return disa_or_adv

        elif disa_or_adv == 'disadvantage':
            if addition == 'advantage':
                return False

        elif disa_or_adv == addition:
            return disa_or_adv

        # return the addition
        return addition

    def resolve_abilities(self, disa_or_adv, damage, attacker, attack_pos):

        for spell_data in self.board_content[attacker].char.spell_data_list:
            if spell_data['resolve_time'] == 'attack_buff':
                if spell_data['effect'] == 'advantage_when_ally_near_target':
                    # check neighbors and add distance
                    main_position = self.character_list[self.board_content[attack_pos].char.char_id]
                    melee_range = self.in_reach_of_characters(main_position,
                                                              size=self.board_content[attack_pos].char.size)
                    for char in melee_range:
                        if self.board_content[char].char.controlling_player == self.board_content[attacker].char.controlling_player:
                            logger.debug('Ability triggered. Advantage on attack')
                            disa_or_adv = self.stack_dis_and_adv(disa_or_adv, 'advantage')
            if spell_data['effect'] == 'prone':
                logger.debug('Prone. Disadvantage to hit')
                disa_or_adv = self.stack_dis_and_adv(disa_or_adv, 'disadvantage')
        return disa_or_adv, damage

    def physical_attack(self, action, action_constant, attack_method, active_attack_range, attack_name):
        """ Executes the main attacks of creatures,
        for example Ogre greatclub attacks. Spells have their own function"""
        attack_pos = self.flip_char_positions(action, action_constant)

        # If attacking a large character, then check if any of his spaces are closer that the main space
        large_closest = self.check_closest_pos_on_large(attack_pos)
        if large_closest:
            attack_pos = large_closest

        # Debug information
        logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                     f'{self.board_content[self.active_character_position].char.monster_name} attacked '
                     f'with {attack_name} from {self.active_character_position} to {attack_pos}')

        # Move closer if not at attack range. If he died then change turns
        moved, is_alive = self.move_closer_to_target(self.active_character_position, attack_pos, active_attack_range)

        if not is_alive:
            return "change character"

        # check neighbors and add distance
        melee_range = self.in_reach_of_characters(self.active_character_position,
                                                  size=self.board_content[self.active_character_position].char.size)
        distance_to_closest_enemy = False
        for char in melee_range:
            if self.board_content[char].char.controlling_player != self.current_player_num:
                distance_to_closest_enemy = 1
                break

        # Distance to target
        distance_to_target, _ = self.distance_between_squares(self.active_character_position, attack_pos)

        # If the attacker is large, check if the other spots are closer
        if self.board_content[self.active_character_position].char.size == 'large':
            occupied = self.gather_large_positions(self.active_character_position)
            for pos in occupied:
                pos_distance, _ = self.distance_between_squares(pos, attack_pos)
                if pos_distance < distance_to_target:
                    distance_to_target = pos_distance

        to_hit, damage, disa_or_adv, on_hit_effect, dmg_type = attack_method(action_id=self.current_action_id,
                                                                             distance=distance_to_closest_enemy)

        # Calculate flanked status if range indicates the weapon is a melee
        if active_attack_range == 1:
            if self.is_flanked(attacker_pos_input=self.active_character_position, target_pos=attack_pos):
                logger.debug('Flanked')
                disa_or_adv = 'advantage'

        # look for buffs affect the dmg or advantage/disadvantage situation on the attack
        disa_or_adv, damage = self.resolve_abilities(disa_or_adv, damage, self.active_character_position, attack_pos)

        damage = self.board_content[attack_pos].char.did_attack_hit(damage, to_hit, disa_or_adv, distance_to_target)
        if not isinstance(damage, bool):
            self.char_take_damage(self.active_character_position, attack_pos, damage, on_hit_effect, dmg_type)

    def execute_action(self, action):

        # Report on the status of the character
        for spell_data in self.board_content[self.active_character_position].char.spell_data_list:
            if spell_data['effect'] == 'prone':
                logger.debug(f'Is prone')
            if spell_data['effect'] == 'grappled':
                logger.debug(f'Is grappled')
        logger.debug(self.board_content[self.active_character_position].char.spell_data_list)
        logger.debug(f'Can move upto: {self.board_content[self.active_character_position].char.max_move_distance()}')

        # Action id
        self.current_action_id += 1
        action_reward = 0

        # activate start of turn effects. No skip turn effects available
        if self.board_content[self.active_character_position].char.is_first_action:
            self.start_of_turn_effects(self.active_character_position)
            self.board_content[self.active_character_position].char.first_action()

        # Print the distance to closest enemy #107
        for char_id in self.character_list:
            if not self.char_is_dead(char_id):
                if self.board_content[self.character_list[char_id]].char.controlling_player != self.current_player_num:
                    logger.debug(f'Enemy: {self.character_list[char_id]}')
                else:
                    logger.debug(f'Ally: {self.character_list[char_id]}')

        # side step left in relation to target
        if 0 <= action < 20:

            move_pos = self.flip_char_positions(action, 0)

            distance, path = self.distance_between_squares(self.active_character_position, move_pos)
            distance -= 1
            side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='left',
                                                 target_spot=move_pos)
            path = [side_step_pos]

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'moved from {self.active_character_position} to {path[0]}')

            if not self.is_path_viable(path):
                raise Exception(f'Error 3: {path} {path}')
            active_alive = self.move_active(path)

            if not active_alive:
                return "change character", action_reward

        # side step right in relation to target
        if 20 <= action < 40:

            move_pos = self.flip_char_positions(action, 20)

            distance, path = self.distance_between_squares(self.active_character_position, move_pos)
            distance -= 1
            side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='right',
                                                 target_spot=move_pos)
            path = [side_step_pos]

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'moved from {self.active_character_position} to {path[0]}')

            if not self.is_path_viable(path):
                raise Exception(f'Error 3: {path} {path}')
            active_alive = self.move_active(path)

            if not active_alive:
                return "change character", action_reward

        # move backwards in relation to target
        if 40 <= action < 60:

            move_pos = self.flip_char_positions(action, 40)

            distance, path = self.distance_between_squares(self.active_character_position, move_pos)
            distance -= 1
            side_step_pos = self.side_step_cells(self.active_character_position, path[0], left_or_right='back',
                                                 target_spot=move_pos)
            path = [side_step_pos]

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'moved from {self.active_character_position} to {path[0]}')

            if not self.is_path_viable(path):
                raise Exception(f'Error 3: {path} {path}')
            active_alive = self.move_active(path)

            if not active_alive:
                return "change character", action_reward

        # Move closer to character
        if 60 <= action < 80:

            move_pos = self.flip_char_positions(action, 60)

            distance, path = self.distance_between_squares(self.active_character_position, move_pos)
            distance -= 1
            path = path[:1]

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'moved from {self.active_character_position} to {path[0]}')

            if not self.is_path_viable(path):
                raise Exception(f'Error 3: {path} {path}')
            active_alive = self.move_active(path)

            if not active_alive:
                return "change character", action_reward

        # Attack1
        if 80 <= action < 100:

            change_char = self.physical_attack(action,
                                               80,
                                               self.board_content[self.active_character_position].char.attack_action1,
                                               self.board_content[self.active_character_position].char.attack_action1_range,
                                               self.board_content[self.active_character_position].char.attack1_name)
            if change_char == 'change character':
                return 'change character', action_reward

        # Attack2
        if 100 <= action < 120:

            #action_reward += 0.1

            change_char = self.physical_attack(action, 100,
                                               self.board_content[self.active_character_position].char.attack_action2,
                                               self.board_content[self.active_character_position].char.attack_action2_range,
                                               self.board_content[self.active_character_position].char.attack2_name)
            if change_char == 'change character':
                return 'change character', action_reward

        # Spell 1
        if 120 <= action < 140:

            #action_reward += 0.1


            attack_pos = self.flip_char_positions(action, 120)

            large_closest = self.check_closest_pos_on_large(attack_pos)
            if large_closest:
                attack_pos = large_closest

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'cast spell (1) from {self.active_character_position} to {attack_pos}')

            active_attack_range = self.board_content[self.active_character_position].char.spell_action1_range

            # Move closer if not at attack range. If he died then change turns
            moved, is_alive = self.move_closer_to_target(self.active_character_position, attack_pos,
                                                         active_attack_range)

            if not is_alive:
                return "change character", action_reward


            previous_spell_concentration = False
            if self.board_content[self.active_character_position].char.concentrating:
                previous_spell_concentration = self.board_content[self.active_character_position].char.concentrating

            spell_data = self.board_content[self.active_character_position].char.spell_action1(action_id=self.current_action_id)
            self.resolve_spell(attack_pos, spell_data)

            # Remove the previous spell from the board if spell requires concentration
            if spell_data['caster']:
                self.end_spell(previous_spell_concentration)

        # Spell 2
        if 140 <= action < 160:

            #action_reward += 0.1

            attack_pos = self.flip_char_positions(action, 140)

            large_closest = self.check_closest_pos_on_large(attack_pos)
            if large_closest:
                attack_pos = large_closest

            # Debug information
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'cast spell (2) from {self.active_character_position} to {attack_pos}')

            active_attack_range = self.board_content[self.active_character_position].char.spell_action2_range

            # Move closer if not at attack range. If he died then change turns
            moved, is_alive = self.move_closer_to_target(self.active_character_position, attack_pos,
                                                         active_attack_range)

            if not is_alive:
                return "change character", action_reward

            previous_spell_concentration = False
            if self.board_content[self.active_character_position].char.concentrating:
                previous_spell_concentration = self.board_content[self.active_character_position].char.concentrating

            spell_data = self.board_content[self.active_character_position].char.spell_action2(action_id=self.current_action_id)
            self.resolve_spell(attack_pos, spell_data)

            # Remove the previous spell from the board if spell requires concentration
            if spell_data['caster']:
                self.end_spell(previous_spell_concentration)

        # Special ability 1
        # 2000
        # Special ability 2
        # 2001. Should be unviable still

        # Remove grapple
        if action == 162:
            remove_spells = []
            for spell_data in self.board_content[self.active_character_position].char.spell_data_list:
                if 'grappled' == spell_data['effect'] and \
                        self.board_content[self.active_character_position].char.char_id != spell_data['caster']:
                    saving_throw = self.board_content[self.active_character_position].char.take_saving_throw(spell_data['save_type'])
                    if saving_throw >= spell_data['save_dc']:
                        logger.debug('Grapple succesfully removed')
                        remove_spells.append(spell_data['action_id'])
                    else:
                        logger.debug('Save against Grapple failed')

            # Remove the grapples
            for spell in remove_spells:
                self.board_content[self.active_character_position].char.remove_spell(spell)
                self.board_content[self.active_character_position].char.remove_speed_debuff()

        # stand up from prone
        if action == 163:
            logger.debug('Standing up from prone')
            remove_spells = []
            for spell_data in self.board_content[self.active_character_position].char.spell_data_list:
                if 'prone' == spell_data['effect']:
                    remove_spells.append(spell_data['action_id'])

            for spell in remove_spells:
                self.board_content[self.active_character_position].char.remove_spell(spell)
                self.board_content[self.active_character_position].char.reduce_speed(math.floor(
                    self.board_content[self.active_character_position].char.speed / 2))

        # Dodge
        if action == 164:

            self.board_content[self.active_character_position].char.dodge(self.current_action_id)
            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'dodging at {self.active_character_position}')

        # End turn
        if action == 165:

            logger.debug(f'Action {self.current_action_id}: Player {self.current_player_num} '
                         f'ended turn at {self.active_character_position} with '
                         f'{self.board_content[self.active_character_position].char.monster_name}')


            """
            # If the character did not use its action on its turn
            if not self.board_content[self.active_character_position].char.used_actions():
                if not self.was_ccd:
                    action_reward -= 1
            """
            if not self.board_content[self.active_character_position].char.used_actions():
                logger.debug('Did not use action')

            # activate end of turn spells
            self.end_of_turn_effects(self.active_character_position)

            self.board_content[self.active_character_position].char.reset_speed()
            self.board_content[self.active_character_position].char.reset_actions()
            self.board_content[self.active_character_position].char.end_turn()

            return "change character", action_reward
        else:
            return "keep going", action_reward

    def give_damage_reward(self, rewarded_player, damage, healing=False):
        # Give reward proportional to damage done. Enemy gain equal negative reward.
        # Healing gains bigger rewards than damage
        if not healing:
            max_reward_dmg = 15
            #self.step_reward[rewarded_player] += damage / max_reward_dmg
            #self.step_reward[1-rewarded_player] -= damage / max_reward_dmg
        else:
            max_reward_dmg = 4
            #self.step_reward[rewarded_player] += damage / max_reward_dmg

    def end_of_turn_effects(self, target_pos):
        # Check and resolve end of turn effects. Tick down timers.
        spell_data_list = self.board_content[target_pos].char.spell_data_list
        remove_spells = []
        reduce_spells = []
        if spell_data_list:
            # Check every spell effecting the character
            for i in range(len(spell_data_list)):
                # If the character have any effects that resolve at the end of turn
                if spell_data_list[i]['resolve_time'] == 'end_of_turn':
                    # Is it a spell that has a save
                    action_id = spell_data_list[i]['action_id']
                    save_type = spell_data_list[i]['save_type']
                    if save_type:
                        saving_throw = self.board_content[target_pos].char.take_saving_throw(save_type)
                        if saving_throw >= spell_data_list[i]['save_dc']:
                            # End the spell on target
                            logger.debug('Saved against spell. Ending effect')
                            remove_spells.append(action_id)
                        else:
                            # reduce duration of spell
                            logger.debug('Failed save against spell.')
                            reduce_spells.append(action_id)
                    else:
                        # reduce duration of spell
                        reduce_spells.append(action_id)

        for spell in remove_spells:
            self.board_content[target_pos].char.remove_spell(spell)
            self.check_concentration_needed(spell)

        for spell in reduce_spells:
            self.board_content[target_pos].char.reduce_spell_duration(spell)
            self.check_concentration_needed(spell)

    def start_of_turn_effects(self, target_pos):
        # Check and resolve start of turn effects. Tick down timers.
        self.board_content[target_pos].char.reset_reaction()
        spell_data_list = self.board_content[target_pos].char.spell_data_list
        remove_spells = []
        reduce_spells = []
        if spell_data_list:
            # Check every spell effecting the character
            for i in range(len(spell_data_list)):
                # If the character have any effects that resolve at the end of turn
                if spell_data_list[i]['resolve_time'] == 'start_of_turn':
                    # Is it a spell that has a save
                    action_id = spell_data_list[i]['action_id']
                    save_type = spell_data_list[i]['save_type']
                    if save_type:
                        saving_throw = self.board_content[target_pos].char.take_saving_throw(save_type)
                        if saving_throw >= spell_data_list[i]['save_dc']:
                            # End the spell on target
                            remove_spells.append(action_id)
                        else:
                            # reduce duration of spell
                            reduce_spells.append(action_id)
                    else:
                        # reduce duration of spell
                        reduce_spells.append(action_id)

        for spell in remove_spells:
            self.board_content[target_pos].char.remove_spell(spell)
            self.check_concentration_needed(spell)

        for spell in reduce_spells:
            self.board_content[target_pos].char.reduce_spell_duration(spell)
            self.check_concentration_needed(spell)

    def end_spell(self, action_id):
        # Search each object in the board and remove any spell or action with the correct id
        for i in range(0, 400):
            if self.board_content[i].char:
                spell_data_list = self.board_content[i].char.spell_data_list
                remove_spells = []
                if spell_data_list:
                    for j in range(len(spell_data_list)):
                        if action_id == spell_data_list[j]['action_id']:
                            remove_spells.append(action_id)

                for spell in remove_spells:
                    self.board_content[i].char.remove_spell(spell)
                    logger.debug(f'Ended spell {spell}')

    def check_concentration_needed(self, action_id):
        # Check if the spell has any targets active. Drop concentration if theres nothing to concentrate anymore
        caster_pos = False
        for i in range(0, 400):
            if self.board_content[i].char:
                spell_data_list = self.board_content[i].char.spell_data_list
                # Save the caster so we dont have to look at the board again
                if action_id == self.board_content[i].char.concentrating:
                    caster_pos = i

                if spell_data_list:
                    for j in range(len(spell_data_list)):
                        if action_id == spell_data_list[j]['action_id']:
                            return

        if caster_pos:
            # We got here, so caster is concentrating on nothing. Drop concentration
            self.board_content[caster_pos].char.drop_concentration()

    def char_take_damage(self, attack_spot, target_pos, damage, on_hit_effect, dmg_type):

        logger.debug(f'Target {self.board_content[target_pos].char.monster_name} at {target_pos} took {damage}')

        # On hit effects of monster, like grapples, poison daggers etc.
        if on_hit_effect:
            self.resolve_spell(target_pos, on_hit_effect)

        # Take damage
        is_alive = self.board_content[target_pos].char.take_damage(damage, dmg_type)
        logger.debug(f'Target at {target_pos} has {self.board_content[target_pos].char.hp} hp remaining')
        self.gather_damage_stat(attacking_player=self.board_content[attack_spot].char.controlling_player, damage=damage)

        # Give rewards
        self.give_damage_reward(1-self.board_content[target_pos].char.controlling_player, damage)

        # If character dies, update game stats
        if not is_alive:
            # End concentration spells immediately.
            if self.board_content[target_pos].char.concentrating:
                self.end_spell(self.board_content[target_pos].char.concentrating)

            # End grappling effects
            spells_ending = []
            for spell_data in self.board_content[target_pos].char.spell_data_list:
                if spell_data['effect'] == 'grappled':
                    spells_ending.append(spell_data['action_id'])

            for spell in spells_ending:
                self.end_spell(spell)

            # Give reward for enemy team and reduce own reward
            self.give_damage_reward(1-self.board_content[target_pos].char.controlling_player, 45)

            logger.debug(f'Character at {self.character_list[self.board_content[target_pos].char.char_id]} dies')

            # remove larger characters extra spots
            if self.board_content[target_pos].char.size == 'large':
                target_pos = self.character_list[self.board_content[target_pos].char.char_id]
                occupied_space = self.gather_large_positions(target_pos)
                for pos in occupied_space[1:]:
                    self.board_content[pos].remove_char()

            # Update the char dictionary
            self.character_list[self.board_content[target_pos].char.char_id] = 'Dead'

            self.board_content[target_pos].remove_char()
            self.adjust_character_counts(attacking_player=self.board_content[attack_spot].char.controlling_player)


        else:
            # if concentrating. Check if concentration drops. End spell if concentration drops
            if self.board_content[target_pos].char.concentrating:
                saving_throw = self.board_content[target_pos].char.take_saving_throw('constitution')
                save_dc = 10
                if damage > save_dc:
                    save_dc = damage
                if saving_throw >= save_dc:
                    self.end_spell(self.board_content[target_pos].char.concentrating)
                    self.board_content[target_pos].char.drop_concentration()
                    logger.debug(f'Concentration ended')

    def resolve_spell(self, target_position, spell_data):
        # Single target spells
        if not spell_data['aoe']:
            for condition_immunity in self.board_content[target_position].char.condition_immunities:
                if condition_immunity in spell_data['conditions']:
                    logger.debug('Immune to condition')
                    return
            # damaging and healing spells
            if spell_data['damage']:
                # Damaging spells
                if spell_data['damage'] > 0:
                    return
                # must be a healing spell if this is true. No saves for that
                elif spell_data['damage'] < 0:
                    # Cant overheal. Heal only wounded amount
                    self.board_content[target_position].char.take_damage(spell_data['damage'], 'healing')
                    logger.debug(f"Character at {target_position} has {self.board_content[target_position].char.hp} hp")
                    # Inverse the damaging player to update right stat
                    self.gather_damage_stat(1-self.current_player_num, spell_data['damage'])
                    logger.debug(f"Healed {target_position} for {spell_data['damage']}")

                    # Reward
                    self.give_damage_reward(self.current_player_num, spell_data['damage'], healing=True)

            else:
                # Non damaging spells. Skip turn spells like Hold person. Add grapple here aswell
                if spell_data['effect'] == 'skip_turn':
                    save_results = self.board_content[target_position].char.take_saving_throw(spell_data['save_type'])
                    if save_results < spell_data['save_dc']:
                        logger.debug(f'Save failed at {target_position}')
                        self.board_content[target_position].char.apply_spell(spell_data)

                        # add concentration to the caster
                        if spell_data['caster']:
                            self.board_content[self.active_character_position].char.add_concentration(spell_data['action_id'])
                    else:
                        logger.debug(f'Save success at {target_position}')
                # Grapple
                if spell_data['effect'] == 'grappled':
                    # cant grapple as AoO. Only active can grapple
                    if self.current_player_num != self.board_content[target_position].char.controlling_player:
                        # If already grappling a target, dont do anything
                        for current_spells in self.board_content[self.active_character_position].char.spell_data_list:
                            if current_spells['effect'] == 'grappled' and current_spells['caster'] == \
                                    self.board_content[self.active_character_position].char.char_id:
                                return
                        logger.debug('Grappled')
                        self.board_content[target_position].char.apply_spell(spell_data)
                        self.board_content[target_position].char.set_speed_to_zero()
                        # Caster also cannot move
                        self.board_content[self.active_character_position].char.apply_spell(spell_data)
                        self.board_content[self.active_character_position].char.set_speed_to_zero()
                if spell_data['effect'] == 'prone':
                    # cant cause prone as AoO. Only active can cause prone
                    if self.current_player_num != self.board_content[target_position].char.controlling_player:

                        # If already prone, do nothing
                        for current_spells in self.board_content[target_position].char.spell_data_list:
                            if current_spells['effect'] == 'prone':
                                return

                        save_results = self.board_content[target_position].char.take_saving_throw(spell_data['save_type'])
                        if save_results < spell_data['save_dc']:
                            logger.debug(f'Save failed at {target_position}')
                            logger.debug('Knocked prone')
                            self.board_content[target_position].char.apply_spell(spell_data)

    def find_next_character(self):
        # Change active character to the next highest initiative or end round
        highest_initiative = -10
        new_active_pos = -1
        for i in range(self.n_squares):
            if self.active_character_position == i:
                continue
            if self.board_content[i].char:
                if self.board_content[i].char.size == 'large':
                    if not self.board_content[i].char_main_pos:
                        continue
                if not self.board_content[i].char.turn_ended:
                    if self.board_content[i].char.initiative >= highest_initiative:
                        highest_initiative = self.board_content[i].char.initiative
                        new_active_pos = i
        if new_active_pos == -1:
            return False
        else:
            return new_active_pos

    def gather_damage_stat(self, attacking_player, damage):
        if attacking_player == 0:
            self.team1_damage += damage
        else:
            self.team2_damage += damage

    def adjust_character_counts(self, attacking_player):

        if attacking_player == 0:
            #self.step_reward[0] += 1
            self.team2_remaining -= 1
        else:
            #self.step_reward[1] += 1
            self.team1_remaining -= 1

    def next_turn(self):
        # Find the character that starts the turn and reset the "turn_ended" variable
        highest_initiative = -10
        new_active_pos = -1

        for i in range(self.n_squares):
            if self.board_content[i].char:
                if self.board_content[i].char.size == 'large':
                    if not self.board_content[i].char_main_pos:
                        continue
                # Set turn_ended to False
                self.board_content[i].char.reset_turn()
                if self.board_content[i].char.initiative >= highest_initiative:
                    highest_initiative = self.board_content[i].char.initiative
                    new_active_pos = i
        if new_active_pos == -1:
            # If this happens, the game will crash
            return False
        else:
            return new_active_pos

    def step(self, action):
        # print debug info
        logger.debug(f'Character ID: {self.board_content[self.active_character_position].char.char_id}')
        logger.debug(f'Controlling player: {self.board_content[self.active_character_position].char.controlling_player}')
        logger.debug(f'Current player: {self.current_player_num}')
        logger.debug(f'Character position: {self.active_character_position}')
        logger.debug(f'Character initiative: {self.board_content[self.active_character_position].char.initiative}')

        self.step_reward = [0] * self.n_players
        done = False

        # check move legality or if the round number is higher than 100. End game if it is
        if self.round_number > 29:
            done = True
        elif self.legal_actions[action] == 0:
            self.step_reward = [1.0 / (self.n_players - 1)] * self.n_players
            self.step_reward[self.current_player_num] = -1
            done = True
        else:

            action_result, action_reward = self.execute_action(action)

            self.step_reward[self.current_player_num] += action_reward

            # Set the next active player based on initiative
            if action_result == "change character":
                # Write function to update spell status on all characters.


                new_active = self.find_next_character()
                if new_active:
                    self.active_character_position = new_active
                    self.current_player_num = self.board_content[self.active_character_position].char.controlling_player
                else:
                    """
                    if self.team1_damage > self.team2_damage:
                        reward[0] += 1
                        reward[1] -= 1
                    else:
                        reward[0] -= 1
                        reward[1] += 1
                    """

                    new_round_char = self.next_turn()
                    self.active_character_position = new_round_char
                    self.current_player_num = self.board_content[self.active_character_position].char.controlling_player

                    self.round_number += 1

            # Check if either team is dead
            if self.team1_remaining == 0:
                done = True
                self.step_reward[1] += 30 - self.round_number
                #self.step_reward[0] -= 15 - self.round_number
            if self.team2_remaining == 0:
                done = True
                self.step_reward[0] += 30 - self.round_number
                #self.step_reward[1] -= 15 - self.round_number



        self.done = done

        #self.render()

        return self.observation, self.step_reward, done, {}

    def reset(self):
        # Scoring metadata
        self.round_number = 0
        self.team1_damage = 0
        self.team2_damage = 0
        self.current_action_id = 0
        self.character_list = {}

        # Initialize the board and set the self.current_player_num
        self.set_contents()

        self.team1_remaining = 5
        self.team2_remaining = 5

        # Set the current player based on rolled initiative
        self.done = False
        logger.debug(f'\n\n---- NEW GAME ----')

        return self.observation

    def render(self, mode='human', close=False):

        if close:
            return

        logger.debug(f'Round: {self.round_number}')

        """
        char_count = 0
        unique_char_id = []
        for i in range(400):
            if self.board_content[i].char:
                if self.board_content[i].char.char_id not in unique_char_id:
                    char_count += 1
                    unique_char_id.append(self.board_content[i].char.char_id)
        
        if char_count != self.team1_remaining + self.team2_remaining - 6:
            raise Exception('Characters got deleted somewhere')
        logger.debug(f'Total character count {char_count}')
        """
        logger.debug(f'Team 1 characters remaining: {self.team1_remaining}')
        logger.debug(f'Team 2 characters remaining: {self.team2_remaining}')
        logger.debug(f'Team 1 damage done: {self.team1_damage}')
        logger.debug(f'Team 2 damage done: {self.team2_damage}')

    def rules_move(self):
        raise Exception('Rules based agent is not yet implemented for DndCombat!')
