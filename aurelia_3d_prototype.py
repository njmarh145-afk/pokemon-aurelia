# aurelia_3d_prototype.py
# Prototype 3D "Aurelia" overworld using Ursina
# Playable: walk, talk to NPCs, choose starter, trigger wild battles, enter simple gym
#
# Requires: ursina
# Install: pip install ursina
#
# This file is intentionally single-file and commented for extension.

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController  # we'll adapt movement
import random
import sys

app = Ursina()
window.title = "Aurelia Prototype — 3D Overworld Playtest"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# ---- Config ----
TILE = 1
MAP_W = 40
MAP_H = 24

# Player config
PLAYER_SPEED = 4
ENCOUNTER_CHANCE = 0.08   # chance per step on grass to trigger wild encounter

# Basic color palette
GRASS_COLOR = color.rgb(110, 185, 80)
GROUND_COLOR = color.rgb(200, 170, 120)
WATER_COLOR = color.rgb(60, 140, 200)
STONE_COLOR = color.rgb(130, 130, 130)

# ---- Simple pokemon-like classes (very light) ----
class Move:
    def __init__(self, name, power, pp):
        self.name = name
        self.power = power
        self.pp = pp
        self.max_pp = pp

class Mon:
    def __init__(self, name, level, max_hp, attack, defense, moves):
        self.name = name
        self.level = level
        self.max_hp = max_hp
        self.hp = max_hp
        self.attack = attack
        self.defense = defense
        self.moves = [Move(*m) for m in moves]

    def is_fainted(self):
        return self.hp <= 0

# Small sample species for prototype
SPECIES = {
    "Flamkit": lambda lvl=5: Mon("Flamkit", lvl, 22 + lvl*2, 7, 4, [("Tackle",6,35),("Ember",8,25)]),
    "Aquadot": lambda lvl=5: Mon("Aquadot", lvl, 20 + lvl*2, 6, 5, [("Tackle",6,35),("WaterJet",9,20)]),
    "Leafin": lambda lvl=5: Mon("Leafin", lvl, 21 + lvl*2, 6, 6, [("Tackle",6,35),("VineWhip",8,25)]),
    "Grubbit": lambda lvl=2: Mon("Grubbit", lvl, 10+lvl, 4, 2, [("Bite",4,25)]),
    "Puddle": lambda lvl=2: Mon("Puddle", lvl, 9+lvl, 3, 2, [("Splash",2,30)])
}

# ---- World map generation (simple tile map) ----
# Tile codes: 0 ground, 1 grass, 2 water, 3 building / wall
world = [[0 for x in range(MAP_W)] for y in range(MAP_H)]

def carve_grass_patch(x0, y0, w, h, density=0.5):
    for y in range(y0, min(MAP_H, y0+h)):
        for x in range(x0, min(MAP_W, x0+w)):
            if random.random() < density:
                world[y][x] = 1

# Meadowcross area (left)
for y in range(3,10):
    for x in range(2,10):
        world[y][x] = 0
carve_grass_patch(10,3,10,6, density=0.4)

# Glimmerport area (right)
for y in range(3,10):
    for x in range(28,36):
        world[y][x] = 0
carve_grass_patch(18,4,9,6, density=0.45)

# water bay between towns
for y in range(10,14):
    for x in range(12,28):
        world[y][x] = 2

# some scattered grass on routes
for i in range(6):
    carve_grass_patch(10 + i*2, 12 + (i%3), 3, 3, density=0.35)

# buildings: simple rectangular buildings for Meadowcross lab and Glimmerport gym
def place_building(x0, y0, w, h):
    for y in range(y0, min(MAP_H, y0+h)):
        for x in range(x0, min(MAP_W, x0+w)):
            world[y][x] = 3

# Meadowcross lab
place_building(3,5,4,4)
# Meadowcross houses
place_building(5,6,3,3)
place_building(7,5,3,3)

# Glimmerport buildings
place_building(30,5,4,6)  # gym
place_building(26,6,3,3)
place_building(32,9,3,2)

# simple path markers (not blocked)
for y in range(0,MAP_H):
    for x in range(0,MAP_W):
        if world[y][x] == 3:
            pass

# ---- Entities for tiles ----
tile_entities = []

def spawn_world():
    for ent in tile_entities:
        destroy(ent)
    tile_entities.clear()

    for y in range(MAP_H):
        for x in range(MAP_W):
            tx = x - MAP_W//2
            ty = y - MAP_H//2
            tile = world[y][x]
            pos = (tx, 0, ty)
            if tile == 0:
                e = Entity(model='quad', color=GROUND_COLOR, scale=(1,1), position=pos, rotation=(90,0,0))
            elif tile == 1:
                e = Entity(model='quad', color=GRASS_COLOR, scale=(1,1), position=pos, rotation=(90,0,0))
            elif tile == 2:
                e = Entity(model='quad', color=WATER_COLOR, scale=(1,1), position=pos, rotation=(90,0,0))
            elif tile == 3:
                # building floor as stone
                e = Entity(model='quad', color=STONE_COLOR, scale=(1,1), position=pos, rotation=(90,0,0))
                # raise a small cube to visually show building
                if random.random() < 0.02:
                    b = Entity(model='cube', color=color.rgb(150,120,100), scale=(0.9,0.9,0.9), position=(pos[0],0.5,pos[2]))
                    tile_entities.append(b)
            tile_entities.append(e)

# ---- Player ----
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__()
        self.model = 'cube'
        self.scale = (0.6, 1.2, 0.6)
        self.color = color.azure
        self.collider = BoxCollider(self, center=(0,0.6,0), size=(0.6,1.2,0.6))
        self.speed = PLAYER_SPEED
        self.position = (-MAP_W//2+3, 0.5, -MAP_H//2+3)
        self.party = []  # list of Mon
        self.name = "Player"
        self.last_step_tile = None
        self.controls_enabled = True

player = Player()

# Camera: third-person behind player
camera_parent = Entity()
camera_parent.position = player.position
camera.parent = camera_parent
camera.position = (0, 6, -8)
camera.rotation_x = 20

def update_camera():
    camera_parent.position = player.position + Vec3(0,0,0)

# ---- NPC system ----
class NPC(Entity):
    def __init__(self, position=(0,0,0), name="NPC", dialogues=None):
        super().__init__()
        self.model = 'cube'
        self.scale = (0.8, 1.4, 0.6)
        self.color = color.lime
        self.position = (position[0], 0.5, position[2])
        self.name = name
        self.dialogues = dialogues or ["..."]
        self.dialog_index = 0
        self.collider = BoxCollider(self, center=(0,0.6,0), size=(0.8,1.4,0.6))

    def interact(self):
        ui_show_dialog(self.name, self.dialogues)

# Spawn a few NPCs in Meadowcross and Glimmerport
npcs = []
def place_npcs():
    for n in npcs:
        destroy(n)
    npcs.clear()
    # Meadowcross villager
    npc1 = NPC(position=(-MAP_W//2+4,0,-MAP_H//2+6), name="Villager",
               dialogues=["I heard Mons dance in the fields at dawn.", "Try visiting the lab to choose a starter."])
    npcs.append(npc1)
    npc1.color = color.rgb(255,220,150)
    # Rival NPC near lab
    rival = NPC(position=(-MAP_W//2+5,0,-MAP_H//2+5), name="Rival",
               dialogues=["You again! I'll beat you to the Pokemon League!", "Let's have a friendly rematch soon."])
    rival.color = color.orange
    npcs.append(rival)
    # Lab Professor (in building)
    prof = NPC(position=(-MAP_W//2+3,0,-MAP_H//2+6), name="Professor Aurelia",
               dialogues=["Welcome to the lab! Choose your starter: Flame, Aqua or Leaf.", "Good luck on your journey!"])
    prof.color = color.cyan
    npcs.append(prof)
    # Glimmerport dock NPC
    npc2 = NPC(position=(MAP_W//2-6,0,-MAP_H//2+6), name="Fisher",
               dialogues=["The tide's been strange. Stay out of the deep water!", "Umbra grunts have been snooping around the docks."])
    npc2.color = color.rgb(200,230,255)
    npcs.append(npc2)
    # Gym Leader in Glimmerport (building)
    gym = NPC(position=(MAP_W//2-30,0,-MAP_H//2+6), name="Marine (GymLeader)",
              dialogues=["You wish to challenge the Gym? Defeat me and take the Tidal Crest!"])
    gym.color = color.azure
    npcs.append(gym)

# ---- UI Helpers ----
dialog_panel = None
dialog_text_entity = None
dialog_speaker_entity = None
dialog_active = False
dialog_lines = []
dialog_cursor = 0

def ui_show_dialog(speaker, lines):
    global dialog_panel, dialog_text_entity, dialog_active, dialog_lines, dialog_cursor, dialog_speaker_entity
    if dialog_panel:
        destroy(dialog_panel)
    dialog_panel = Entity(parent=camera.ui)
    frame = Entity(parent=dialog_panel, model='quad', color=color.rgb(240,240,240), scale=(0.9,0.22), y=-0.7, x=0)
    dialog_speaker_entity = Text(speaker + ":", parent=dialog_panel, origin=(0,-.5), scale=2, x=-0.43, y=-0.57, color=color.black)
    dialog_text_entity = Text('', parent=dialog_panel, origin=(-.5,.5), scale=1.6, x=-0.39, y=-0.75, color=color.black, wrap=40)
    dialog_lines = lines
    dialog_cursor = 0
    dialog_active = True
    show_dialog_line()

def show_dialog_line():
    global dialog_text_entity, dialog_lines, dialog_cursor
    if dialog_text_entity:
        dialog_text_entity.text = dialog_lines[dialog_cursor]

def ui_close_dialog():
    global dialog_panel, dialog_active
    if dialog_panel:
        destroy(dialog_panel)
    dialog_panel = None
    dialog_active = False

# Starter selection UI
starter_panel = None
def ui_show_starter_select():
    global starter_panel
    if starter_panel: destroy(starter_panel)
    starter_panel = Entity(parent=camera.ui)
    bg = Entity(parent=starter_panel, model='quad', color=color.rgb(20,20,30), scale=(0.8,0.38), y=0.02)
    Text("Choose your Starter", parent=starter_panel, scale=2.4, y=0.26)
    # Buttons for starters
    btn_fire = Button(text="Flamkit (Fire)", color=color.orange, parent=starter_panel, scale=(0.25,0.12), position=(-0.33,-0.05))
    btn_water = Button(text="Aquadot (Water)", color=color.azure, parent=starter_panel, scale=(0.25,0.12), position=(0.0,-0.05))
    btn_grass = Button(text="Leafin (Grass)", color=color.lime, parent=starter_panel, scale=(0.25,0.12), position=(0.33,-0.05))

    def choose_fire():
        player.party.append(SPECIES)
        destroy(starter_panel)
        Text("You received Flamkit!", origin=(0,0), scale=2, color=color.white, duration=2)
    def choose_water():
        player.party.append(SPECIES)
        destroy(starter_panel)
        Text("You received Aquadot!", origin=(0,0), scale=2, color=color.white, duration=2)
    def choose_grass():
        player.party.append(SPECIES)
        destroy(starter_panel)
        Text("You received Leafin!", origin=(0,0), scale=2, color=color.white, duration=2)

    btn_fire.on_click = choose_fire
    btn_water.on_click = choose_water
    btn_grass.on_click = choose_grass

# Simple battle UI (turn-based minimal)
battle_panel = None
in_battle = False
battle_active_mon = None
battle_player_mon = None
battle_messages = []

def start_battle(wild_mon):
    global battle_panel, in_battle, battle_active_mon, battle_player_mon, battle_messages
    if in_battle:
        return
    # require at least one mon in party
    if len(player.party) == 0:
        Text("You need a starter to battle!", origin=(0,0), scale=1.5, duration=2)
        return
    in_battle = True
    battle_active_mon = wild_mon
    battle_player_mon = player.party[0]
    battle_messages = [f"A wild {wild_mon.name} appeared!"]
    show_battle_ui()

def show_battle_ui():
    global battle_panel
    if battle_panel: destroy(battle_panel)
    battle_panel = Entity(parent=camera.ui)
    bg = Entity(parent=battle_panel, model='quad', color=color.rgb(20,20,30), scale=(1.0,0.6), y=-0.1)
    # show wild mon
    Text(f"Wild {battle_active_mon.name} L{battle_active_mon.level}", parent=battle_panel, origin=(0,0), scale=1.6, y=0.2)
    # show player mon
    Text(f"{battle_player_mon.name} HP:{battle_player_mon.hp}/{battle_player_mon.max_hp}", parent=battle_panel, origin=(0,0), scale=1.2, y=-0.05, x=-0.4)
    # messages
    msg = "\n".join(battle_messages[-3:])
    Text(msg, parent=battle_panel, origin=(0,0), scale=1.1, y=-0.3)
    # move buttons
    # only show first two moves for simplicity
    m1 = Button(text=battle_player_mon.moves[0].name, parent=battle_panel, scale=(0.22,0.08), position=(-0.32,-0.42))
    if len(battle_player_mon.moves) > 1:
        m2 = Button(text=battle_player_mon.moves[1].name, parent=battle_panel, scale=(0.22,0.08), position=(0.0,-0.42))
    else:
        m2 = None
    flee_btn = Button(text="Run", parent=battle_panel, scale=(0.22,0.08), position=(0.32,-0.42))

    def do_move(mv):
        perform_player_attack(mv)

    m1.on_click = lambda: do_move(battle_player_mon.moves[0])
    if m2:
        m2.on_click = lambda: do_move(battle_player_mon.moves[1])
    flee_btn.on_click = lambda: end_battle(fled=True)

def perform_player_attack(move):
    global battle_messages, battle_active_mon, battle_player_mon
    if move.pp <= 0:
        battle_messages.append("No PP left!")
        show_battle_ui()
        return
    move.pp -= 1
    dmg = max(1, move.power + battle_player_mon.attack - battle_active_mon.defense)
    # small randomness
    dmg = int(dmg * random.uniform(0.85, 1.15))
    battle_active_mon.hp -= dmg
    battle_messages.append(f"{battle_player_mon.name} used {move.name}! {dmg} dmg.")
    if battle_active_mon.is_fainted():
        battle_messages.append(f"Wild {battle_active_mon.name} fainted!")
        show_battle_ui()
        invoke(end_battle, delay=1.2)
        return
    # wild attacks
    wmv = random.choice(battle_active_mon.moves)
    if wmv.pp > 0:
        wmv.pp -= 1
    wdmg = max(1, wmv.power + battle_active_mon.attack - battle_player_mon.defense)
    wdmg = int(wdmg * random.uniform(0.85, 1.15))
    battle_player_mon.hp -= wdmg
    battle_messages.append(f"Wild {battle_active_mon.name} used {wmv.name}! {wdmg} dmg.")
    if battle_player_mon.is_fainted():
        battle_messages.append(f"{battle_player_mon.name} fainted! You blacked out...")
        # simple penalty: heal and return player home
        show_battle_ui()
        invoke(player_recover_penalty, delay=1.4)
        return
    show_battle_ui()

def player_recover_penalty():
    for m in player.party:
        m.hp = m.max_hp
    # teleport to Meadowcross start
    player.position = Vec3(-MAP_W//2+3, 0.5, -MAP_H//2+3)
    end_battle()

def end_battle(fled=False):
    global battle_panel, in_battle, battle_active_mon, battle_player_mon, battle_messages
    if battle_panel:
        destroy(battle_panel)
    in_battle = False
    if fled:
        Text("Got away safely!", origin=(0,0), scale=1.5, duration=1.2)

# ---- Movement & input ----
def input(key):
    global dialog_active, dialog_cursor, dialog_lines
    if key == 'escape':
        application.quit()
    # handle dialog advance
    if dialog_active and key == 'e':
        dialog_cursor += 1
        if dialog_cursor >= len(dialog_lines):
            ui_close_dialog()
        else:
            show_dialog_line()
    # interact with NPCs
    if key == 'e' and not dialog_active and not in_battle:
        # check for nearby npc
        for n in npcs:
            if distance(n.position, player.position) < 1.6:
                n.interact()
                return
    # simple menu: show party with Q
    if key == 'tab':
        show_party_ui()

# keyboard movement handled in update() for consistent stepping detection
movement = {'w':False,'s':False,'a':False,'d':False}

def update():
    global movement, dialog_active, in_battle
    # camera follow
    update_camera()
    # player controls disabled while dialog or in battle or UI active
    if dialog_active or in_battle:
        return

    speed = player.speed * time.dt
    dir_vec = Vec3(0,0,0)
    if held_keys['w']:
        dir_vec += Vec3(0,0,1)
    if held_keys['s']:
        dir_vec += Vec3(0,0,-1)
    if held_keys['a']:
        dir_vec += Vec3(-1,0,0)
    if held_keys['d']:
        dir_vec += Vec3(1,0,0)
    if dir_vec != Vec3(0,0,0):
        dir_vec = dir_vec.normalized()
        new_pos = player.position + dir_vec * speed
        # simple collision: prevent entering water tiles (tile==2) or buildings (3)
        tx = int(round(new_pos.x + MAP_W//2))
        tz = int(round(new_pos.z + MAP_H//2))
        if 0 <= tz < MAP_H and 0 <= tx < MAP_W:
            tile = world[tz][tx]
            if tile == 2 or tile == 3:
                # blocked (no movement)
                pass
            else:
                player.position = new_pos
                # step detection: only trigger once per tile move
                check_for_step(tx, tz)
    # rotate player to movement direction visually
    if held_keys['w']:
        player.rotation_y = 0
    if held_keys['s']:
        player.rotation_y = 180
    if held_keys['a']:
        player.rotation_y = 90
    if held_keys['d']:
        player.rotation_y = 270

# step handling for grass encounters
def check_for_step(tile_x, tile_y):
    # determine tile coordinates relative to world array
    # world indices: [row(y)][col(x)] where row = z + MAP_H//2, col = x + MAP_W//2
    # given tile_x, tile_y already computed as above
    global player
    # convert back safe indexes
    wx = tile_x
    wz = tile_y
    if 0 <= wz < MAP_H and 0 <= wx < MAP_W:
        tile = world[wz][wx]
        if tile == 1:
            # random encounter
            if random.random() < ENCOUNTER_CHANCE:
                # spawn a random wild mon from species pool
                wild = random.choice(SPECIES)
                start_battle(wild)

# ---- Utility UI: show party ----
def show_party_ui():
    if len(player.party) == 0:
        Text("You have no Pokémon. Visit Professor Aurelia to choose a starter.", origin=(0,0), scale=1.2, duration=2.4)
        return
    panel = Entity(parent=camera.ui)
    bg = Entity(parent=panel, model='quad', color=color.rgb(10,10,30), scale=(0.8,0.55), y=0)
    Text("Party", parent=panel, scale=2.4, y=0.22)
    for i,m in enumerate(player.party):
        Text(f"{m.name} L{m.level} HP:{m.hp}/{m.max_hp}", parent=panel, y=0.08 - i*0.10, scale=1.2, x=-0.3)
    # auto-destroy panel after 3.5s
    invoke(destroy, panel, delay=3.5)

# ---- Initialization ----
spawn_world()
place_npcs()

# show starter UI at launch
ui_show_starter_select()

# little help text
Text("Move: WASD | Interact: E | Party: TAB | Quit: ESC", origin=(-0.8,0.45), scale=1.1, color=color.white, background=True)

# ---- run app ----
app.run()
