import time
import uuid
import random
import numpy as np
from collections import defaultdict
from kva import kva, set_storage
from collections import Counter
from tqdm import tqdm

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
    def __init__(self, resources=4):
        self.history = []
        self.id = get_random_id()
        self.name = get_random_name()
        self.inbox = []
        self.rewards = RewardLogger(
            {"agent_id": self.id, 'name': self.name, 'class': self.__class__.__name__},
            resources)
    
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
        """Return a new agent with the same properties as this agent
        
        The default action is to simply copy the agent, but one could also implement a mutation here
        """
        child = copy.deepcopy(self)
        child.id = get_random_id()
        kva.log(event="Reproduction", parent_id=self.id, child_id=self.id)
        child.rewards = RewardLogger({"agent_id": child.id}, resources)
        return child
        

        

class AIAgent(Agent):
    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        super().__init__()


class OAIgent(AIAgent):
    async def get_next_action(self):
        pass


class ClaudeAgent(AIAgent):
    async def get_next_action(self):
        pass


class RandomAgent(Agent):
    async def get_next_action(self, observation, game):
        return random.choice(["Cooperate", "Defect"])
    

class DefectBot(Agent):
    async def get_next_action(self, observation, game):
        return "Defect"

class CooperateBot(Agent):
    async def get_next_action(self, observation, game):
        return "Cooperate"
    

class Game():
    async def play(self, agents):
        pass


class PrisonersDilemma():
    """
    __| C   | D     |
    C | 1/1 | -1/2  |
    D | 2/-1| 0/0   |
    """
    def __init__(self, capacity=2, rounds=4, noise=0.1):
        self.capacity = capacity
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
    
    def evolve(self):
        """When an agent has this many resources, they reproduce (copy themselves) and they lose resources"""
        next_generation = []
        for agent in self.agents:
            agent.rewards.append(-1) # Eating cost
            if agent.total_reward < 0:
                continue
            while agent.total_reward > self.resources_to_evolve:
                next_generation.append(agent.child(self.resources_to_evolve))
                agent.rewards.append(-self.resources_to_evolve)
            next_generation.append(agent)
        return next_generation
    
    # def evolve(self):
    #     # Shuffle agents to avoid selection bias
    #     random.shuffle(self.agents)
    #     agents = sorted(self.agents, key=lambda x: x.total_reward, reverse=True)
    #     best_agents = agents[:len(agents) // 2]
    #     next_generation = []
    #     for agent in best_agents:
    #         agent.rewards.append(-self.resources_to_evolve)
    #         next_generation += [agent.child(self.resources_to_evolve), agent]
    #     return next_generation
    
    def select_for_game(self, agents, capacity, backup):
        """Takes a list og agents that need to play in this round and returns a list of agents that will play and a list of agents that still need to play
        
        One could implement a location based selection here, but for now we just randomly select agents
        """
        if len(agents) < capacity:
            return agents + random.sample(backup, k=capacity - len(agents)), []
        
        ids = random.sample(range(len(agents)), capacity)
        return [agents[i] for i in ids], [agent for i, agent in enumerate(agents) if i not in ids]

    @property
    def name(self):
        # TODO return name based on agent population and game distribution
        return "World"

    async def run(self, n_rounds):
        kva.init()
        with kva.context(world=self.name, run_id=get_random_id()):
            for i in tqdm(range(n_rounds)):
                agents_count = Counter([type(agent).__name__ for agent in self.agents])
                logged = kva.log(step=i, population=agents_count)
                print(logged)
                need_to_play = self.agents
                while need_to_play:
                    game = copy.deepcopy(random.choice(self.games))
                    players, need_to_play = self.select_for_game(need_to_play, game.capacity, backup=[agent for agent in self.agents if agent not in need_to_play])
                    await game.play(players)
                self.agents = self.evolve()
      

async def main():
    world = World(
        agents=[RandomAgent() for i in range(10)] + [CooperateBot() for i in range(10)] + [DefectBot() for i in range(2)],
        games=[PrisonersDilemma(2)]
    )

    await world.run(50)
    df = kva.get(step=49).latest('players', index='game')
    print(df)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())