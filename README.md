# Bing-Rewards

<div align="center">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/bing-rewards?style=flat-square&label=Python&logo=python&logoColor=yellow">
<a href="https://pypi.org/p/bing-rewards/"> <img alt="PyPi" src="https://img.shields.io/pypi/v/bing-rewards?label=PyPI&style=flat-square&logo=pypi&logoColor=yellow"></a>
<a href="https://pypi.org/p/bing-rewards/"> <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/bing-rewards?style=flat-square&label=Downloads&color=orange"></a>
<br>
<img alt="PyPI - License" src="https://img.shields.io/pypi/l/bing-rewards?style=flat-square&label=License&color=blueviolet">
</div>

### A CLI app and web UI to perform Bing searches
Please submit an issue or pull-request if you have an idea for a feature

- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Options](#options)
- [Config](#config)
- [Development](#development)


## Features

* Automated Bing searches via Chrome DevTools Protocol (CDP) — no keyboard hijacking
* **Web UI** for easy configuration and monitoring (`uvicorn bing_rewards.webapp:app`)
* **Multi-account support** — run searches across multiple Microsoft accounts sequentially
* **Headless mode** — run without visible browser windows (`--headless`)
* **Cross-platform** — works on Windows, Linux (including Wayland), and macOS
* Mobile and desktop search modes with configurable counts
* Fine-tune delays and browser path via [config file](#config)
* Not intended as a fully automated service — assists with manual tasks


> [!Important]
> This was originally created in a different age, when Bing & MS was much simpler and less bloated with AI ~~slop~~ tools. Users have reported a wide variety of success on whether this method works at all with the new systems. See some of the pinned or closed issues for reports from others that may improve success. I maintain the *code* in a working state as an excersie in Python packaging, but do *not* personally use the utility, and **cannot guarantee this method will even generate points anymore**!

## Installation
Bing-rewards is a CLI application distributed on PyPI. You can install it however you prefer to manage Python applications on your system. I recommend `pipx` or `uv`.

### With [`pipx`](https://pipx.pypa.io/stable/) or `pip`
```bash
pipx install bing-rewards
```

### With [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
```sh
uv tool install bing-rewards
```

These commands will make the executable `bing-rewards` available on your PATH.
Look below or try the `--help` flag to see detailed usage.

> [!Tip]
> Use a virtual environment or [`pipx`](https://pypa.github.io/pipx/) to avoid polluting your global package space with executable apps. See: [pipx](https://pypa.github.io/pipx/)

### Locally
Clone the repo and install locally. See: [Developing](#development--contribution)

## Dependencies

- Python 3.10 or newer

- A Chromium-based browser (`chrome`, `chromium`, `brave`, etc.) discoverable on PATH, or specify with `--exe`
  - [Download Google Chrome](https://www.google.com/intl/en/chrome/)
  - See `"browser_path"` in [config](#config) for persistent override

- **FastAPI** and **uvicorn** (installed with package) for the optional web UI

- **websocket-client** (installed with package) for CDP communication

- You must log into [bing.com](https://www.bing.com) with your Microsoft account at least once in each browser profile to save cookies
## Usage

### CLI

Complete mobile and desktop daily points (default: 33 desktop + 23 mobile):

```bash
bing-rewards
```

Run 10 mobile searches only:

```bash
bing-rewards -m -c10
```

Headless mode (no visible window):

```bash
bing-rewards --headless
```

Dry run (verify config without launching browser):

```bash
bing-rewards --dryrun
```

### Web UI

Launch the web interface:

```bash
uvicorn bing_rewards.webapp:app --port 8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

The UI allows you to:
- Configure multi-account runs with separate Chrome profiles
- Toggle desktop/mobile/headless/dryrun modes
- Adjust search counts per run
- Monitor live logs and run status
- Start/stop runs without touching the CLI

### Multi-Account Setup

Edit `config.json` (`~/.config/bing-rewards/config.json` on Linux, `%APPDATA%\bing-rewards\config.json` on Windows):

```json
{
  "accounts": [
    {
      "name": "Account1",
      "user_data_dir": "/path/to/chrome-profile-1",
      "profile_dir": "Default"
    },
    {
      "name": "Account2",
      "user_data_dir": "/path/to/chrome-profile-2",
      "profile_dir": "Default"
    }
  ],
  "desktop_count": 33,
  "mobile_count": 23,
  "headless": false
}
```

Each account runs in its own isolated Chrome `user-data-dir`. Log into each profile's Bing once manually, then automated runs will reuse those sessions.

## Options

Running with no options will complete mobile and desktop daily search quota.
The following options are available to change the default behavior.
Options supplied at execution time override any config.
| Flag                       | Option                                                                                          |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| `-h`, `--help`             | Display help and exit                                                                           |
| `-c`, `--count=N`          | Override the number of searches to complete                                                     |
| `-b`, `--bing`             | Use this flag if Bing is already your default search engine                                     |
| `-d`, `--desktop`          | Only perform desktop searches                                                                   |
| `-m`, `--mobile`           | Only perform mobile searches                                                                    |
| `-n`, `--dryrun`           | Validate configuration without launching browser                                                |
| `--exe PATH`               | Full path to Chrome-compatible browser (Brave, Chromium, Chrome tested)                         |
| `--load-delay SEC`         | Time given to Chrome to load (seconds)                                                          |
| `--search-delay MIN[,MAX]` | Time between searches (seconds); single value or range for random delays                        |
| `--open-rewards`           | Open the Microsoft Rewards dashboard after completing searches                                  |
| `--headless`               | Run browser in headless mode (no visible window)                                                |
| `--ime`                    | (Windows) Press Shift to switch IME to English input before typing                              |
## Config

A config file is generated in `$XDG_CONFIG_HOME/bing-rewards/` (Linux/macOS) or `%APPDATA%\bing-rewards\` (Windows) on first run.

Example `~/.config/bing-rewards/config.json`:

```json
{
  "desktop_count": 33,
  "mobile_count": 23,
  "load_delay": 1.5,
  "search_delay": 6.0,
  "search_url": "https://www.bing.com/search?form=QBRE&q=",
  "desktop_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edge/126.0.0.0",
  "mobile_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 6 Build/AP2A.240605.024) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36 Edge/121.0.2277.138",
  "browser_path": "chrome",
  "bing": false,
  "open_rewards": false,
  "headless": false,
  "ime": false,
  "accounts": [],
  "profile": ["Default"]
}
```

**New in this fork:**
- `headless`: Run browsers without visible windows
- `accounts`: Array of account configs for multi-account runs (see [Multi-Account Setup](#multi-account-setup))
- Removed `window` and `exit` options (CDP always manages browser lifecycle cleanly)

### User agents

The default user agents that are passed to the Chrome process are below.
You may want to experiment with different user agents, or update versions accordingly.
Alternate user agents can be set in the config file.

Edge Browser on Windows 10 desktop:
> Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edge/126.0.0.0

Mobile Edge Browser on Pixel 6 phone:
>  Mozilla/5.0 (Linux; Android 14; Pixel 6 Build/AP2A.240605.024) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36 Edge/121.0.2277.138


## Words
The [keywords](https://web.archive.org/web/20220523083250/https://www.myhelpfulguides.com/keywords.txt) included in this repo where taken from this site
[https://www.myhelpfulguides.com/2018/07/19/bing-rewards-auto-searcher-with-python-3/](https://web.archive.org/web/20220331033847/https://www.myhelpfulguides.com/2018/07/19/bing-rewards-auto-searcher-with-python-3/).

Their script provided the original inspiration but has since been completely rewritten and expanded.
The original author was contacted for the source of keywords, but declined to respond

## Development

This project is managed by the [`uv`](https://docs.astral.sh/uv) toolchain.
Ensure you have `uv` installed on your system. This is probably available in your package manager,
or can be installed with `pip` or `pipx`

Then, fork the repository on Github and clone to your machine. The first invocation of any `uv` command will install the `bing-rewards` package in editable mode, with the dev dependencies (`ruff` and `pre-commit`) automatically.

Install the defined pre-commit hooks: `uv run pre-commit install --install-hooks`

Launch bing-rewards in the editable dev environment: `uv run bing-rewards --help`

Feel free to open a PR against the `master` branch with additional features or fixes!
