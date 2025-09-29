from ursina import *
from game.scenes.meadowcross import Meadowcross
from game.dialogue import DialogueBox

app = Ursina()

# Player
player = Entity(model='cube', color=color.orange, scale=(1,2,1), collider='box')

camera.position = (0, 15, -20)
camera.rotation_x = 30

speed = 5
dialogue_box = DialogueBox()
current_scene = Meadowcross(dialogue_box)

def update():
    if not dialogue_box.enabled:  # Disable movement when in dialogue
        move = Vec3(
            held_keys['d'] - held_keys['a'],
            0,
            held_keys['w'] - held_keys['s']
        ).normalized() * time.dt * speed
        player.position += move

def input(key):
    if key == 'e':  # interact button
        npc = current_scene.check_interactions(player)
        if npc:
            npc.talk(dialogue_box)

app.run()
