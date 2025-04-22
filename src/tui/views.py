import curses

class BasePane:
    def __init__(self, win, title):
        self.win = win
        self.title = title
        self.focus = False
        self.in_modal = False
        self.modal_origin = None

    def set_focus(self, focused):
        self.focus = focused

    def set_modal(self, in_modal, modal_origin):
        self.in_modal = in_modal
        self.modal_origin = modal_origin

    def render_title(self):
        if self.in_modal and self.modal_origin == self.title.lower():
            cp = curses.color_pair(3)
        elif self.focus:
            cp = curses.color_pair(2)
        else:
            cp = curses.color_pair(1)
        self.win.bkgd(' ', cp)
        self.win.clear()
        self.win.box()
        self.win.addstr(0, 2, self.title, cp)


class ListPane(BasePane):
    def __init__(self, win, title):
        super().__init__(win, title)
        self.items = []
        self.selected = 0
        self.scroll = 0

    def set_items(self, items):
        self.items = items
        if self.selected >= len(items):
            self.selected = max(0, len(items) - 1)
        self._adjust_scroll()

    def _adjust_scroll(self):
        h, _ = self.win.getmaxyx()
        visible = h - 2
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1

    def render(self):
        self.render_title()
        h, w = self.win.getmaxyx()
        visible = h - 2
        disp = self.items[self.scroll:self.scroll + visible]
        for idx, item in enumerate(disp):
            actual = self.scroll + idx
            marker = '>' if self.focus and actual == self.selected else ' '
            name = getattr(item, 'name', str(item))
            self.win.addstr(1 + idx, 2, f"{marker} {name}")
        if len(self.items) > visible:
            if self.scroll > 0:
                self.win.addch(1, w - 2, '^')
            if self.scroll + visible < len(self.items):
                self.win.addch(h - 2, w - 2, 'v')
        self.win.refresh()

    def handle_key(self, key):
        if key not in (curses.KEY_UP, curses.KEY_DOWN):
            return
        if not self.items:
            return
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.items)
        else:
            self.selected = (self.selected + 1) % len(self.items)
        self._adjust_scroll()

    def get_selected(self):
        if not self.items:
            return None
        return self.items[self.selected]


class LogPane(BasePane):
    def __init__(self, win):
        super().__init__(win, 'Log')
        self.messages = []
        self.scroll = 0

    def add_message(self, message):
        self.messages.append(message)
        self.scroll = 0

    def handle_key(self, key):
        if key not in (curses.KEY_UP, curses.KEY_DOWN):
            return
        h, _ = self.win.getmaxyx()
        height = h - 2
        max_scroll = max(0, len(self.messages) - height)
        delta = -1 if key == curses.KEY_UP else 1
        self.scroll = max(0, min(self.scroll + delta, max_scroll))

    def render(self):
        if self.in_modal and self.modal_origin == 'log':
            cp = curses.color_pair(3)
        elif self.focus:
            cp = curses.color_pair(2)
        else:
            cp = curses.color_pair(1)
        self.win.bkgd(' ', cp)
        self.win.clear()
        self.win.box()
        self.win.addstr(0, 2, self.title, cp)
        h, w = self.win.getmaxyx()
        height = h - 2
        start = self.scroll
        end = min(start + height, len(self.messages))
        for idx, line in enumerate(self.messages[start:end]):
            self.win.addstr(1 + idx, 2, line[:w - 4])
        if len(self.messages) > height:
            if self.scroll > 0:
                self.win.addch(1, w - 2, '^')
            if end < len(self.messages):
                self.win.addch(h - 2, w - 2, 'v')
        self.win.refresh()


class LegendPane:
    def __init__(self, win):
        self.win = win

    def render(self, focus):
        self.win.clear()
        legend = "p-play  q-quit"
        if focus == 'input':
            legend += "  l-loop"
        elif focus == 'output':
            legend += "  d-delete"
        self.win.addstr(0, 2, legend)
        self.win.refresh()