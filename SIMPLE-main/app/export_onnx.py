# docker-compose exec app python3 train.py -r -e butterfly

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

import tensorflow as tf
tf.get_logger().setLevel('INFO')
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


import argparse
import time
from shutil import copyfile
from mpi4py import MPI

from stable_baselines.ppo1 import PPO1
from stable_baselines.common.callbacks import EvalCallback

from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines.common import set_global_seeds
from stable_baselines import logger

from utils.callbacks import SelfPlayCallback
from utils.files import reset_logs, reset_models
from utils.register import get_network_arch, get_environment
from utils.selfplay import selfplay_wrapper

import config


base_env = get_environment('dndcombat')
env = selfplay_wrapper(base_env)(opponent_type = 'mostly_best', verbose = False)


model = PPO1.load('zoo/dndcombat/best_model.zip', env=env)

#print(ppo_model.get_parameters())

print(model.act_model)
print(model.action_ph)
print(model.act_model.obs_ph)
tf.saved_model.simple_save(model.sess, 'tensorflow_model', inputs={"obs": model.act_model.obs_ph}, outputs={"action": model.action_ph})

#arch = get_network_arch('dndcombat')

#print(arch._value_fn)