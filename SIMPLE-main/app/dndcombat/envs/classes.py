import random
from stable_baselines import logger
import numpy as np
import math

class Square():
    def __init__(self, position, is_terrain, character, env_effects, main_pos=False):
        self.position = position
        self.is_terrain = is_terrain
        self.character_in_pos = character
        self.env_effects = env_effects

        # Large character
        # If this square is the "main" square of this large character
        self.char_main_pos = False

    def remove_char(self):
        self.character_in_pos = False
        self.char_main_pos = False

    def get_position(self):
        return self.position

    def set_character(self, character, large_main=False):
        self.character_in_pos = character
        if large_main:
            self.char_main_pos = large_main

    def get_character(self):
        return self.character_in_pos

    @property
    def char(self):
        if not self.character_in_pos:
            return False
        else:
            return self.character_in_pos


class Character():
    def __init__(self, char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed, size='medium'):

        self.char_id = char_id
        self.controlling_player = controlling_player

        self.stre = stre
        self.dex = dex
        self.con = con
        self.intt = intt
        self.wis = wis
        self.cha = cha
        self.ac = ac
        self.start_hp = hp
        self.speed = speed

        # Other attributes
        self.initiative = 0
        self.actions_available = 1
        self.bonus_action_available = 1
        self.speed_left = speed
        self.has_moved = 0
        self.hp = hp

        # If range is zero, then the monster doesnt have this attack and is always illegal action
        self.attack_action1_range = 0
        self.attack_action2_range = 0
        self.spell_action1_range = 0
        self.spell_action2_range = 0

        # Historic data for AI
        self.damage_done = 0
        self.damage_received = 0
        self.turn_ended = False
        self.is_first_action = True

        self.spell_data_list = []
        self.cast_spell = False
        self.concentrating = False
        self.reaction_available = True
        self.size = size

        self.dmg_immunities = []
        self.dmg_resistances = []
        self.condition_immunities = []

        # Multiattack uses
        self.multiattacks_left = []

        self.set_initiative()

    def set_initiative(self):
        self.initiative = random.randint(1, 20) + self.dex

    def set_position(self, pos):
        self.pos = pos

    def first_action(self):
        self.is_first_action = False

    def take_damage(self, damage, dmg_type):

        if dmg_type in self.dmg_immunities:
            logger.debug('Immune to damage')
            damage = 0
        elif dmg_type in self.dmg_resistances:
            logger.debug('Resistant towards damage')
            damage = math.floor(damage/2)

        is_alive = True
        if damage < 0:
            self.hp -= damage
            if self.hp > self.start_hp:
                self.hp = self.start_hp
            return is_alive
        self.hp -= damage
        if self.hp <= 0:
            is_alive = False

        self.damage_received += damage

        return is_alive

    def dodge(self, action_id=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False

        spell_data = {'valid_targets': False,
                      'damage': False,
                      'aoe': False,
                      'effect': False,
                      'hit_modifier': ['disadvantage_to_hit'],
                      'duration': 1,
                      'save_type': False,
                      'save_dc': False,
                      'caster': False,
                      'resolve_time': 'start_of_turn',
                      'action_id': action_id,
                      'conditions': [False]}
        self.actions_available -= action_cost

        # Apply the effect
        self.apply_spell(spell_data)

    def reset_reaction(self):
        self.reaction_available = True

    def spend_reaction(self):
        self.reaction_available = False

    def drop_concentration(self):
        self.concentrating = False

    def add_concentration(self, action_id):
        self.concentrating = action_id

    def take_saving_throw(self, save_type):
        chosen_attribute = False
        best_modifier = -99
        attribute_dict = {'strength': self.stre,
         'dexterity': self.dex,
         'constitution': self.con,
         'intelligence': self.intt,
         'wisdom': self.wis,
         'charisma': self.cha}
        for attribute in attribute_dict:
            if attribute in save_type:
                if attribute_dict[attribute] > best_modifier:
                    chosen_attribute = attribute
                    best_modifier = attribute_dict[attribute]

        save_dict = {'strength': random.randint(1, 20) + self.stre,
                     'dexterity': random.randint(1, 20) + self.dex,
                     'constitution': random.randint(1, 20) + self.con,
                     'intelligence': random.randint(1, 20) + self.intt,
                     'wisdom': random.randint(1, 20) + self.wis,
                     'charisma': random.randint(1, 20) + self.cha}
        return save_dict[chosen_attribute]

    def remove_spell(self, action_id):
        for i in range(len(self.spell_data_list)):
            if self.spell_data_list[i]['action_id'] == action_id:
                # Restore speed if the spell was a grapple or restrain
                if self.spell_data_list[i]['effect'] == 'grappled':
                    self.remove_speed_debuff()
                del self.spell_data_list[i]
                return

    def reduce_spell_duration(self, action_id):
        for i in range(len(self.spell_data_list)):
            if self.spell_data_list[i]['action_id'] == action_id:
                self.spell_data_list[i]['duration'] -= 1
                if self.spell_data_list[i]['duration'] == 0:
                    del self.spell_data_list[i]
                    return

    def apply_spell(self, spell_data):
        self.spell_data_list.append(spell_data)

    def set_speed_to_zero(self):
        self.speed_left = 0

    def reduce_speed(self, distance):
        slowed = False
        for spell_data in self.spell_data_list:
            if spell_data['effect'] == 'prone':
                slowed = True
        if slowed:
            self.speed_left -= (distance * 2)
            self.has_moved += (distance * 2)
        else:
            self.speed_left -= distance
            self.has_moved += distance

    def max_move_distance(self):
        """Slowed means that moving one square doubles the speed consumed"""
        slowed = False
        for spell_data in self.spell_data_list:
            if spell_data['effect'] == 'prone':
                slowed = True
        if slowed:
            return math.floor(self.speed_left / 2)
        else:
            return self.speed_left

    def remove_speed_debuff(self):
        logger.debug('Grapple ended. Restoring speed')
        self.speed_left = self.speed - self.has_moved

    def reset_speed(self):
        set_speed_to_zero = False
        for spell_data in self.spell_data_list:
            if spell_data['effect'] == 'grappled':
                logger.debug('Grappled. Speed zero')
                set_speed_to_zero = True

        if set_speed_to_zero:
            self.speed_left = 0
        else:
            self.speed_left = self.speed
        self.has_moved = 0

    def reset_actions(self):
        self.actions_available = 1
        self.bonus_action_available = 1
        self.multiattacks_left = []

    def did_attack_hit(self, damages, hit_rolls, disa_or_adv, distance):

        dmg = damages[0]
        roll = hit_rolls[0]
        auto_crit = False
        advantage = False
        disadvantage = False
        if disa_or_adv == 'advantage':
            advantage = True
        if disa_or_adv == 'disadvantage':
            disadvantage = True
        # Check spell effects for modifiers
        for spell_data in self.spell_data_list:
            if spell_data['hit_modifier']:
                for modifier in spell_data['hit_modifier']:
                    if modifier == 'disadvantage_to_hit':
                        disadvantage = True
                    if modifier == 'advantage_to_hit':
                        advantage = True
                    if modifier == 'melee_automatic_critical':
                        if distance == 1:
                            auto_crit = True
                    if modifier == 'melee_advantage_to_hit':
                        if distance == 1:
                            advantage = True
                    if modifier == 'ranged_disadvantage_to_hit':
                        if distance > 1:
                            disadvantage = True

        if advantage and disadvantage:
            advantage = False
            disadvantage = False

        if advantage:
            logger.debug(f'Rolling with advantage')
            roll = hit_rolls[np.argmax(hit_rolls)]
            dmg = damages[np.argmax(hit_rolls)]

        if disadvantage:
            logger.debug(f'Rolling with disadvantage')
            roll = hit_rolls[np.argmin(hit_rolls)]
            dmg = damages[np.argmin(hit_rolls)]

        if auto_crit:
            logger.debug('Automatic critical')
            dmg = damages[2]

        if roll >= self.ac:
            logger.debug(f'Attack hit')
            return dmg
        else:
            logger.debug(f'Attack missed')
            return False

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Define in monster class
        return False

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Define in monster class
        return False

    def spell_action1(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Targeted spell action
        return False

    def spell_action2(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Targeted spell action
        return False

    def special_ability1(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Self-cast ability or spell
        return False

    def special_ability2(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=0):
        # Self-cast ability or spell
        return False

    def reset_turn(self):
        self.turn_ended = False
        self.cast_spell = False

    def end_turn(self):
        self.turn_ended = True
        self.is_first_action = True
        self.multiattacks_left = []

    def used_actions(self):
        # Add bonus actions eventually
        if self.actions_available > 0:
            return False
        else:
            return True

    def use_action(self):
        self.actions_available -= 1

    def roll_hit_die(self, lower_hit, upper_hit, hit_bonus, lower_dmg, upper_dmg, dmg_bonus, n_dmg=1):
        # Roll twice for advantage/disadvantage methods downstream
        roll1 = random.randint(lower_hit, upper_hit)
        roll2 = random.randint(lower_hit, upper_hit)
        damages = []

        if roll1 == 20:
            logger.debug('Critical hit!')
            damage = 0
            for i in range(n_dmg):
                damage += random.randint(lower_dmg, upper_dmg)
            damage *= 2
            damage += dmg_bonus
            damages.append(damage)
        else:
            damage = 0
            for i in range(n_dmg):
                damage += random.randint(lower_dmg, upper_dmg)
            damage += dmg_bonus
            damages.append(damage)

        if roll2 == 20:
            damage = 0
            for i in range(n_dmg):
                damage += random.randint(lower_dmg, upper_dmg)
            damage *= 2
            damage += dmg_bonus
            damages.append(damage)
        else:
            damage = 0
            for i in range(n_dmg):
                damage += random.randint(lower_dmg, upper_dmg)
            damage += dmg_bonus
            damages.append(damage)

        # Automatic crit roll for specific cases like paralysis on the target grating auto crit
        damage = 0
        for i in range(n_dmg):
            damage += random.randint(lower_dmg, upper_dmg)
        damage *= 2
        damage += dmg_bonus
        damages.append(damage)

        hit_rolls = [roll1 + hit_bonus, roll2 + hit_bonus]

        return damages, hit_rolls


class OrcMelee(Character):
    def __init__(self, char_id, controlling_player, stre=3, dex=1, con=3, intt=-2, wis=0, cha=0, ac=13, hp=15, speed=6):
        super(OrcMelee, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.cr = 100
        self.monster_name = 'OrcMelee'
        self.attack_action1_range = 1

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # Melee hit with a Great axe. Spends action
        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 12, 3)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'slashing'


class OrcRanged(Character):
    def __init__(self, char_id, controlling_player, stre=3, dex=1, con=3, intt=-2, wis=0, cha=0, ac=13, hp=12, speed=6):
        super(OrcRanged, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.cr = 125
        self.monster_name = 'OrcRanged'
        self.attack_action1_range = 1
        self.attack_action2_range = 12

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # Melee hit with a Great axe. Spends action
        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 6, 3)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'piercing'

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # For ranged weapons add disadvantage if target is close
        disadvantage = False
        if distance == 1:
            disadvantage = 'disadvantage'

        # Javelin throw (double range for testing)
        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 6, 3)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, disadvantage, False, 'piercing'

class OrcShaman(Character):
    def __init__(self, char_id, controlling_player, stre=2, dex=0, con=1, intt=0, wis=2, cha=1, ac=15, hp=15, speed=6):
        super(OrcShaman, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.monster_name = 'OrcShaman'
        self.cr = 150
        self.attack_action1_range = 1
        self.spell_action1_range = 12
        self.spell_action2_range = 12
        self.spell_slots = [4, 2]

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # Melee hit with a mace. Spends action
        damages, to_hit = self.roll_hit_die(1, 20, 4,
                                            1, 6, 2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'bludgeoning'

    def spell_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        # Hold person lvl 2 spell
        spell_data = {'valid_targets': ['enemy'],
                      'damage': 0,
                      'aoe': False,
                      'effect': 'skip_turn',
                      'duration': 10,
                      'save_type': 'wisdom',
                      'save_dc': 10 + self.wis,
                      'caster': self.char_id,
                      'resolve_time': 'end_of_turn',
                      'action_id': action_id,
                      'hit_modifier': ['advantage_to_hit', 'melee_automatic_critical'],
                      'conditions': ['paralyzed']}

        if check:
            if self.actions_available >= action_cost \
                    and self.bonus_action_available >= bonus_cost \
                    and not self.cast_spell \
                    and self.spell_slots[1] > 0:
                return spell_data['valid_targets']
            return False

        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost
        self.cast_spell = True
        self.spell_slots[1] -= 1

        return spell_data

    def spell_action2(self, action_id=False, distance=False, check=False, action_cost=0, bonus_cost=1):
        # Healing word lvl 1 spell
        spell_data = {'valid_targets': ['friendly_healing'],
                      'damage': -(random.randint(1, 4) + self.wis),
                      'aoe': False,
                      'effect': False,
                      'save_type': False,
                      'save_dc': False,
                      'caster': False,
                      'resolve_time': False,
                      'action_id': False,
                      'hit_modifier': [False],
                      'conditions': [False]
                      }
        if check:
            if self.actions_available >= action_cost \
                    and self.bonus_action_available >= bonus_cost \
                    and not self.cast_spell \
                    and self.spell_slots[0] > 0:
                return spell_data['valid_targets']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost
        self.cast_spell = True
        self.spell_slots[0] -= 1

        return spell_data

class Ogre(Character):
    def __init__(self, char_id, controlling_player, stre=4, dex=-1, con=3, intt=-3, wis=-2, cha=-2, ac=11, hp=59, speed=8):
        super(Ogre, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.monster_name = 'Ogre'
        self.cr = 450
        self.size = 'large'
        self.attack_action1_range = 1
        self.attack_action2_range = 6

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # Melee hit with a Great club. Spends action
        damages, to_hit = self.roll_hit_die(1, 20, 6,
                                            1, 8, 4, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'bludgeoning'

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # For ranged weapons add disadvantage if target is close
        disadvantage = False
        if distance == 1:
            disadvantage = 'disadvantage'

        # Javelin throw (double range for testing)
        damages, to_hit = self.roll_hit_die(1, 20, 6,
                                            1, 6, 4, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, disadvantage, False, 'piercing'

class BrownBear(Character):
    def __init__(self, char_id, controlling_player, stre=4, dex=0, con=3, intt=-4, wis=1, cha=-2, ac=11, hp=34, speed=8):
        super(BrownBear, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.cr = 200
        self.monster_name = 'BrownBear'
        self.size = 'large'
        self.attack_action1_range = 1
        self.attack_action2_range = 1
        self.attack1_name = 'Claw'
        self.attack2_name = 'Bite'

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        """Claw attack of brown bear. Attacking first time adds one use of second attack 'bite' """
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            elif 'attack_1' in self.multiattacks_left:
                return ['enemy']
            else:
                return False

        if self.actions_available >= 1:
            # Spend resources to use this ability
            self.actions_available -= action_cost
            self.bonus_action_available -= bonus_cost
            self.multiattacks_left.append('attack_2')
        else:
            del self.multiattacks_left[self.multiattacks_left.index('attack_1')]


        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 8, 4, n_dmg=1)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'piercing'

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        """Bite attack of brown bear. Attacking first time adds one use of second attack 'claw' """
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            elif 'attack_2' in self.multiattacks_left:
                return ['enemy']
            else:
                return False

        if self.actions_available >= 1:
            # Spend resources to use this ability
            self.actions_available -= action_cost
            self.bonus_action_available -= bonus_cost
            self.multiattacks_left.append('attack_1')
        else:
            del self.multiattacks_left[self.multiattacks_left.index('attack_2')]

        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 6, 4, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'slashing'

class AnimatedArmor(Character):
    def __init__(self, char_id, controlling_player, stre=2, dex=0, con=1, intt=-5, wis=-4, cha=-5, ac=18, hp=33, speed=5):
        super(AnimatedArmor, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.cr = 200
        self.monster_name = 'AnimatedArmor'
        self.attack_action1_range = 1
        self.attack1_name = 'Slam'
        self.dmg_immunities = ['poison', 'psychic']
        self.condition_immunities = ['blinded', 'charmed', 'deafened', 'exhaustion',
                                     'frightened', 'paralyzed', 'petrified', 'poisoned']

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        """Animated armor slam. Has multiattack """
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            elif 'attack_1' in self.multiattacks_left:
                return ['enemy']
            else:
                return False

        if self.actions_available >= 1:
            # Spend resources to use this ability
            self.actions_available -= action_cost
            self.bonus_action_available -= bonus_cost
            self.multiattacks_left.append('attack_1')
        else:
            del self.multiattacks_left[self.multiattacks_left.index('attack_1')]


        damages, to_hit = self.roll_hit_die(1, 20, 4,
                                            1, 6, 2, n_dmg=1)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'bludgeoning'

class Bugbear(Character):
    def __init__(self, char_id, controlling_player, stre=2, dex=2, con=1, intt=-1, wis=0, cha=-1, ac=16, hp=27, speed=6):
        super(Bugbear, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.monster_name = 'Bugbear'
        self.cr = 200
        self.attack_action1_range = 1
        self.attack_action2_range = 6
        self.attack1_name = 'Morningstar'
        self.attack2_name = 'Javelin'

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        damages, to_hit = self.roll_hit_die(1, 20, 4,
                                            1, 8, 2, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, False, 'piercing'

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            return False
        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost

        # For ranged weapons add disadvantage if target is close
        disadvantage = False
        if distance == 1:
            disadvantage = 'disadvantage'

        # Javelin throw (double range for testing)
        damages, to_hit = self.roll_hit_die(1, 20, 4,
                                            1, 6, 2, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, disadvantage, False, 'piercing'

class DireWolf(Character):
    def __init__(self, char_id, controlling_player, stre=3, dex=2, con=2, intt=-4, wis=1, cha=-2, ac=14, hp=37, speed=8):
        super(DireWolf, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.cr = 200
        self.monster_name = 'DireWolf'
        self.size = 'large'
        self.attack_action1_range = 1
        self.attack1_name = 'Bite'
        self.spell_data_list.append({'valid_targets': False,
                                      'damage': False,
                                      'aoe': False,
                                      'effect': 'advantage_when_ally_near_target',
                                      'save_type': False,
                                      'save_dc': False,
                                      'caster': False,
                                      'resolve_time': 'attack_buff',
                                      'action_id': False,
                                      'hit_modifier': [False],
                                     'conditions': [False]})

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            else:
                return False

        # Spend resources to use this ability
        self.actions_available -= action_cost
        self.bonus_action_available -= bonus_cost


        damages, to_hit = self.roll_hit_die(1, 20, 5,
                                            1, 6, 3, n_dmg=2)

        on_hit = {'valid_targets': ['enemy'],
                      'damage': False,
                      'aoe': False,
                      'effect': 'prone',
                      'duration': False,
                      'save_type': 'strength',
                      'save_dc': 13,
                      'caster': False,
                      'resolve_time': False,
                      'action_id': action_id,
                      'hit_modifier': ['melee_advantage_to_hit', 'ranged_disadvantage_to_hit'],
                        'conditions': [False]}

        self.damage_done += np.mean(damages[:2])

        return to_hit, damages, False, on_hit, 'piercing'

class Chuul(Character):
    def __init__(self, char_id, controlling_player, stre=4, dex=0, con=3, intt=-3, wis=0, cha=-3, ac=16, hp=93, speed=6):
        super(Chuul, self).__init__(char_id, controlling_player, stre, dex, con, intt, wis, cha, ac, hp, speed)

        # Attack attributes
        self.monster_name = 'Chuul'
        self.cr = 1100
        self.size = 'large'
        self.attack_action1_range = 1
        self.attack_action2_range = 1
        self.attack1_name = 'Pincer'
        self.attack2_name = 'Tentacles'
        self.dmg_immunities = ['poison']
        self.condition_immunities = ['poisoned']

    def attack_action1(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy']
            elif 'attack_1' in self.multiattacks_left:
                return ['enemy']
            else:
                return False
        if self.actions_available >= 1:
            # Spend resources to use this ability
            self.actions_available -= action_cost
            self.bonus_action_available -= bonus_cost
            self.multiattacks_left += ['attack_1', 'attack_2']
        else:
            del self.multiattacks_left[self.multiattacks_left.index('attack_1')]

        damages, to_hit = self.roll_hit_die(1, 20, 6,
                                            1, 6, 4, n_dmg=2)

        self.damage_done += np.mean(damages[:2])

        on_hit = {'valid_targets': False,
                      'damage': False,
                      'aoe': False,
                      'effect': 'grappled',
                      'save_type': 'strength_or_dexterity',
                      'save_dc': 14,
                      'caster': self.char_id,
                      'resolve_time': False,
                      'action_id': action_id,
                      'hit_modifier': [False],
                        'conditions': [False]}

        return to_hit, damages, False, on_hit, 'bludgeoning'

    def attack_action2(self, action_id=False, distance=False, check=False, action_cost=1, bonus_cost=0):
        if check:
            if self.actions_available >= action_cost and self.bonus_action_available >= bonus_cost:
                return ['enemy', 'grappled_by']
            elif 'attack_2' in self.multiattacks_left:
                return ['enemy', 'grappled_by']
            else:
                return False
        if self.actions_available >= 1:
            # Spend resources to use this ability
            self.actions_available -= action_cost
            self.bonus_action_available -= bonus_cost
            self.multiattacks_left += ['attack_1', 'attack_1']
        else:
            del self.multiattacks_left[self.multiattacks_left.index('attack_2')]

        # Add 100 to autohit
        damages, to_hit = self.roll_hit_die(1, 20, 100,
                                            0, 0, 0, n_dmg=1)

        self.damage_done += np.mean(damages[:2])

        on_hit = {'valid_targets': ['enemy'],
                      'damage': False,
                      'aoe': False,
                      'effect': 'skip_turn',
                      'duration': 10,
                      'save_type': 'constitution',
                      'save_dc': 13,
                      'caster': False,
                      'resolve_time': 'end_of_turn',
                      'action_id': action_id,
                      'hit_modifier': ['advantage_to_hit', 'melee_automatic_critical'],
                        'conditions': ['poisoned', 'paralyzed']}

        return to_hit, damages, False, on_hit, 'piercing'


def how_many_monsters(return_count=True, monster_name=False):
    monster_type_id = {'OrcMelee': [0, OrcMelee],
                       'OrcRanged': [1, OrcRanged],
                       'OrcShaman': [2, OrcShaman],
                       'Ogre': [3, Ogre],
                       'BrownBear': [4, BrownBear],
                       'AnimatedArmor': [5, AnimatedArmor],
                       'Bugbear': [6, Bugbear],
                       'DireWolf': [7, DireWolf],
                       'Chuul': [8, Chuul]}

    if return_count:
        return len(monster_type_id)
    else:
        return monster_type_id[monster_name]
