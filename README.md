# 🎵 Loopify 🔄

[![Stars](https://img.shields.io/github/stars/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/stargazers)
[![Forks](https://img.shields.io/github/forks/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/network)
[![Issues](https://img.shields.io/github/issues/ndjuric/sonus_iteratus?style=flat-square&logo=github)](https://github.com/ndjuric/sonus_iteratus/issues)
[![License](https://img.shields.io/github/license/ndjuric/sonus_iteratus?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.6%2B-blue?style=flat-square&logo=python)](https://www.python.org)

 A simple way to find seamless audio subsamples inside your already short audio samples and generate perfect hour-long loops! 🚀

**Give it a ⭐️ if you like it!**

## 🎬 Table of Contents
- [Background](#background)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## 🚀 Introduction

This is a command-line tool with a terminal user interface designed for the meticulous and highly customizable looping of subsamples of short audio samples. I know.

This tool provides a straightforward, terminal-based UI for:

* 📂 Selecting `.wav` audio samples that have been copied to data/sound/input/ folder
* 🎯 Detecting optimal, seamless looping points
* 🔄 Looping those samples... *ad nauseam* (I jest, of course not, it loops those samples for a user-specified duration, of course 😉), and saving the output to data/sound/output

## 🤔 Why, Though?

Frud, a friend, initiated a chat one night, while en route to _redacted_ and asked me if I could: "Clean up and repeat this noisy recording of... some kind of emergency siren 🚨 ... for 10 hours"

So, unhindered by my... *ahem*... evolving mastery of audio tools 🤷‍♂️, led to creation of this... audio tool.

## 🎧 wat
While the origins of this tool might be niche and might forever be shrouded in mystery, it aims to be a valuable tool for anyone needing to seamlessly loop that loop. I'm actually putting this on my github. That's right. There are also plans on making that ncurses code look better and even be more readable.

## ✨ Functionality

I think this tool offers a clean, terminal user interface (TUI) structured for efficiency:

* **📂 Input Pane (Left):** Displays all `.wav` audio files residing in the `data/sound/input/` directory.
* **📭 Output Pane (Right):** Shows the generated looped audio files, saved to the `data/sound/output/` directory.
* **📜 Log Pane (Bottom):** Provides helpful logs, feedback, and status updates.
* **💡 Legend:** A context-aware guide to keybindings and actions, dynamically updating to ease your looping journey.

## ⚙️ Workflow

TUI guides you through a clear, iterative looping process:

### 1. 📥 Input Selection

In the left pane, wield these commands:

* `q`:  Quit the tool (once you've finished your symphony 🤘).
* `p`:  Preview the selected audio sample (give it a listen 👂).
* `l`:  Unleash the looping algorithm! (the magic happens here ✨).

### 2. 🔍 Looping Point Analysis

The interesting part for me was figuring out 'seamless' subsamples.

* When you hit `l`, it analyzes the sample 🧐.
* It then presents a selection of potential looping points, highlighting the "best" candidate (trust the algorithm, depending on the input it actually does detect the most seamless transitions 🧘).

### 3. ✂️ Subsample Selection

Now, you have choices:

* `q`:  Return to the input pane (think again? 🤔).
* `p`:  Preview each identified subsample (hear the possibilities 👂).
* ✅ Proceed with the algorithm's "best" loop, *or* select your own adventure!

### 4. ⏳ Output Duration

How long do you want your sonic masterpiece to play? 🎶

* Enter the desired duration in seconds (it *must* be longer than your chosen subsample, duh 🙄).
* `q`:  Go back, change your mind (it happens 🤷‍♀️).
* ✅ Finally, be done with it and let the program loop the loop.

### 5. 📤 Output Management

The right pane is your output control center:

* `q`:  Quit (peace out ✌️).
* `p`:  Play your newly crafted looped audio (crank it up! 🔊).
* `Delete`: Remove the generated file (oops, wrong loop? 😬).
* `⬆️/⬇️ Scrolling`: Navigate the output (and input/log) panes with your keyboard (for when you're *really* prolific ✍️).

Output filenames are automatically generated, including the original sample name, the selected subsample info (if any), and the output duration (because organization is key 🔑).

---

Clone the repo, create a virtual environment and inside it install neccessary requirements

```bash
~ git clone https://github.com/ndjuric/sonus_iteratus.git && cd sonus_iteratus
sonus_iteratus/ ~ python -m venv src/.venv && source src/.venv/bin/activate
sonus_iteratus/ ~ pip install -r requirements.txt
```

## 📜 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

**Contributions are welcome!** (It might not be the most useful piece of software out there but hey, if someone has ideas, send a PR, fork it, have fun! 🙌)

> Let's make some noise! 🔊
