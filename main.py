import datetime as dt
import os
import uuid
import random
import numpy as np
from kva import kva, set_storage, File
from collections import Counter
from tqdm import tqdm
import matplotlib.pyplot as plt
import pandas as pd

set_storage("./.kva")

import copy

def get_random_name():
    return random.choice([
        "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy", "Kevin", "Larry", "Mallory", "Nancy", "Oscar", "Peggy", "Quentin", "Randy", "Steve", "Trent", "Ursula", "Victor", "Walter", "Xavier", "Yvonne", "Zelda"
    ])

def get_random_id():
    return uuid.uuid4().hex[:8]

class RewardLogger():
    """List that logs every change to kva"""
    def __init__(self, logging_context, initial_value):
        self.logging_context = logging_context
        self.data = []
        self.append(initial_value)
    
    def append(self, value):
        self.data += [value]
        kva.log(add=value, total=sum(self.data), **self.logging_context)

class Agent():
    def __init__(self, resources=4, location=None, speed=0.01):
        self.history = []
        self.id = get_random_id()
        self.name = get_random_name()
        self.inbox = []
        self.rewards = RewardLogger(
            {"agent_id": self.id, 'name': self.name, 'class': self.__class__.__name__},
            resources)
        self.location = location or (random.random(), random.random())
        self.speed = speed
    
    @property
    def total_reward(self):
        return sum(self.rewards.data)

    async def react(self, observation, options, game):
        logged = kva.log(observation=observation, agent_id=self.id)
        observation = "\n".join(self.inbox) + "\n" + observation
        self.inbox = []
        self.history.append(observation)
        action = await self.get_next_action(observation, game)
        kva.log(action=action, agent_id=self.id)
        self.history.append(action)
        return action
    
    async def notify(self, observation):
        kva.log(observation=observation, agent_id=self.id)
        self.inbox.append(observation)
    
    async def get_next_action(self, observation, game):
        pass

    def child(self, resources):
        """Return a new agent with the same properties as this agent"""
        child = copy.deepcopy(self)
        child.id = get_random_id()
        kva.log(event="Reproduction", parent_id=self.id, child_id=child.id)
        child.rewards = RewardLogger({"agent_id": child.id}, resources)
        # Spawn child near parent with some random noise
        child.location = (
            self.location[0] + random.gauss(0, self.speed) % 1,
            self.location[1] + random.gauss(0, self.speed) % 1
        )
        child.speed *= random.gauss(1, 0.5)
        return child

    def move(self):
        """Move the agent randomly"""
        self.location = (
            max(0, min(1, self.location[0] + random.gauss(0, self.speed))),
            max(0, min(1, self.location[1] + random.gauss(0, self.speed)))
        )

class RandomAgent(Agent):
    async def get_next_action(self, observation, game):
        return random.choice(["Cooperate", "Defect"])
    
    @property
    def color(self):
        return 'blue'

class DefectBot(Agent):
    async def get_next_action(self, observation, game):
        return "Defect"
    
    @property
    def color(self):
        return 'red'

class CooperateBot(Agent):
    async def get_next_action(self, observation, game):
        return "Cooperate"
    
    @property
    def color(self):
        return 'green'

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
        with kva.context(game=self.action_description['name'], game_id=get_random_id(), players=[agent.id for agent in agents]):
            for agent in agents:
                await agent.notify("You are playing a round of repeated prisoners dilemma.")
            
            for round in range(self.rounds):
                with kva.context(round=round):
                    actions = []
                    for agent in agents:
                        actions.append(agent.react(f"Round {round}: Please choose your next action.", options=self.action_description, game=self))
                    actions = [await i for i in actions]
                    rewards = self.get_reward(actions)
                    observation = "\n".join([
                        f"{player.name} selected {action} and scored {reward}"
                        for player, action, reward in zip(agents, actions, rewards)
                    ])
                    for agent, reward in zip(agents, rewards):
                        await agent.notify(observation)
                        agent.rewards.append(reward)

class World:
    def __init__(self, agents, games, resources_to_evolve=4.0):
        self.agents = agents
        self.games = games
        self.resources_to_evolve = resources_to_evolve
        self.world_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
        os.makedirs(f'worlds/{self.world_id}', exist_ok=True)
        self.stopped_at_step = 0
    
    def evolve(self):
        """When an agent has this many resources, they reproduce (copy themselves) and they lose resources"""
        next_generation = []
        for agent in self.agents:
            agent.rewards.append(-1)  # Eating cost
            agent.move()  # Move the agent
            if agent.total_reward < 0:
                continue
            while agent.total_reward > self.resources_to_evolve:
                next_generation.append(agent.child(self.resources_to_evolve))
                agent.rewards.append(-self.resources_to_evolve)
            next_generation.append(agent)
        return next_generation
    
    def select_for_game(self, agents, game):
        """Select agents for a game based on proximity"""
        sorted_agents = sorted(agents, key=lambda a: self.distance(a.location, game.location))
        selected = sorted_agents[:game.capacity]
        return selected

    @staticmethod
    def distance(loc1, loc2):
        x = (loc1[0] - loc2[0])
        y = (loc1[1] - loc2[1])
        x = min(x, 1 - x)
        y = min(y, 1 - y)
        return ((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)**0.5

    @property
    def name(self):
        return "Location-based World"

    async def run(self, n_rounds):
        kva.init(run_id=self.world_id)
        for i in tqdm(range(n_rounds)):
            if len(self.agents) == 0:
                self.stopped_at_step += i
                return
            agents_count = Counter([type(agent).__name__ for agent in self.agents])
            logged = kva.log(step=self.stopped_at_step + i, population=agents_count)
            print(logged)
            
            random.shuffle(self.games)
            for game in self.games:
                selected_agents = self.select_for_game(self.agents, game)
                await game.play(selected_agents)
            
            self.agents = self.evolve()
            if i % 1 == 0:  # Visualize every 10 rounds
                self.visualize(i)
        self.stopped_at_step += n_rounds

    def visualize(self, round_number):
        plt.figure(figsize=(10, 10))
        for agent in self.agents:
            color = 'r' if isinstance(agent, DefectBot) else 'g' if isinstance(agent, CooperateBot) else 'b'
            size = min(1000, agent.total_reward * 30)  # Adjust size based on total_reward
            plt.scatter(agent.location[0], agent.location[1], c=color, s=size, alpha=0.5)
        
        for game in self.games:
            plt.scatter(game.location[0], game.location[1], c='k', marker='s', s=100)
        
        plt.title(f'World State at Round {round_number}')
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.savefig(f'worlds/{self.world_id}/world_state_round_{round_number:06d}.png')
        plt.close()
        kva.log(world_state=File(f'worlds/{self.world_id}/world_state_round_{round_number:06d}.png'))
    
    def population_plot(self):
        df = kva.get(run_id=self.world_id).latest("population", index=["step"])
        # Make a larger figure with higher resolution
        fig = plt.figure(figsize=(10, 6), dpi=100)

        df_unpacked = pd.json_normalize(df['population'])
        df_result = pd.concat([df.drop('population', axis=1), df_unpacked], axis=1)[df['population'].iloc[0].keys()]

        df_result.plot(kind='area', stacked=True, ax=plt.gca())
        plt.title('Population')
        plt.xlabel('Step')
        plt.tight_layout()
        plt.savefig(f'worlds/{self.world_id}/population.png')
        kva.log(population_plot=File(f'worlds/{self.world_id}/population.png'))
    
    def ffmpeg(self):
        # ffmpeg -framerate 2 -pattern_type glob -i 'world_state_round_*.png' -c:v libx264 -pix_fmt yuv420p output.mp4
        os.system(f"ffmpeg -framerate 2 -pattern_type glob -i 'worlds/{self.world_id}/world_state_round_*.png' -c:v libx264 -pix_fmt yuv420p worlds/{self.world_id}/output.mp4")
        kva.log(animation=File(f'worlds/{self.world_id}/output.mp4'))

async def main():
    agents = [RandomAgent() for i in range(10)] + [CooperateBot() for i in range(10)] + [DefectBot() for i in range(10)]
    world = World(
        agents=agents,
        games=[PrisonersDilemma(rounds=4, capacity=2) for _ in range(len(agents)//2)]
    )

    await world.run(50)
    world.population_plot()
    world.ffmpeg()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())