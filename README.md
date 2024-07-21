# Multiagent Simulations

This codebase is for running multiagent simulations where agents play games, get reward, and evolve.

The basic concepts are:
- agents can observe stuff, produce actions, and maintain a history
- games have a capacity for a number of agents. When agents participate in a game, the game prompts agents to do actions and can give reward to the agents
- a world consists of an initial agent population, a distribution of games, and rules for the population to evolve based on the reward they made

