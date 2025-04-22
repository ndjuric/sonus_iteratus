#!/usr/bin/env python

class TUI:
    """Text-based UI controller for the AudioLooperApp."""
    def __init__(self, app):
        self.app = app
        self.fs = app.fs
        self.min_loop_duration = app.min_loop_duration
        self.peak_threshold = app.peak_threshold

    def start(self):
        import curses
        curses.wrapper(self._main)

    def _main(self, stdscr):
        stdscr.clear()
        stdscr.refresh()
        import curses
        import subprocess
        import tempfile
        from datetime import datetime
        import soundfile as sf
        from audio_processor import SirenLooper
        from tui.views import ListPane, LogPane, LegendPane
        from tui.modals import SelectionModal, PromptModal, ConfirmModal

        # Initialize curses settings
        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_BLUE, -1)

        # Determine layout dimensions
        max_y, max_x = stdscr.getmaxyx()
        legend_h = 1
        gap = 2
        log_h = 7
        pane_h = max_y - legend_h - log_h
        pane_w = (max_x - gap) // 2

        # Create windows
        legend_win = curses.newwin(legend_h, max_x, 0, 0)
        input_win = curses.newwin(pane_h, pane_w, legend_h, 0); input_win.keypad(True)
        output_win = curses.newwin(pane_h, pane_w, legend_h, pane_w + gap); output_win.keypad(True)
        log_win = curses.newwin(log_h, max_x, legend_h + pane_h, 0); log_win.keypad(True)

        # Instantiate view components
        legend_pane = LegendPane(legend_win)
        input_pane = ListPane(input_win, 'Input')
        output_pane = ListPane(output_win, 'Output')
        log_pane = LogPane(log_win)

        player_proc = None
        focus = 'input'

        # Main event loop
        while True:
            files_in = self.fs.get_sound_input_files()
            files_out = list(self.fs.sound_output_folder.glob('*.wav'))

            # Update pane states
            input_pane.set_items(files_in)
            input_pane.set_focus(focus == 'input')
            output_pane.set_items(files_out)
            output_pane.set_focus(focus == 'output')
            log_pane.set_focus(focus == 'log')

            # Render panes
            legend_pane.render(focus)
            input_pane.render()
            output_pane.render()
            log_pane.render()

            # Handle input
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == 9:  # Tab
                focus = {'input': 'output', 'output': 'log', 'log': 'input'}[focus]
            elif key in (curses.KEY_UP, curses.KEY_DOWN):
                if focus == 'log':
                    log_pane.handle_key(key)
                else:
                    if player_proc:
                        player_proc.terminate()
                        player_proc = None
                    if focus == 'input':
                        input_pane.handle_key(key)
                    elif focus == 'output':
                        output_pane.handle_key(key)
            elif key == ord('p'):
                pane = input_pane if focus == 'input' else output_pane
                selected = pane.get_selected()
                if selected:
                    path = str(selected)
                    ts = datetime.now().strftime("%H:%M:%S")
                    if player_proc:
                        player_proc.terminate()
                        player_proc = None
                        log_pane.add_message(f"{ts} Stopped playing {path}")
                    else:
                        player_proc = subprocess.Popen(['aplay', '-q', path])
                        log_pane.add_message(f"{ts} Started playing {path}")
            elif key == ord('l') and focus == 'input':
                selected = input_pane.get_selected()
                if not selected:
                    continue
                looper = SirenLooper(
                    selected.name,
                    self.fs,
                    min_loop_duration_sec=self.min_loop_duration or 0.1,
                    peak_height_threshold=self.peak_threshold
                )
                ts = datetime.now().strftime("%H:%M:%S")
                log_pane.add_message(f"{ts} Finding loop points...")
                candidates = looper.find_seamless_loop_points()
                if not candidates:
                    log_pane.add_message(f"{ts} No loop points found, retrying with relaxed parameters")
                    if self.app._retry_loop_detection(looper):
                        candidates = looper.loop_candidates
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_pane.add_message(f"{ts} Found loop points after retries")
                    else:
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_pane.add_message(f"{ts} No loop points found after retries")
                        continue
                if len(candidates) > 1:
                    sel_idx = SelectionModal(stdscr, candidates, looper).show()
                    if sel_idx is None:
                        continue
                    chosen = candidates[sel_idx]
                else:
                    chosen = candidates[0]
                loop_d = chosen.duration_seconds(looper.sr)
                prompt = PromptModal(
                    stdscr,
                    f"Enter target duration >= {2 * loop_d:.2f}s:"
                ).show()
                if prompt is None:
                    ts = datetime.now().strftime("%H:%M:%S")
                    log_pane.add_message(f"{ts} Cancelled target input")
                    continue
                try:
                    target = float(prompt)
                    if target < 2 * loop_d:
                        log_pane.add_message("Target too short. Try again.")
                        continue
                except ValueError:
                    log_pane.add_message("Invalid input. Try again.")
                    continue
                ts = datetime.now().strftime("%H:%M:%S")
                log_pane.add_message(f"{ts} Processing and saving...")
                output_name = f"{selected.stem}_loop{(candidates.index(chosen)+1)}_{int(target)}s.wav"
                result = looper.process_and_save(target, output_file=output_name)
                ts = datetime.now().strftime("%H:%M:%S")
                log_pane.add_message(f"{ts} Saved looped file: {result.audio_path}")
            elif key == ord('d') and focus == 'output':
                selected = output_pane.get_selected()
                if not selected:
                    continue
                confirm = ConfirmModal(
                    stdscr,
                    f"Delete '{selected.name}'?"
                ).show()
                if not confirm:
                    continue
                selected.unlink()
                ts = datetime.now().strftime("%H:%M:%S")
                log_pane.add_message(f"{ts} Deleted {selected.name}")
