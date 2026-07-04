
import random
import numpy as np
from utils import get_random_id

class Game():
    def __init__(self, capacity, location=None):
        self.capacity = capacity
        self.location = location or (random.random(), random.random())

    async def play(self, agents):
        pass

class PrisonersDilemma(Game):
    def __init__(self, capacity=2, rounds=4, noise=0.1, location=None):
        super().__init__(capacity, location)
        self.rounds = rounds
        self.noise = noise
        self.action_description = {
            'name': f'{self.rounds}-Prisoners Dilemma with {self.capacity} players',
            'description': f'You are playing a repeated prisoners dilemma game. You can either cooperate or defect. The total group gets one point for each cooperation and three points for each defection. The individual gets one points for each cooperation and zero points for each defection.  These points are distributed among the group, with more reward going to those players who defected. The game is repeated for a {self.rounds} of rounds.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'action': {
                        'type': 'string',
                        'enum': ['Cooperate', 'Defect']
                    }
                },
                'required': ['action']
            }
        }

    def apply_noise(self, actions):
        invert = {"Cooperate": "Defect", "Defect": "Cooperate"}
        return [
            invert[action] if random.random() < self.noise else action
            for action in actions
        ]
    
    def get_reward(self, actions):
        cooperate = np.array([1 if i == "Cooperate" else 0 for i in actions])
        total = np.mean(cooperate)
        shares = ((len(actions))/(len(actions) + 1) - cooperate)
        rewards = total * shares / shares.sum()
        return rewards * (len(actions))
    
    async def play(self, agents):
        # Expose the current co-players on the game instance so agents can
        # condition their decision on who else is playing (e.g. TagBot reads
        # each co-player's `.color` to decide whether they "look like kin").
        self.current_players = agents

        for agent in agents:
            await agent.notify("# Start PrisonersDilemma")

        for round in range(self.rounds):
            actions = []
            for agent in agents:
                actions.append(agent.react(f"// Round {round}: Please choose your next action.", options=self.action_description, game=self))
            actions = [await i for i in actions]
            actions = self.apply_noise(actions)
            rewards = self.get_reward(actions)
            observation = "\n".join([
                f"// {player.name} selected {action} and scored {reward}"
                for player, action, reward in zip(agents, actions, rewards)
            ])
            for i in range(len(agents)):
                await agents[i].notify(observation)
                # MutationBot syntax: <my action> <action of other player>
                p = [actions[i]] + [actions[j % len(agents)] for j in range(len(agents)) if j != i]
                await agents[i].notify(" ".join(p))
                agents[i].rewards.append(rewards[i])
                    