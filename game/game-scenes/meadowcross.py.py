from ursina import *
from game.dialogue import DialogueBox

class NPC(Entity):
    def __init__(self, name, dialogue, position=(0,0,0)):
        super().__init__(model='cube', color=color.azure, position=position, collider='box')
        self.name = name
        self.dialogue = dialogue

    def talk(self, dialogue_box):
        lines = [f"{self.name}: {line}" for line in self.dialogue]
        dialogue_box.start(lines)

class Meadowcross(Entity):
    def __init__(self, dialogue_box):
        super().__init__()
        self.dialogue_box = dialogue_box
        self.npcs = []

        # ground
        Entity(model='plane', scale=30, texture='white_cube', texture_scale=(30,30), color=color.green)

        # simple houses
        Entity(model='cube', scale=(4,3,4), position=(5,1.5,0), color=color.brown)
        Entity(model='cube', scale=(4,3,4), position=(-5,1.5,0), color=color.brown)

        # NPCs
        self.npcs.append(NPC("Villager", ["Welcome to Meadowcross!", "It’s a peaceful town."], position=(2,0,2)))
        self.npcs.append(NPC("Researcher", ["I study Pokémon from this region.", "Have you heard of Mega Evolution?"], position=(-2,0,-3)))

    def check_interactions(self, player):
        for npc in self.npcs:
            if distance(player.position, npc.position) < 2:
                return npc
        return None
