import random
import uuid
import copy
from collections import defaultdict

from utils import (
    get_random_name, get_random_id, random_color, rgb_to_binary,
    hamming_similarity, rgb_vector_similarity, rgb_vector_to_hex, binary_to_rgb,
)

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
        # NOTE: this used to zip(self.pattern, trajectory) i.e. the raw pattern
        # *string* against the trajectory *line list*, which meant only the
        # first character of each line was ever compared. Rules therefore
        # almost never matched anything beyond the first token, so MutatingBot
        # never really reused what it had learned. Fixed to compare line-by-line.
        for p, t in zip(pattern, trajectory):
            # Check symbols
            for s_p, s_t in zip(p, t):
                if s_p != '*' and s_p != s_t:
                    return False
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


class TagBot(Agent):
    """Minimal 'green-beard' / tag-based kin-recognition agent.

    Every agent carries a costless, arbitrary, heritable, mutable "look"
    (`self.color`, the same 24-bit binary string used for visualization
    elsewhere) plus a heritable `tolerance` in [0, 1]: the minimum fraction
    of matching bits a co-player's look must share for this agent to
    cooperate with them.

    tolerance == 0   -> cooperate with everyone (indiscriminate altruist)
    tolerance == 1   -> cooperate with (almost) nobody, incl. most kin (xenophobe)
    0 < tolerance < 1 -> cooperate selectively with agents that "look like family"

    This is the piece that was missing for the "evolution of rules" experiment
    described in the doc: MutatingBot's trajectory-matching rules never saw
    an opponent's look at all, so no kin-conditioned strategy could ever
    arise. TagBot instead makes the look a first-class, decidable input, and
    lets evolution (mutation + differential reproduction) discover whatever
    tolerance is fittest given the population's tag diversity and how games
    are paired (see World(pairing=...) and kin_experiment.py).
    """

    def __init__(self, resources=4, location=None, speed=0.1, tolerance=None):
        super().__init__(resources, location, speed)
        self.color = random_color()  # the visible "look" / tag
        self.tolerance = random.random() if tolerance is None else tolerance

    async def get_next_action(self, observation, game):
        co_players = [a for a in getattr(game, "current_players", []) if a is not self]
        if not co_players:
            return "Cooperate"
        avg_similarity = sum(
            hamming_similarity(self.color, other.color) for other in co_players
        ) / len(co_players)
        return "Cooperate" if avg_similarity >= self.tolerance else "Defect"

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

        # Mutate look: flip one random bit
        bits = child.color.split(" ")
        bit_to_flip = random.randint(0, len(bits) - 1)
        bits[bit_to_flip] = str(int(not int(bits[bit_to_flip])))
        child.color = " ".join(bits)

        # Mutate tolerance
        child.tolerance = min(1.0, max(0.0, child.tolerance + random.gauss(0, 0.05)))

        return child


class GradientTagBot(Agent):
    """Green-beard agent whose 'look' is a *continuous* RGB color.

    Motivation: TagBot's tag is a 24-bit string mutated by flipping exactly
    one bit per birth. That makes the look move in coarse, discontinuous jumps
    (a single bit can swing a whole channel by 128), and tag "distance" is a
    Hamming count that ignores how close two colors actually are perceptually.

    GradientTagBot instead stores the look as three floats in [0,1] and mutates
    it *smoothly*: add zero-mean Gaussian noise to the RGB vector and clip back
    into the valid [0,1]^3 cube. Offspring therefore drift by small color steps,
    so lineages trace out a continuous gradient in color space and kin form
    gradually-shading clusters rather than discrete bit-classes. Similarity is
    the continuous `rgb_vector_similarity` (1 - normalized L1 distance) instead
    of a bit-match fraction.

    Everything else matches TagBot: a heritable `tolerance` in [0,1]; cooperate
    with a co-player iff average look-similarity >= tolerance. `self.color` is
    kept as a binary string synced from the RGB vector purely so the existing
    visualization / World bookkeeping keeps working.
    """

    def __init__(self, resources=4, location=None, speed=0.1, tolerance=None,
                 mutation_sigma=0.08):
        super().__init__(resources, location, speed)
        self.rgb = [random.random(), random.random(), random.random()]
        self.mutation_sigma = mutation_sigma
        self.tolerance = random.random() if tolerance is None else tolerance
        self._sync_color()

    def _sync_color(self):
        self.color = rgb_to_binary(rgb_vector_to_hex(self.rgb))

    async def get_next_action(self, observation, game):
        co_players = [a for a in getattr(game, "current_players", []) if a is not self]
        if not co_players:
            return "Cooperate"
        avg_similarity = sum(
            rgb_vector_similarity(self.rgb, getattr(other, "rgb", None)
                                  or self._hex_rgb(other))
            for other in co_players
        ) / len(co_players)
        return "Cooperate" if avg_similarity >= self.tolerance else "Defect"

    @staticmethod
    def _hex_rgb(other):
        # Fallback: derive an RGB vector from a bit-string-look agent so mixed
        # populations still compare meaningfully.
        h = binary_to_rgb(other.color).lstrip("#")
        return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]

    def child(self, resources):
        child = copy.deepcopy(self)
        child.id = get_random_id()
        child.rewards = RewardLogger({"agent_id": child.id}, resources)

        child.tail = child.location
        child.location = (
            (self.location[0] + random.gauss(0, self.speed)) % 1,
            (self.location[1] + random.gauss(0, self.speed)) % 1,
        )
        child.speed *= random.gauss(1, 0.1)

        # Smooth gradient mutation: add Gaussian noise to RGB, clip to [0,1].
        child.rgb = [
            min(1.0, max(0.0, c + random.gauss(0, self.mutation_sigma)))
            for c in self.rgb
        ]
        child._sync_color()

        child.tolerance = min(1.0, max(0.0, child.tolerance + random.gauss(0, 0.05)))
        return child


class KinMutatingBot(MutatingBot):
    """MutatingBot that can *condition its learned rules on the co-player's look*.

    Roadmap item 2. The original MutatingBot learned `trajectory -> action`
    rules, but the trajectory never contained any information about *who* it
    was playing, so no kin-conditioned strategy ("cooperate with look-alikes,
    defect against strangers") could ever be expressed, let alone selected for.

    Now that `game.current_players` exposes each co-player's heritable `.color`
    tag, this agent injects a *discretized kin-similarity token* into the
    trajectory before rule matching:

        LOOK <bucket>

    where `bucket` in {0..n_buckets-1} is the average bit-similarity between
    this agent's tag and its co-players', binned into `n_buckets`. Because the
    token is an ordinary (non-`#`, non-`//`) line, MutatingBot's existing
    Rule.matches / Rule.mutate machinery treats it exactly like any other part
    of the pattern: rules can key off it, and mutation can generalize it to `*`
    (kin-agnostic) when that turns out to be fitter. Evolution then decides,
    for free, whether reading the tag is worth conditioning on.
    """

    def __init__(self, resources=4, location=None, speed=0.1, n_buckets=4):
        super().__init__(resources, location, speed)
        self.color = random_color()  # heritable, mutable "look" / tag
        self.n_buckets = n_buckets

    def _kin_bucket(self, game):
        co_players = [a for a in getattr(game, "current_players", []) if a is not self]
        if not co_players:
            return None
        avg_similarity = sum(
            hamming_similarity(self.color, other.color) for other in co_players
        ) / len(co_players)
        # Map [0, 1] similarity onto an integer bucket 0..n_buckets-1.
        bucket = min(self.n_buckets - 1, int(avg_similarity * self.n_buckets))
        return bucket

    async def get_next_action(self, observation, game):
        bucket = self._kin_bucket(game)
        if bucket is not None:
            # Prepend a matchable kinship token so learned rules can condition
            # on "how much does my opponent look like me right now".
            observation = f"LOOK {bucket}\n" + observation
        return await super().get_next_action(observation, game)


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