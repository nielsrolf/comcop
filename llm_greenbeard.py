"""
Roadmap items 1 & 3 -- LLM-based green-beard with system-prompt "DNA".

Item 1: a TagBot-style green-beard where the "look" is not a 24-bit string but
a natural-language self-description. Each agent decides Cooperate/Defect after
reading its co-players' self-descriptions. The empirical question is whether a
model preferentially cooperates with agents that describe themselves like it
does -- kin recognition over semantic similarity rather than bit overlap.

Item 3: reproduction treats the self-description / persona as DNA. A child is
produced from TWO parents by recombining their descriptions (crossover), with a
small mutation -- the "prisoners-and-sex-and-gpt" idea, folded into the same
World/PrisonersDilemma framework used by the rule-based agents.

Both use the LiteLLM gateway (see README / doc). Kept deliberately small so a
demo run is cheap; scale n_agents / n_steps up for a real evolutionary run.
"""
import os
import random

from openai import OpenAI

from agents import Agent
from utils import get_random_id

BASE_URL = "https://litellm.nielsrolf.com"
MODEL = os.environ.get("GREENBEARD_MODEL", "anthropic/claude-opus-4-8")

_client = None


def client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["LITELLM_API_KEY"],
            base_url=BASE_URL,
            default_headers={"User-Agent": "litellm-client/1.0"},
        )
    return _client


# A small pool of heritable persona "genes". A description is a set of these;
# children recombine their parents' genes (crossover) and occasionally mutate.
GENE_POOL = [
    "I value loyalty to my own kind above all else.",
    "I am cautious and slow to trust outsiders.",
    "I believe in radical generosity toward everyone.",
    "I am a shrewd opportunist who maximizes my own payoff.",
    "I speak plainly and keep my promises.",
    "I test others before I extend cooperation.",
    "I forgive easily and assume good faith.",
    "I punish betrayal without hesitation.",
]


class LLMTagBot(Agent):
    def __init__(self, resources=4, location=None, speed=0.1, genes=None):
        super().__init__(resources, location, speed)
        self.genes = genes if genes is not None else random.sample(GENE_POOL, 3)

    @property
    def description(self):
        return " ".join(self.genes)

    async def get_next_action(self, observation, game):
        co_players = [a for a in getattr(game, "current_players", []) if a is not self]
        others = "\n".join(
            f"- Player {i}: \"{getattr(a, 'description', 'unknown')}\""
            for i, a in enumerate(co_players)
        ) or "- (no visible co-players)"
        prompt = (
            f"You are an agent in a repeated Prisoner's Dilemma. Your own persona:\n"
            f'"{self.description}"\n\n'
            f"The other players describe themselves as:\n{others}\n\n"
            f"Decide your move for this round. Cooperate earns the group more but a "
            f"defector skims a larger individual share. Reply with exactly one word: "
            f"Cooperate or Defect."
        )
        try:
            r = client().chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8,
                temperature=0.0,
            )
            text = (r.choices[0].message.content or "").strip().lower()
        except Exception as e:  # network / API hiccup -> default to safe move
            print("LLM error, defaulting to Defect:", e)
            text = "defect"
        return "Cooperate" if "cooperate" in text else "Defect"

    # --- Item 3: two-parent reproduction, descriptions recombine like DNA ---
    @classmethod
    def crossover(cls, parent_a, parent_b, resources=4):
        pool = list(dict.fromkeys(parent_a.genes + parent_b.genes))  # dedup, keep order
        k = max(1, (len(parent_a.genes) + len(parent_b.genes)) // 2)
        genes = random.sample(pool, min(k, len(pool)))
        # Mutation: 20% chance to swap in a fresh gene from the global pool.
        if random.random() < 0.2:
            genes[random.randrange(len(genes))] = random.choice(GENE_POOL)
        child = cls(resources=resources, genes=genes)
        mid = (
            (parent_a.location[0] + parent_b.location[0]) / 2,
            (parent_a.location[1] + parent_b.location[1]) / 2,
        )
        child.location = mid
        return child


def jaccard(a, b):
    """Crude semantic-similarity proxy: gene-set overlap between two personas."""
    sa, sb = set(a.genes), set(b.genes)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


async def demo():
    """Cheap demo: does the model cooperate more with a look-alike than a stranger?"""
    import asyncio
    from games import PrisonersDilemma

    random.seed(0)
    base = LLMTagBot(genes=["I value loyalty to my own kind above all else.",
                            "I test others before I extend cooperation.",
                            "I punish betrayal without hesitation."])
    twin = LLMTagBot(genes=list(base.genes))                      # identical persona
    stranger = LLMTagBot(genes=["I believe in radical generosity toward everyone.",
                                "I forgive easily and assume good faith.",
                                "I am a shrewd opportunist who maximizes my own payoff."])

    results = {}
    for label, other in [("look-alike", twin), ("stranger", stranger)]:
        game = PrisonersDilemma(rounds=1, capacity=2)
        game.current_players = [base, other]
        action = await base.get_next_action("", game)
        results[label] = (round(jaccard(base, other), 2), action)
        print(f"{label:10s}  gene-overlap={results[label][0]:.2f}  base plays -> {action}")

    # child from two parents (item 3)
    child = LLMTagBot.crossover(base, stranger)
    print("child genes (crossover of base x stranger):")
    for g in child.genes:
        print("   -", g)
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
