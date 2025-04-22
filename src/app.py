#!/usr/bin/env python
import curses
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import librosa
import numpy as np
import argparse
from datetime import datetime
from fs import FS
from audio_processor import SirenLooper
from models import LoopCandidate, ProcessResult


class AudioLooperApp:
    """
    Main application class that orchestrates the audio looping process.
    """
    def __init__(self) -> None:
        # Register signal handler for clean exit before anything else
        signal.signal(signal.SIGINT, self._handle_exit)
        
        self.fs = FS()  # Ensure FS is initialized first
        self.args = self._parse_arguments()
        
        logging.info(f"Project root determined as: {self.fs.root}")
        
        self.audio_file: Optional[str] = self.args.audio
        self.target_duration_sec: Optional[float] = self.args.target
        self.min_loop_duration: float = self.args.min_loop_duration
        self.peak_threshold: float = self.args.peak_threshold

    def _handle_exit(self, signum, frame) -> None:
        """
        Handle clean exit on keyboard interrupt.
        """
        print("\nExiting cleanly. Goodbye!")
        sys.exit(0)

    def _parse_arguments(self) -> argparse.Namespace:
        """
        Parse command line arguments.
        
        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description="Create a seamlessly looped audio file.",
            epilog=f"Example usage: python app.py --audio {self.fs.sound_input_folder / 'phaser2.wav'} --target 30"
        )
        parser.add_argument(
            "--audio",
            type=str,
            default=None,
            help=f"Path to the input audio file (default: None)"
        )
        parser.add_argument(
            "--target",
            type=float,
            default=None,
            help="Target duration in seconds for the looped audio (default: None)"
        )
        parser.add_argument(
            "--min-loop-duration",
            type=float,
            default=None,
            help="Minimum loop duration in seconds. If not set, defaults to 0.1s."
        )
        parser.add_argument(
            "--peak-threshold",
            type=float,
            default=0.1,  # Default peak height threshold for loop extraction
            help="Peak height threshold for loop extraction (default: 0.1)"
        )
        return parser.parse_args()

    def _retry_loop_detection(self, looper: SirenLooper) -> bool:
        """
        Retry loop detection with progressively relaxed parameters.
        
        Args:
            looper: SirenLooper instance
            
        Returns:
            True if loop points were found, False otherwise
        """
        retries = 3
        for attempt in range(1, retries + 1):
            looper.min_loop_duration_sec /= 2
            looper.peak_height_threshold *= 0.8
            
            logging.info(
                f"Retry {attempt}/{retries} with adjusted parameters: "
                f"min_loop_duration={looper.min_loop_duration_sec:.2f}s, "
                f"threshold={looper.peak_height_threshold:.2f}"
            )
            
            try:
                looper.find_seamless_loop_points()
                if looper.loop_candidates:
                    return True
            except Exception as e:
                logging.error(f"Error during retry {attempt}: {e}")
                
        return False

    def run(self) -> None:
        """
        Main method to run the application using a static curses TUI interface.
        """
        import curses
        import subprocess
        # Initialize log storage and scrolling
        log_messages: List[str] = []
        scroll_pos = 0

        def tui_main(stdscr):
            # Initialize curses settings
            curses.curs_set(0)
            stdscr.nodelay(False)
            stdscr.keypad(True)
            # Clear screen to apply background
            stdscr.clear(); stdscr.refresh()
            # Initialize color scheme and modal state
            curses.start_color(); curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, -1)  # default pane
            curses.init_pair(2, curses.COLOR_GREEN, -1)  # active pane or modal
            curses.init_pair(3, curses.COLOR_BLUE, -1)   # origin pane during modal
            in_modal = False; modal_origin = None
            # Initialize dynamic file lists
            player_proc = None  # Track playback subprocess

            # State variables
            focus = 'input'
            idx_in = 0
            idx_out = 0
            nonlocal scroll_pos
            nonlocal log_messages

            # Initialize dimensions and windows
            max_y, max_x = stdscr.getmaxyx()
            legend_h = 1
            gap = 2
            log_h = 7
            pane_h = max_y - legend_h - log_h
            pane_w = (max_x - gap) // 2

            # Create legend window at top
            legend_win = curses.newwin(legend_h, max_x, 0, 0)
            input_win = curses.newwin(pane_h, pane_w, legend_h, 0); input_win.keypad(True)
            output_win = curses.newwin(pane_h, pane_w, legend_h, pane_w + gap); output_win.keypad(True)
            # Create log window below panes
            log_win = curses.newwin(log_h, max_x, legend_h + pane_h, 0); log_win.keypad(True)

            # Helper to render log pane with scrolling
            def render_logs():
                # color log pane based on focus
                if in_modal and modal_origin == 'log': cp = curses.color_pair(3)
                elif focus == 'log': cp = curses.color_pair(2)
                else: cp = curses.color_pair(1)
                log_win.bkgd(' ', cp)
                log_win.clear(); log_win.box(); log_win.addstr(0, 2, "Log", cp)
                # Determine visible log lines based on scroll_pos
                total = len(log_messages)
                height = log_h - 2
                start = scroll_pos
                end = min(scroll_pos + height, total)
                for i, line in enumerate(log_messages[start:end]):
                    log_win.addstr(1+i, 2, line[:max_x-4])
                # Draw scroll arrows if needed
                if total > height:
                    # up arrow if not at top
                    if scroll_pos > 0:
                        log_win.addch(1, max_x-2, '^')
                    # down arrow if not at bottom
                    if end < total:
                        log_win.addch(log_h-2, max_x-2, 'v')
                log_win.refresh()

            # Initialize scroll positions for panes
            scroll_in = 0; scroll_out = 0
            # Initial render
            render_logs()

            while True:
                # Refresh file lists to detect new files
                files_in = self.fs.get_sound_input_files()
                files_out = list(self.fs.sound_output_folder.glob('*.wav'))

                # Draw input pane with scrolling and color based on focus/modal
                # determine color pair for input pane
                if in_modal and modal_origin == 'input': cp = curses.color_pair(3)
                elif focus == 'input': cp = curses.color_pair(2)
                else: cp = curses.color_pair(1)
                input_win.bkgd(' ', cp)
                input_win.clear(); input_win.box(); input_win.addstr(0, 2, "Input", cp)
                visible = pane_h - 2
                # adjust scroll if cursor moved out of view
                if idx_in < scroll_in: scroll_in = idx_in
                elif idx_in >= scroll_in + visible: scroll_in = idx_in - visible + 1
                # determine slice
                disp_in = files_in[scroll_in:scroll_in + visible]
                for j, f in enumerate(disp_in):
                    actual = scroll_in + j
                    marker = '>' if focus == 'input' and actual == idx_in else ' '
                    input_win.addstr(1 + j, 2, f"{marker} {f.name}")
                # draw simple scrollbar arrows
                if len(files_in) > visible:
                    if scroll_in > 0: input_win.addch(1, pane_w - 2, '^')
                    if scroll_in + visible < len(files_in): input_win.addch(pane_h - 2, pane_w - 2, 'v')
                input_win.refresh()

                # Draw output pane with scrolling and color based on focus/modal
                if in_modal and modal_origin == 'output': cp = curses.color_pair(3)
                elif focus == 'output': cp = curses.color_pair(2)
                else: cp = curses.color_pair(1)
                output_win.bkgd(' ', cp)
                output_win.clear(); output_win.box(); output_win.addstr(0, 2, "Output", cp)
                visible_o = pane_h - 2
                if idx_out < scroll_out: scroll_out = idx_out
                elif idx_out >= scroll_out + visible_o: scroll_out = idx_out - visible_o + 1
                disp_out = files_out[scroll_out:scroll_out + visible_o]
                for j, f in enumerate(disp_out):
                    actual = scroll_out + j
                    marker = '>' if focus == 'output' and actual == idx_out else ' '
                    output_win.addstr(1 + j, 2, f"{marker} {f.name}")
                if len(files_out) > visible_o:
                    if scroll_out > 0: output_win.addch(1, pane_w - 2, '^')
                    if scroll_out + visible_o < len(files_out): output_win.addch(pane_h - 2, pane_w - 2, 'v')
                output_win.refresh()

                # Draw legend at bottom
                legend_win.clear()
                legend = "p-play  q-quit"
                if focus == 'input':
                    legend += "  l-loop"
                elif focus == 'output':
                    legend += "  d-delete"
                legend_win.addstr(0, 2, legend)
                legend_win.refresh()

                # Handle user input
                key = stdscr.getch()
                if key == ord('q'):
                    break
                elif key == 9:  # Tab key cycles focus among input, output, log
                    if focus == 'input':
                        focus = 'output'
                    elif focus == 'output':
                        focus = 'log'
                    else:
                        focus = 'input'
                elif key in (curses.KEY_UP, curses.KEY_DOWN):
                    if focus == 'log':
                        # Scroll log pane
                        delta = -1 if key == curses.KEY_UP else 1
                        max_scroll = max(0, len(log_messages)-(log_h-2))
                        scroll_pos = min(max(scroll_pos+delta, 0), max_scroll)
                        render_logs()
                    else:
                        # Stop playback on navigation
                        if player_proc:
                            player_proc.terminate()
                            player_proc = None
                        if focus == 'input' and files_in:
                            idx_in = (idx_in - 1) % len(files_in) if key == curses.KEY_UP else (idx_in + 1) % len(files_in)
                        elif focus == 'output' and files_out:
                            idx_out = (idx_out - 1) % len(files_out) if key == curses.KEY_UP else (idx_out + 1) % len(files_out)
                elif key == ord('p'):
                    # Toggle playback for selected file and log actions
                    path = str(files_in[idx_in] if focus == 'input' else files_out[idx_out])
                    ts = datetime.now().strftime("%H:%M:%S")
                    if player_proc:
                        player_proc.terminate()
                        player_proc = None
                        log_messages.append(f"{ts} Stopped playing {path}")
                    else:
                        player_proc = subprocess.Popen(['aplay', '-q', path])
                        scroll_pos = 0
                        log_messages.append(f"{ts} Started playing {path}")
                    render_logs()
                elif key == ord('l') and focus == 'input':
                    # Initialize looper for selected file
                    sel_file = files_in[idx_in]
                    looper = SirenLooper(sel_file.name, self.fs,
                                         min_loop_duration_sec=self.min_loop_duration if self.min_loop_duration else 0.1,
                                         peak_height_threshold=self.peak_threshold)
                    # Find loop points
                    log_win.clear(); log_win.box(); log_win.addstr(0,2,"Log"); log_win.addstr(1,2,"Finding loop points..."); log_win.refresh()
                    candidates = looper.find_seamless_loop_points()
                    if not candidates:
                        # Attempt retry with relaxed parameters
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_messages.append(f"{ts} No loop points found, retrying with relaxed parameters")
                        scroll_pos = 0; render_logs()
                        if self._retry_loop_detection(looper):
                            candidates = looper.loop_candidates
                            ts = datetime.now().strftime("%H:%M:%S")
                            log_messages.append(f"{ts} Found loop points after retries")
                            scroll_pos = 0; render_logs()
                        else:
                            ts = datetime.now().strftime("%H:%M:%S")
                            log_messages.append(f"{ts} No loop points found after retries")
                            scroll_pos = 0; render_logs()
                            continue
                    # If only one candidate, skip selection modal
                    if len(candidates) == 1:
                        chosen = candidates[0]
                    else:
                        # Modal for selecting loop point without cancel option
                        num_c = len(candidates)
                        modal_h = num_c + 3; modal_w = max_x // 2
                        my = (pane_h - modal_h) // 2; mx = (max_x - modal_w) // 2
                        modal = curses.newwin(modal_h, modal_w, my, mx); modal.keypad(True)
                        # enter modal state from input pane and color it
                        in_modal = True; modal_origin = 'input'
                        modal.bkgd(' ', curses.color_pair(2))
                        sel_idx = 0
                        modal_player = None
                        aborted_modal = False  # allow user to cancel modal with q
                        while True:
                            modal.clear(); modal.box(); modal.addstr(0,2,"Select Loop Point")
                            for j, c in enumerate(candidates):
                                s = c.start/looper.sr; e = c.end/looper.sr
                                label = f"{j+1}. {s:.2f}-{e:.2f}" + (" (best)" if j==0 else "")
                                marker = '>' if j==sel_idx else ' '
                                modal.addstr(1+j,2,f"{marker} {label}")
                            modal.addstr(modal_h-2,2,"Enter=select  p-play"); modal.refresh()
                            mk = modal.getch()
                            if mk == ord('q'):
                                aborted_modal = True
                                break
                            if mk in (curses.KEY_UP, curses.KEY_DOWN):
                                sel_idx = (sel_idx-1)%num_c if mk==curses.KEY_UP else (sel_idx+1)%num_c
                            elif mk == ord('p'):
                                # toggle preview
                                if modal_player:
                                    modal_player.terminate(); modal_player=None
                                else:
                                    import tempfile, soundfile as sf
                                    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                                    seg = looper.y[candidates[sel_idx].start:candidates[sel_idx].end]
                                    sf.write(tmp.name, seg, looper.sr)
                                    modal_player = subprocess.Popen(['aplay', '-q', tmp.name])
                            elif mk in (10,13):  # Enter
                                chosen = candidates[sel_idx]; break
                        modal.clear(); modal.refresh(); del modal
                        # exit modal state
                        in_modal = False; modal_origin = None
                        if aborted_modal:
                            # user cancelled modal, return to main UI
                            continue
                    # Prompt for target duration in a popup window
                    loop_d = chosen.duration_seconds(looper.sr)
                    pw = 40; ph = 5
                    py = (pane_h - ph)//2 + legend_h; px = (max_x - pw)//2
                    pw_win = curses.newwin(ph, pw, py, px); pw_win.keypad(True); pw_win.box()
                    # enter modal state for target input and color it
                    in_modal = True; modal_origin = 'input'
                    pw_win.bkgd(' ', curses.color_pair(2))
                    pw_win.addstr(1,2,f"Enter target duration >= {2*loop_d:.2f}s:")
                    pw_win.addstr(2,2,"> "); pw_win.refresh()
                    # numeric-only input for target duration, allow 'q' to abort
                    curses.curs_set(1)
                    inp_str = ""
                    aborted_input = False
                    while True:
                        pw_win.move(2, 4 + len(inp_str)); pw_win.refresh()
                        mk = pw_win.getch()
                        if mk in (10,13):  # Enter
                            break
                        elif mk == ord('q'):
                            aborted_input = True; break
                        elif mk in (curses.KEY_BACKSPACE, 127):
                            if inp_str:
                                inp_str = inp_str[:-1]
                                pw_win.move(2, 4 + len(inp_str)); pw_win.delch()
                        elif chr(mk).isdigit() or mk == ord('.'):
                            if len(inp_str) < 10:
                                inp_str += chr(mk)
                                pw_win.addch(2, 4 + len(inp_str)-1, mk)
                    curses.curs_set(0)
                    pw_win.clear(); pw_win.refresh(); del pw_win
                    # exit modal state
                    in_modal = False; modal_origin = None
                    if aborted_input:
                        # user aborted target input
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_messages.append(f"{ts} Cancelled target input")
                        scroll_pos = 0; render_logs()
                        continue
                    inp_str = inp_str.strip()
                    try:
                        target = float(inp_str)
                        if target < 2*loop_d:
                            log_win.clear(); log_win.box(); log_win.addstr(1,2,"Target too short. Try again."); log_win.refresh(); continue
                    except:
                        log_win.clear(); log_win.box(); log_win.addstr(1,2,"Invalid input. Try again."); log_win.refresh(); continue
                    # Process and save with custom output name
                    log_win.clear(); log_win.box(); log_win.addstr(0,2,"Log"); log_win.addstr(1,2,"Processing and saving..."); log_win.refresh()
                    output_name = f"{sel_file.stem}_loop{sel_idx+1}_{int(target)}s.wav"
                    result = looper.process_and_save(target, output_file=output_name)
                    ts = datetime.now().strftime("%H:%M:%S")
                    log_messages.append(f"{ts} Saved looped file: {result.audio_path}")
                    scroll_pos = 0
                    render_logs()
                    # Update output files list
                    files_out[:] = list(self.fs.sound_output_folder.glob('*.wav'))
                elif key == ord('d') and focus == 'output' and files_out:
                    # Confirm deletion of selected output file
                    to_delete = files_out[idx_out]
                    name = to_delete.name
                    mh, mw = 5, max(len(name)+20, 30)
                    # center modal on entire screen
                    y = (max_y - mh) // 2
                    x = (max_x - mw) // 2
                    modal = curses.newwin(mh, mw, y, x); modal.keypad(True)
                    # enter modal state from output pane and color it
                    in_modal = True; modal_origin = 'output'
                    modal.bkgd(' ', curses.color_pair(2))
                    sel_yes = True; aborted = False
                    while True:
                        modal.clear(); modal.box()
                        modal.addstr(1, 2, f"Delete '{name}'?")
                        # Draw Yes/No buttons
                        yes_attr = curses.A_REVERSE if sel_yes else curses.A_NORMAL
                        no_attr = curses.A_REVERSE if not sel_yes else curses.A_NORMAL
                        modal.addstr(3, mw//2 - 5, " Yes ", yes_attr)
                        modal.addstr(3, mw//2 + 1, " No ", no_attr)
                        modal.refresh()
                        mk = modal.getch()
                        if mk == ord('q'):
                            aborted = True; break
                        if mk == 9 or mk in (curses.KEY_LEFT, curses.KEY_RIGHT):
                            sel_yes = not sel_yes
                        elif mk in (10, 13):
                            break
                    modal.clear(); modal.refresh(); del modal
                    # exit modal state
                    in_modal = False; modal_origin = None
                    if aborted or not sel_yes:
                        continue
                    # Delete file and log
                    to_delete.unlink()
                    ts = datetime.now().strftime("%H:%M:%S")
                    log_messages.append(f"{ts} Deleted {name}")
                    scroll_pos = 0; render_logs()
                    # Adjust selection index if needed
                    if idx_out >= len(files_out): idx_out = max(0, len(files_out)-1)

            # Cleanup curses
            # Removed redundant curses.endwin() call

        # Launch the TUI (wrapper handles cleanup/endwin)
        curses.wrapper(tui_main)