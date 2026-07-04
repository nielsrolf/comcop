import uuid
import random

def get_random_name():
    return random.choice([
        "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy", "Kevin", "Larry", "Mallory", "Nancy", "Oscar", "Peggy", "Quentin", "Randy", "Steve", "Trent", "Ursula", "Victor", "Walter", "Xavier", "Yvonne", "Zelda"
    ])

def get_random_id():
    return uuid.uuid4().hex[:8]


def random_color():
    # Return 3 byte binary string
    original = [" ".join([bit for bit in format(random.randint(0, 255), '08b')]) for _ in range(3)]
    return ''.join(original)

def binary_to_rgb(binary):
    # Return hex string like #FFFFFF
    binary = binary.replace(" ", "")
    hex_color = format(int(binary, 2), '06x')
    return "#" + hex_color

def rgb_to_binary(rgb):
    # Return 3 byte binary string
    rgb = rgb.replace("#", "")
    return ' '.join([format(int(rgb[i:i+2], 16), '08b') for i in range(0, 6, 2)])


def rgb_vector_similarity(rgb_a, rgb_b):
    """Similarity between two continuous RGB vectors in [0,1]^3.

    Returns 1.0 for identical colors and 0.0 for maximally distant ones,
    using normalized L1 distance:  1 - mean(|a-b|) over the 3 channels.
    This is the continuous analogue of `hamming_similarity` and is used by
    GradientTagBot, whose "look" is a real-valued color that mutates by
    adding Gaussian noise (a smooth gradient) rather than by flipping a bit.
    """
    if not rgb_a or not rgb_b or len(rgb_a) != len(rgb_b):
        return 0.0
    return 1.0 - sum(abs(a - b) for a, b in zip(rgb_a, rgb_b)) / len(rgb_a)


def rgb_vector_to_hex(rgb):
    """[r,g,b] floats in [0,1] -> '#rrggbb' hex string."""
    return "#" + "".join(format(int(round(max(0.0, min(1.0, c)) * 255)), "02x") for c in rgb)


def hamming_similarity(color_a, color_b):
    """Fraction of matching bits between two binary-string 'looks' (e.g. agent colors).

    1.0 means identical tags ("full siblings"), 0.0 means every bit differs.
    Used by TagBot to decide whether a co-player looks enough like "kin" to
    cooperate with, and by World to track population-level tag diversity.
    """
    bits_a = color_a.replace(" ", "")
    bits_b = color_b.replace(" ", "")
    if not bits_a or len(bits_a) != len(bits_b):
        return 0.0
    matches = sum(1 for a, b in zip(bits_a, bits_b) if a == b)
    return matches / len(bits_a)
