from gym.envs.registration import register

register(
    id='DndCombatEnv-v0',
    entry_point='dndcombat.envs:DndCombatEnv',
)

