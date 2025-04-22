import curses
import tempfile
import subprocess
import soundfile as sf

class SelectionModal:
    def __init__(self, stdscr, candidates, looper):
        self.stdscr = stdscr
        self.candidates = candidates
        self.looper = looper
        self.selected = 0
        self.aborted = False

    def show(self):
        num = len(self.candidates)
        max_y, max_x = self.stdscr.getmaxyx()
        modal_h = num + 3
        modal_w = max_x // 2
        starty = (max_y - modal_h) // 2
        startx = (max_x - modal_w) // 2
        win = curses.newwin(modal_h, modal_w, starty, startx)
        win.keypad(True)
        win.bkgd(' ', curses.color_pair(2))
        modal_player = None
        while True:
            win.clear(); win.box(); win.addstr(0, 2, "Select Loop Point")
            for idx, c in enumerate(self.candidates):
                s = c.start / self.looper.sr; e = c.end / self.looper.sr
                label = f"{idx+1}. {s:.2f}-{e:.2f}" + (" (best)" if idx == 0 else "")
                marker = '>' if idx == self.selected else ' '
                win.addstr(1 + idx, 2, f"{marker} {label}")
            win.addstr(modal_h - 2, 2, "Enter=select  p-play"); win.refresh()
            k = win.getch()
            if k == ord('q'):
                self.aborted = True; break
            elif k in (curses.KEY_UP, curses.KEY_DOWN):
                if k == curses.KEY_UP:
                    self.selected = (self.selected - 1) % num
                else:
                    self.selected = (self.selected + 1) % num
            elif k == ord('p'):
                if modal_player:
                    modal_player.terminate(); modal_player = None
                else:
                    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                    seg = self.looper.y[self.candidates[self.selected].start:self.candidates[self.selected].end]
                    sf.write(tmp.name, seg, self.looper.sr)
                    modal_player = subprocess.Popen(['aplay', '-q', tmp.name])
            elif k in (10, 13):
                break
        win.clear(); win.refresh(); del win
        return None if self.aborted else self.selected

class PromptModal:
    def __init__(self, stdscr, prompt):
        self.stdscr = stdscr
        self.prompt = prompt
        self.aborted = False

    def show(self):
        max_y, max_x = self.stdscr.getmaxyx()
        ph, pw = 5, 40
        starty = (max_y - ph) // 2
        startx = (max_x - pw) // 2
        win = curses.newwin(ph, pw, starty, startx)
        win.keypad(True); win.box(); win.bkgd(' ', curses.color_pair(2))
        win.addstr(1, 2, self.prompt)
        win.addstr(2, 2, "> "); win.refresh()
        curses.curs_set(1)
        inp = ""
        while True:
            win.move(2, 4 + len(inp)); win.refresh()
            k = win.getch()
            if k in (10, 13): break
            elif k == ord('q'):
                self.aborted = True; break
            elif k in (curses.KEY_BACKSPACE, 127):
                if inp:
                    inp = inp[:-1]; win.delch(2, 4 + len(inp))
            else:
                ch = chr(k)
                if ch.isdigit() or ch == '.':
                    inp += ch; win.addstr(2, 4 + len(inp) - 1, ch)
        curses.curs_set(0)
        win.clear(); win.refresh(); del win
        return None if self.aborted else inp.strip()

class ConfirmModal:
    def __init__(self, stdscr, prompt):
        self.stdscr = stdscr
        self.prompt = prompt
        self.confirm = True
        self.aborted = False

    def show(self):
        max_y, max_x = self.stdscr.getmaxyx()
        mh, mw = 5, max(len(self.prompt) + 20, 30)
        starty = (max_y - mh) // 2
        startx = (max_x - mw) // 2
        win = curses.newwin(mh, mw, starty, startx)
        win.keypad(True); win.box(); win.bkgd(' ', curses.color_pair(2))
        while True:
            win.clear(); win.box(); win.addstr(1, 2, self.prompt)
            yes_attr = curses.A_REVERSE if self.confirm else curses.A_NORMAL
            no_attr = curses.A_REVERSE if not self.confirm else curses.A_NORMAL
            win.addstr(3, mw // 2 - 5, " Yes ", yes_attr)
            win.addstr(3, mw // 2 + 1, " No ", no_attr)
            win.refresh()
            k = win.getch()
            if k == ord('q'):
                self.aborted = True; break
            elif k in (9, curses.KEY_LEFT, curses.KEY_RIGHT):
                self.confirm = not self.confirm
            elif k in (10, 13):
                break
        win.clear(); win.refresh(); del win
        return False if self.aborted else self.confirm