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
    return ' '.join([format(random.randint(0, 255), '08b') for _ in range(3)])

def binary_to_rgb(binary):
    # Return hex string like #FFFFFF
    binary = binary.replace(" ", "")
    hex_color = format(int(binary, 2), '06x')
    return "#" + hex_color

def rgb_to_binary(rgb):
    # Return 3 byte binary string
    rgb = rgb.replace("#", "")
    return ' '.join([format(int(rgb[i:i+2], 16), '08b') for i in range(0, 6, 2)])
