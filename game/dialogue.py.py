from ursina import *

class DialogueBox(Entity):
    def __init__(self, **kwargs):
        super().__init__(parent=camera.ui, enabled=False)
        self.bg = Entity(parent=self, model='quad', color=color.black66,
                         scale=(1.5, 0.3), position=(0, -0.4), z=-1)
        self.text_entity = Text(parent=self, text='', scale=1.2,
                                position=(-0.7, -0.4), origin=(-.5, .5), line_height=1.2)
        self.current_line = 0
        self.lines = []
        self.on_finish = None

    def start(self, lines, on_finish=None):
        self.lines = lines
        self.current_line = 0
        self.on_finish = on_finish
        self.enabled = True
        self._show_line()

    def _show_line(self):
        if self.current_line < len(self.lines):
            self.text_entity.text = self.lines[self.current_line]
        else:
            self.enabled = False
            if self.on_finish:
                self.on_finish()

    def input(self, key):
        if not self.enabled:
            return
        if key == 'space' or key == 'enter':
            self.current_line += 1
            self._show_line()
