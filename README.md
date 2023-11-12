# cannongameRL
Cannon self-made game with env wrapper with intention to train a PPO (sb3) network

Project is a self-made simple game in python, using pygame library.
Intention was to train a RL Network by using stable-baselines3 libraries. Initially PPO was the chosen one, however, it seems to be more practical for continous rewards and action spaces.

Finally DQN was the selected one with Mlp policy, as observation space is intended to be binary data and not an image


Required libraries:

!pip install pygame
!pip install numpy
!pip install gymnasium
!pip install pytorch (CHOOSE YOUR BEST OPTION ON WEB [CUDA, PLATFORM, ETC..]
!pip install stable-baselines3[extra]