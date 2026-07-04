
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


class UltimatumGame(Game):
    """Repeated two-player ultimatum game.

    Each round every agent acts once as *proposer*: it offers a fraction
    ``offer`` of a pie of size ``pie`` to the other agent (the *responder*).
    The responder accepts iff the offer meets its ``threshold``:

        accept  ->  proposer keeps  pie*(1-offer),  responder gets pie*offer
        reject  ->  both get 0

    Rational self-interest says: offer the smallest non-zero amount, and
    accept any positive amount. Yet humans reliably reject unfair offers and
    proposers make near-fair offers. The question here is whether a *fairness
    norm* co-evolves the way kin-tolerance did in Experiment 2: does the
    population settle on generous offers and demanding thresholds, and does
    that depend on spatial structure (proximity pairing => you tend to bargain
    with kin) or on pie size?

    Agents are expected to expose two heritable genes, ``offer`` and
    ``threshold`` in [0, 1] (see UltimatumBot).
    """

    def __init__(self, capacity=2, rounds=4, pie=2.0, location=None):
        super().__init__(capacity, location)
        self.rounds = rounds
        self.pie = pie

    async def play(self, agents):
        self.current_players = agents
        if len(agents) < 2:
            return
        for _ in range(self.rounds):
            for proposer in agents:
                for responder in agents:
                    if responder is proposer:
                        continue
                    offer = getattr(proposer, "offer", 0.5)
                    threshold = getattr(responder, "threshold", 0.0)
                    if offer >= threshold:
                        proposer.rewards.append(self.pie * (1.0 - offer))
                        responder.rewards.append(self.pie * offer)
                    else:
                        proposer.rewards.append(0.0)
                        responder.rewards.append(0.0)


class WarPeaceGame(Game):
    """Hawk-Dove with an investment / return-on-investment knob.

    Every agent splits a unit budget between *weapons* (``weapon_fraction``)
    and *peaceful production* (``1 - weapon_fraction``), and carries a
    heritable ``aggression`` probability of choosing to attack when it meets
    another agent.

    When two agents meet:
      * If **either** attacks, they fight. The agent with the larger weapon
        stock wins with probability tied to ``determinism`` (a fully
        deterministic world always awards victory to the stronger; a fully
        random world flips a coin). The winner loots ``loot_fraction`` of the
        loser's resources; the loser loses them. Nobody earns peaceful RoI
        this step -- war is pure redistribution minus opportunity cost.
      * If **neither** attacks, both earn ``roi`` on their peaceful capital,
        i.e. ``roi * (1 - weapon_fraction)`` -- a positive-sum outcome.

    Two environmental knobs shape the evolutionary pressure:
      * ``determinism`` in [0,1]: how reliably better weapons win a fight.
      * ``roi``: how rewarding peace is.

    Sweeping these two axes and measuring total welfare (Experiment 3) maps
    out when evolution selects for disarmament and peace vs. an arms race.
    """

    def __init__(self, capacity=2, determinism=1.0, roi=1.0,
                 loot_fraction=0.5, location=None):
        super().__init__(capacity, location)
        self.determinism = determinism
        self.roi = roi
        self.loot_fraction = loot_fraction

    async def play(self, agents):
        self.current_players = agents
        if len(agents) < 2:
            return
        a, b = agents[0], agents[1]
        attack_a = random.random() < getattr(a, "aggression", 0.0)
        attack_b = random.random() < getattr(b, "aggression", 0.0)

        if attack_a or attack_b:
            wa = getattr(a, "weapon_fraction", 0.0)
            wb = getattr(b, "weapon_fraction", 0.0)
            if random.random() < self.determinism:
                winner, loser = (a, b) if wa >= wb else (b, a)
            else:
                winner, loser = (a, b) if random.random() < 0.5 else (b, a)
            loot = self.loot_fraction * max(0.0, loser.total_reward)
            winner.rewards.append(loot)
            loser.rewards.append(-loot)
        else:
            a.rewards.append(self.roi * (1.0 - getattr(a, "weapon_fraction", 0.0)))
            b.rewards.append(self.roi * (1.0 - getattr(b, "weapon_fraction", 0.0)))
                    