import re
import random
from collections import defaultdict

class Rule:
    def __init__(self, pattern, action, priority):
        self.pattern = pattern
        self.action = action
        self.priority = priority

    def matches(self, trajectory):
        return re.match(self.pattern, trajectory) is not None

class MutatingBot(Agent):
    def __init__(self, resources=4, location=None, speed=0.1):
        super().__init__(resources, location, speed)
        self.rules = []
        self.look = self.generate_random_look()

    @staticmethod
    def generate_random_look():
        return ''.join([format(random.randint(0, 255), '08b') for _ in range(9)])

    def format_trajectory(self, observation, game):
        # Format the observation into the specified syntax
        players = [f"Player {i+1}: {player.look}" for i, player in enumerate(game.agents)]
        header = f"{game.__class__.__name__}\n" + "\n".join(players)
        return f"{header}\n{observation}"

    async def get_next_action(self, observation, game):
        trajectory = self.format_trajectory(observation, game)
        
        matching_rules = [rule for rule in self.rules if rule.matches(trajectory)]
        
        if not matching_rules:
            # No matching rule, choose random action and add a new rule
            action = random.choice(["Cooperate", "Defect"])
            new_rule = Rule(re.escape(trajectory), action, random.random())
            self.rules.append(new_rule)
            return action
        
        # Compute policy as weighted sum of matching rules
        policy = defaultdict(float)
        total_priority = sum(rule.priority for rule in matching_rules)
        
        for rule in matching_rules:
            policy[rule.action] += rule.priority / total_priority
        
        # Sample from the policy
        actions, weights = zip(*policy.items())
        return random.choices(actions, weights=weights)[0]

    def mutate(self):
        # Mutate rules
        for rule in self.rules:
            if random.random() < 0.1:  # 10% chance to mutate each rule
                # Replace random elements with "*"
                pattern_parts = list(rule.pattern)
                for _ in range(random.randint(1, 3)):
                    idx = random.randint(0, len(pattern_parts) - 1)
                    pattern_parts[idx] = '*'
                rule.pattern = ''.join(pattern_parts)
                
                # Add noise to priority
                rule.priority += random.gauss(0, 0.1)
                rule.priority = max(0, min(1, rule.priority))  # Clamp between 0 and 1

        # Mutate one bit of the look
        look_bits = list(self.look)
        bit_to_flip = random.randint(0, len(look_bits) - 1)
        look_bits[bit_to_flip] = '1' if look_bits[bit_to_flip] == '0' else '0'
        self.look = ''.join(look_bits)

    def child(self, resources):
        child = super().child(resources)
        child.rules = [Rule(rule.pattern, rule.action, rule.priority) for rule in self.rules]
        child.mutate()
        return child

    @property
    def color(self):
        # Generate a color based on the first 3 bytes of the look
        r = int(self.look[:8], 2)
        g = int(self.look[8:16], 2)
        b = int(self.look[16:24], 2)
        return f'#{r:02x}{g:02x}{b:02x}'
