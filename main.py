import datetime as dt
import os
import uuid
import random
import numpy as np
from collections import Counter
from tqdm import tqdm
import matplotlib.pyplot as plt
import pandas as pd

from agents import *
from games import *
from utils import *



class World:
    def __init__(self, agents, games, resources_to_evolve=4.0, pairing="proximity"):
        """
        pairing: "proximity" (default) selects the `capacity` agents closest to
            each game's location, so agents interact more with spatial
            neighbors ("siblings", since children spawn near parents). This is
            the mechanism behind the location -> cooperation experiment.
            "random" ignores location entirely and draws a uniformly random
            subset of agents for each game instead, which is used to isolate
            *tag-based* kin recognition (TagBot) from spatial assortment.
        """
        self.agents = agents
        self.games = games
        self.resources_to_evolve = resources_to_evolve
        self.pairing = pairing
        self.world_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
        os.makedirs(f'worlds/{self.world_id}', exist_ok=True)
        self.stopped_at_step = 0
        self.population_history = []
        self.color_history = []
        self.tolerance_history = []
        self.similarity_history = []
    
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
        """Select agents for a game, either by spatial proximity or uniformly at random"""
        if self.pairing == "random":
            k = min(game.capacity, len(agents))
            return random.sample(agents, k)
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

    def _avg_tolerance(self):
        """Mean kin-recognition tolerance among TagBot-like agents (None if there are none)."""
        tolerances = [a.tolerance for a in self.agents if hasattr(a, "tolerance")]
        return sum(tolerances) / len(tolerances) if tolerances else None

    def _avg_pairwise_similarity(self, max_pairs=300):
        """Mean tag (color) similarity across a random sample of agent pairs.

        A cheap population-level proxy for "how kin-clustered is the gene
        pool right now" -- rising similarity alongside falling variance in
        tolerance is the signature of tag-based kin selection taking hold.
        """
        agents = self.agents
        n = len(agents)
        if n < 2:
            return None
        pairs_available = n * (n - 1) // 2
        n_pairs = min(max_pairs, pairs_available)
        sims = []
        for _ in range(n_pairs):
            a, b = random.sample(agents, 2)
            sims.append(hamming_similarity(a.color, b.color))
        return sum(sims) / len(sims)

    async def run(self, n_rounds, visualize_every=1):
        # kva.init(run_id=self.world_id)
        for i in tqdm(range(n_rounds)):
            if len(self.agents) == 0:
                self.stopped_at_step += i
                return
            agents_count = Counter([type(agent).__name__ for agent in self.agents])
            # logged = kva.log(step=self.stopped_at_step + i, population=agents_count)
            self.population_history.append(agents_count)
            self.color_history.append([binary_to_rgb(agent.color) for agent in self.agents])
            self.tolerance_history.append(self._avg_tolerance())
            self.similarity_history.append(self._avg_pairwise_similarity())
            print(f"Step {self.stopped_at_step + i}: {agents_count}")

            random.shuffle(self.games)
            for game in self.games:
                selected_agents = self.select_for_game(self.agents, game)
                await game.play(selected_agents)
            
            self.agents = self.evolve()
            if visualize_every is not None and i % visualize_every == 0:  # Visualize every 10 rounds
                self.visualize(i)
        self.stopped_at_step += n_rounds

    def visualize(self, round_number):
        plt.figure(figsize=(10, 10))
        for agent in self.agents:
            color = binary_to_rgb(agent.color)
            size = min(1000, agent.total_reward * 30)  # Adjust size based on total_reward
            plt.scatter(agent.location[0], agent.location[1], c=color, s=size, alpha=0.5)
            # plt.plot([agent.tail[0], agent.location[0]], [agent.tail[1], agent.location[1]], c=color, alpha=0.5)
        
        for game in self.games:
            plt.scatter(game.location[0], game.location[1], c='k', marker='s', s=100)
        
        plt.title(f'World State at Round {round_number}')
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.savefig(f'worlds/{self.world_id}/world_state_round_{round_number:06d}.png')
        plt.close()
    
    def individuals_plot(self):
        # Like population plot, except it's a plot of stacked colored dots - one for each agent
        plt.figure(figsize=(10, 6))
        for step, population in enumerate(self.color_history):
            for y, agent_color in enumerate(population):
                plt.scatter(step, y, c=[agent_color], s=500)
        plt.title('Individuals')
        plt.xlabel('Step')
        plt.tight_layout()
        plt.savefig(f'worlds/{self.world_id}/individuals.png')
    
    def population_plot(self):
        # Make a larger figure with higher resolution

        df_result = pd.DataFrame(self.population_history)
        fig = plt.figure(figsize=(10, 6), dpi=100)
        df_result.plot(kind='area', stacked=True, ax=plt.gca())
        plt.title('Population')
        plt.xlabel('Step')
        plt.tight_layout()
        plt.savefig(f'worlds/{self.world_id}/population.png')
    
    def ffmpeg(self):
        os.system(f"ffmpeg -framerate 2 -pattern_type glob -i 'worlds/{self.world_id}/world_state_round_*.png' -c:v libx264 -pix_fmt yuv420p worlds/{self.world_id}/output.mp4")

async def main():
    agents = [MutatingBot() for i in range(10)] + [CooperateBot() for i in range(10)] + [DefectBot() for i in range(2)] 
    world = World(
        agents=agents,
        games=[PrisonersDilemma(rounds=4, capacity=2) for _ in range(len(agents)//2)]
    )

    await world.run(50)
    for agent in world.agents:
        if isinstance(agent, MutatingBot):
            for rule in agent.rules:
                print(rule.pattern, "->", rule.action)
                print()
            print("-" * 20)
    world.population_plot()
    world.individuals_plot()
    world.ffmpeg()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())