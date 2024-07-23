import random
import uuid
import copy
from collections import defaultdict

from utils import get_random_name, get_random_id, random_color, rgb_to_binary

class RewardLogger():
    """List that logs every change to kva"""
    def __init__(self, logging_context, initial_value):
        self.logging_context = logging_context
        self.data = []
        self.append(initial_value)
    
    def append(self, value):
        self.data += [value]


colors_of ={
    "RandomAgent": rgb_to_binary("#0000FF"),
    "DefectBot": rgb_to_binary("#FF0000"),
    "CooperateBot": rgb_to_binary("#00FF00"),
}

class Agent():
    def __init__(self, resources=4, location=None, speed=0.1):
        self.history = []
        self.id = get_random_id()
        self.name = get_random_name()
        self.inbox = []
        self.rewards = RewardLogger(
            {"agent_id": self.id, 'name': self.name, 'class': self.__class__.__name__},
            resources)
        self.location = location or (random.random(), random.random())
        self.tail = self.location
        self.speed = speed
        self.color = colors_of.get(self.__class__.__name__, random_color())
    
    @property
    def total_reward(self):
        return sum(self.rewards.data)

    async def react(self, observation, options, game):
        observation = "\n".join(self.inbox) + "\n" + observation
        self.inbox = []
        self.history.append(observation)
        action = await self.get_next_action(observation, game)
        self.history.append(action)
        return action
    
    async def notify(self, observation):
        self.inbox.append(observation)
    
    async def get_next_action(self, observation, game):
        pass

    def child(self, resources):
        """Return a new agent with the same properties as this agent"""
        child = copy.deepcopy(self)
        child.id = get_random_id()
        child.rewards = RewardLogger({"agent_id": child.id}, resources)
        # Spawn child near parent with some random noise
        child.tail = child.location
        child.location = (
            (self.location[0] + random.gauss(0, self.speed)) % 1,
            (self.location[1] + random.gauss(0, self.speed)) % 1
        )
        child.speed *= random.gauss(1, 0.5)
        return child

    def move(self):
        """Move the agent randomly"""
        self.tail = self.location
        self.location = (
            min(1, self.location[0] + random.gauss(0, self.speed)) % 1,
            min(1, self.location[1] + random.gauss(0, self.speed)) % 1
        )
        

class RandomAgent(Agent):
    async def get_next_action(self, observation, game):
        return random.choice(["Cooperate", "Defect"])
    

class DefectBot(Agent):
    async def get_next_action(self, observation, game):
        return "Defect"
    

class CooperateBot(Agent):
    async def get_next_action(self, observation, game):
        return "Cooperate"
    


class Rule:
    def __init__(self, pattern, action, priority):
        pattern = "# Start" + pattern.split("# Start")[-1]
        pattern = "\n".join([p for p in pattern.split("\n") if not p.startswith("//")])
        self.pattern = pattern
        self.action = action
        self.priority = priority
    
    def matches(self, trajectory):
        # Remove everything before the last '# Start ...' line
        trajectory = "# Start" + trajectory.split("# Start")[-1]
        trajectory = [p for p in trajectory.split("\n") if not p.startswith("//")]
        pattern = self.pattern.split("\n")
        
        if not len(trajectory) == len(pattern):
            return False
        
        # Check if the pattern matches the trajectory line by line
        for p, t in zip(self.pattern, trajectory):
            # Check symbols
            for s_p, s_t in zip(p, t):
                if s_p != '*' and s_p != s_t:
                    return False
        print("Matched")
        return True
    
    def mutate(self):
        # Replace random symbols with "*" in any line that doesn't start with "//" or "#"
        # If every line starts with "#" or "//", we can't mutate
        if all(line.startswith("#") or line.startswith("//") for line in self.pattern.split("\n")):
            return
        
        lines = self.pattern.split("\n")
        line = "#"
        while line.startswith("#") or line.startswith("//"):
            line_idx = random.randint(0, len(lines) - 1)
            line = lines[line_idx]
        symbols = line.split(" ")
        symbol_idx = random.randint(0, len(symbols) - 1)
        symbols[symbol_idx] = "*"
        lines[line_idx] = " ".join(symbols)
        self.pattern = "\n".join(lines)
        
        



class MutatingBot(Agent):
    def __init__(self, resources=4, location=None, speed=0.1):
        super().__init__(resources, location, speed)
        self.rules = []
        self.color = random_color()
        self.trajectory = ""
    
    async def get_next_action(self, observation, game):
        self.trajectory += observation
        trajectory = self.trajectory
        matching_rules = [rule for rule in self.rules if rule.matches(trajectory)]
        
        if not matching_rules:
            # No matching rule, choose random action and add a new rule
            action = random.choice(game.action_description['parameters']['properties']['action']['enum'])
            new_rule = Rule(trajectory, action, random.random())
            new_rule.mutate()
            self.rules.append(new_rule)
            return action
        
        # Compute policy as weighted sum of matching rules
        policy = defaultdict(float)
        total_priority = sum(rule.priority for rule in matching_rules)
        
        for rule in matching_rules:
            policy[rule.action] += rule.priority / total_priority
        
        # Sample from the policy
        actions, weights = zip(*policy.items())
        choice = random.choices(actions, weights=weights)[0]
        
        # Add this (trajectory, choice) pair as a new rule, such that we keep doing this in the future
        new_rule = Rule(trajectory, choice, random.random())
        return choice
    
    def child(self, resources):
        child = copy.deepcopy(self)
        child.id = get_random_id()
        child.rewards = RewardLogger({"agent_id": child.id}, resources)
        
        # Spawn child near parent with some random noise
        child.tail = child.location
        
        child.location = (
            (self.location[0] + random.gauss(0, self.speed)) % 1,
            (self.location[1] + random.gauss(0, self.speed)) % 1
        )
        child.speed *= random.gauss(1, 0.1)
        
        # Mutate rules
        for rule in child.rules:
            if random.random() < 0.1:
                rule.mutate()
                rule.priority += random.gauss(0, 0.1)

        # Cutoff rules if > 1000 - cutoff lowe priority rules
        if len(child.rules) > 1000:
            child.rules = sorted(child.rules, key=lambda r: r.priority, reverse=True)[:1000]
        
        # Mutate color
        bits = child.color.split(" ")
        bit_to_flip = random.randint(0, len(bits) - 1)
        bits[bit_to_flip] = str(int(not int(bits[bit_to_flip])))
        child.color = " ".join(bits)
        
        # Mutate speed
        child.speed *= random.gauss(1, 0.1)
        
        return child


# # Visualize how colors evolve
# from utils import binary_to_rgb
# if __name__ == "__main__":
#     breakpoint()
#     import matplotlib.pyplot as plt
#     import numpy as np

#     agent = MutatingBot()
#     colors = [agent.color]
#     for _ in range(1000):
#         agent = agent.child(4)
#         colors.append(agent.color)
#         print(agent.color, binary_to_rgb(agent.color))
    
#     # Plot
#     fig, ax = plt.subplots(figsize=(10, 1))
#     ax.imshow([np.array([binary_to_rgb(color) for color in colors])])
#     ax.axis("off")
#     plt.show()