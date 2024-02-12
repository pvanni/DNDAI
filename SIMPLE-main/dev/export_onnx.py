# docker-compose exec app python3 train.py -r -e butterfly

import os

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
tf.get_logger().setLevel('INFO')
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

import torch
import torch.nn as nn
import torch as th
import torch.onnx

from tensorflow.keras.layers import Lambda


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

class PyTorchMlp(nn.Module):

  def __init__(self, n_inputs=129, n_actions=164):
      nn.Module.__init__(self)

      self.fc1 = nn.Linear(n_inputs, 128)
      self.fc2 = nn.Linear(128, 128)
      self.fc3 = nn.Linear(128, 128)
      self.fc4 = nn.Linear(128, 128)
      self.fc5 = nn.Linear(128, 128)
      self.fc6 = nn.Linear(128, 128)
      self.fc7 = nn.Linear(128, 128)
      self.fc8 = nn.Linear(128, 128)
      self.fc9 = nn.Linear(128, n_actions)
      self.activ_fn = nn.ReLU()
      self.out_activ = nn.Softmax(dim=0)

  def forward(self, x):
      x = self.activ_fn(self.fc1(x))

      # First residual connection
      x1 = x
      x = self.activ_fn(self.fc2(x))
      x = self.fc3(x)
      x = th.add(x, x1)
      x = self.activ_fn(x)

      # Second
      x2 = x
      x = self.activ_fn(self.fc4(x))
      x = self.fc5(x)
      x = th.add(x, x2)
      x = self.activ_fn(x)

      # Third
      x3 = x
      x = self.activ_fn(self.fc6(x))
      x = self.fc7(x)
      x = th.add(x, x3)
      x = self.activ_fn(x)

      x = self.activ_fn(self.fc8(x))
      x = self.out_activ(self.fc9(x))

      return x


def copy_mlp_weights(baselines_model):
    torch_mlp = PyTorchMlp(n_inputs=129, n_actions=164)
    model_params = baselines_model.get_parameters()

    policy_keys = []
    for key in model_params.keys():
        if not "dense_8" in key:
            if not "dense_9" in key:
                if not "dense_10" in key:
                    policy_keys.append(key)

    print(policy_keys)
    policy_params = [model_params[key] for key in policy_keys]

    for (th_key, pytorch_param), key, policy_param in zip(torch_mlp.named_parameters(), policy_keys, policy_params):
        param = th.from_numpy(policy_param)
        # Copies parameters from baselines model to pytorch model
        print(th_key, key)
        print(pytorch_param.shape, param.shape, policy_param.shape)
        pytorch_param.data.copy_(param.data.clone().t())

    return torch_mlp

def illegal_mask(actions):
    # mask = Lambda(lambda x: (1 - x) * -1e8)(obs[129:])
    list = []
    for action in actions:
        list.append((1-action) * -1e8)
    #print(list)
    return np.array(list)

base_env = get_environment('dndcombat')
env = selfplay_wrapper(base_env)(opponent_type = 'mostly_best', verbose = False)



baselines_mlp_model = PPO1.load('zoo/dndcombat/best_model.zip', env=env)

for key, value in baselines_mlp_model.get_parameters().items():
  print(key, value.shape)

th_model = copy_mlp_weights(baselines_mlp_model)

obs = env.reset()
obs = obs
#print(obs)
#print(obs.shape)
#print(type(obs))
print(baselines_mlp_model.action_probability(obs))


mask = illegal_mask(obs[129:])
#mask = Lambda(lambda x: (1 - x) * -1e8)(obs[129:])

# th_model(th.from_numpy(obs[:129]).float()

results = th_model(th.from_numpy(obs[:129]).float())

print(results)

torch.onnx.export(th_model, th.randn(129), 'best_model.onnx', export_params=True, input_names=['input'], output_names=['output'])

#results = results.detach().numpy()
#print(np.log(results))
"""
print(mask)
input()
print(results + mask)
"""
import onnx
onnx_model = onnx.load('best_model.onnx')
onnx.checker.check_model(onnx_model)


#print(th_model(th.from_numpy(obs[:129]).float()) * mask)

#tf.matmul(th_model(th.from_numpy(obs[:129]), mask))


#print(ppo_model.get_parameters())

#model.save('onnx_test_model')

#print(tf.saved_model.simple_save)
"""
obs_ph, _, action_ph = model._get_pretrain_placeholders()

print(obs_ph)
print(action_ph)

#print(model.policy.obs_ph)

#print(obs_ph)
#print(action_ph)
#print(model.action_ph)
#print(model.act_model.obs_ph)
#tf.saved_model.simple_save(model.sess, 'tensorflow_model', inputs={"obs": obs_ph}, outputs={"action": action_ph})

#arch = get_network_arch('dndcombat')

#print(arch._value_fn)
"""