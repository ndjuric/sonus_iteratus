# 🎵 Sonus Iteratus 🔄

[![GitHub Stars](https://img.shields.io/github/stars/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/network)
[![GitHub Issues](https://img.shields.io/github/issues/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/issues)
[![License](https://img.shields.io/github/license/ndjuric/sonus_iteratus?style=flat-square)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue?style=flat-square&logo=python)](https://www.python.org)

A simple way to find seamless audio subsamples inside your already short audio samples and generate perfect, hour-long (or more!) loops! 🚀

**Give it a ⭐️ if you like it!**

## 📖 Table of Contents

1.  [Introduction](#1-introduction)
2.  [Background: A Developer's Audio Adventure](#2-background)
3.  [Key Features: Precision Looping in the Terminal](#3-key-features)
4.  [Functionality: Under the Hood](#4-functionality)
5.  [Workflow: Your Looping Journey](#5-workflow)
    * [5.1 Input Selection](#51-input-selection)
    * [5.2 Looping Point Analysis: The Algorithmic Heart](#52-looping-point-analysis)
    * [5.3 Subsample Selection: Fine-Grained Control](#53-subsample-selection)
    * [5.4 Output Duration: Tailoring Your Soundscape](#54-output-duration)
    * [5.5 Output Management: Your Sonic Command Center](#55-output-management)
6.  [Demo: See Audionaut in Action](#6-demo)
7.  [Installation: Get Started in Minutes](#7-installation)
8.  [License](#8-license)
9.  [Contributing: Join the Noise!](#9-contributing)

## 1. 🚀 Introduction

`Sonus Iteratus` is a command-line tool with a terminal user interface, designed for meticulous and highly customizable looping of audio subsamples.

This tool provides a straightforward, terminal-based UI for:

* 📂 Selecting `.wav` audio samples from the `data/sound/input/` folder
* 🎯 Detecting optimal, seamless looping points with algorithmic precision
* 🔄 Looping those samples for a user-specified duration (yes, even for hours 😉), and saving the output to `data/sound/output/`

## 2. 🤔 Background: A Developer's Audio Adventure

The story of `Sonus Iteratus` begins with a friend, a seasoned engineer, caught up in the events surrounding the [Novi Sad bridge collapse](https://sh.wikipedia.org/wiki/Uru%C5%Aavanje_nadstre%C5%A1nice_%C5%BDelezni%C4%8Dke_stanice_Novi_Sad). Tasked with creating a clean, extended loop of a siren recording, I found myself seeking a more programmatic and controlled approach than traditional audio editors offered.

This project became an exploration of audio manipulation from a developer's perspective, prioritizing precision and automation.

## 3. 🎧 Key Features: Precision Looping in the Terminal

`Sonus Iteratus` offers:

* **Terminal-Centric Workflow:** A streamlined, keyboard-driven interface for efficient audio manipulation.
* **Algorithmic Loop Detection:** A core algorithm to identify optimal, seamless looping points.
* **Granular Control:** Fine-tune your loops with precise subsample selection and duration control.
* **Clear Output Management:** Easily manage generated audio files within the terminal.

## 4. ✨ Functionality: Under the Hood

`Sonus Iteratus` presents a clean, terminal user interface (TUI) structured for efficiency:

* **📂 Input Pane (Left):** Displays all `.wav` audio files residing in the `data/sound/input/` directory.
* **📭 Output Pane (Right):** Shows the generated looped audio files, saved to the `data/sound/output/` directory.
* **📜 Log Pane (Bottom):** Provides helpful logs, feedback, and status updates.
* **💡 Legend:** A context-aware guide to keybindings and actions, dynamically updating to ease your looping journey.

## 5. ⚙️ Workflow: Your Looping Journey

The TUI guides you through a clear, iterative looping process:

### 5.1 📥 Input Selection

In the left pane, wield these commands:

* `q`: Quit the tool (once you've finished your symphony 🤘).
* `p`: Preview the selected audio sample (give it a listen 👂).
* `l`: Unleash the looping algorithm! (the magic happens here ✨).

### 5.2 🔍 Looping Point Analysis: The Algorithmic Heart

The core of `Sonus Iteratus` is its intelligent looping algorithm.

* When you hit `l`, it meticulously analyzes the sample 🧐.
* It then presents a selection of potential looping points, highlighting the "best" candidate (trust the algorithm; it's designed to find the most seamless transitions 🧘).

### 5.3 ✂️ Subsample Selection: Fine-Grained Control

Now, you have choices:

* `q`: Return to the input pane (think again? 🤔).
* `p`: Preview each identified subsample (hear the possibilities 👂).
* ✅ Proceed with the algorithm's "best" loop, *or* select your own adventure!

### 5.4 ⏳ Output Duration: Tailoring Your Soundscape

How long do you want your sonic masterpiece to play? 🎶

* Enter the desired duration in seconds (it *must* be longer than your chosen subsample, duh 🙄).
* `q`: Go back, change your mind (it happens 🤷‍♀️).
* ✅ Finally, let the program loop the loop.

### 5.5 📤 Output Management: Your Sonic Command Center

The right pane is your output control center:

* `q`: Quit (peace out ✌️).
* `p`: Play your newly crafted looped audio (crank it up! 🔊).
* `Delete`: Remove the generated file (oops, wrong loop? 😬).
* `⬆️/⬇️ Scrolling`: Navigate the output (and input/log) panes with your keyboard (for when you're *really* prolific ✍️).

Output filenames are automatically generated, including the original sample name, the selected subsample info (if any), and the output duration (because organization is key 🔑).

---

## 6. 🎬 Demo: See Audionaut in Action

**Get a quick visual overview of how to use Audionaut:**

[![asciicast](https://asciinema.org/a/JJTpunHVlXK6X5bWUCvVSLpjA.svg)](https://asciinema.org/a/JJTpunHVlXK6X5bWUCvVSLpjA)

## 7. 🛠️ Installation: Get Started in Minutes

Clone the repo, create a virtual environment, and install the necessary requirements:

```bash
git clone [https://github.com/ndjuric/sonus_iteratus.git](https://github.com/ndjuric/sonus_iteratus.git) && cd sonus_iteratus
python -m venv src/.venv && source src/.venv/bin/activate
pip install -r requirements.txt
```

## 8. 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 9. 🙌 Contributing: Join the Noise!

**Contributions are welcome!** (It might not be the most useful piece of software out there, but hey, if someone has ideas, send a PR, fork it, have fun! 🙌)

>   Let's make some noise! 🔊
