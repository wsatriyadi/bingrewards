# SPDX-FileCopyrightText: 2026 jack-mil
# SPDX-License-Identifier: MIT

"""Web UI server for bing-rewards: config management, multi-account, and run control."""

from __future__ import annotations

import dataclasses
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from bing_rewards import app as app_cdp
from bing_rewards import options as app_options


class State:
    """Shared mutable run state for the web UI."""

    def __init__(self):
        self.status: str = 'idle'  # idle | running | stopping | error
        self.accounts_run: list[str] = []
        self.log_lines: list[str] = []
        self.run_thread: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.started_at: float | None = None

    LOG_MAX_LINES = 500

    def log(self, msg: str):
        self.log_lines.append(msg)
        if len(self.log_lines) > self.LOG_MAX_LINES:
            del self.log_lines[: len(self.log_lines) - self.LOG_MAX_LINES]

    def reset(self):
        self.status = 'running'
        self.accounts_run = []
        self.log_lines = []
        self.stop_flag.clear()
        self.started_at = time.time()


STATE = State()

app = FastAPI(title='bing-rewards web UI')

# ---------- static frontend ----------
STATIC_DIR = Path(__file__).parent / 'webui'
INDEX = STATIC_DIR / 'index.html'


@app.get('/api/config')
def get_config():
    """Return the current merged config (defaults + file) as JSON."""
    cfg = app_options.read_config()
    return dataclasses.asdict(cfg)


@app.get('/api/status')
def get_status():
    """Return current run state."""
    return {
        'status': STATE.status,
        'accounts_run': STATE.accounts_run,
        'log_tail': STATE.log_lines[-20:],
        'log_len': len(STATE.log_lines),
        'started_at': STATE.started_at,
    }

@app.get('/api/log')
def get_log(offset: int = 0):
    """Return log lines from `offset`; returns full lines with cursor."""
    lines = STATE.log_lines
    return {
        'lines': lines[offset:],
        'cursor': len(lines),
    }


class RunRequest(BaseModel):
    """POST /api/run request body."""
    desktop: bool = True
    mobile: bool = True
    dryrun: bool = False
    headless: bool = False
    desktop_count: int | None = None
    mobile_count: int | None = None
    accounts: list[dict] | None = None


@app.post('/api/run')
def start_run(req: RunRequest):
    """Start a run in a background thread."""
    if STATE.status == 'running':
        raise HTTPException(400, 'A run is already in progress')
    STATE.reset()
    STATE.status = 'running'
    STATE.started_at = time.time()

    def run():
        try:
            words_gen = app_cdp.word_generator()
            config = app_options.read_config()
            if req.accounts is not None:
                config.accounts = req.accounts
            if req.headless:
                config.headless = True
            if req.desktop_count is not None:
                config.desktop_count = req.desktop_count
            if req.mobile_count is not None:
                config.mobile_count = req.mobile_count
            accounts = config.get_accounts()
            STATE.accounts_run = [a.name for a in accounts]
            STATE.log(
                f'Run started: {len(accounts)} account(s), '
                f'desktop={req.desktop}, mobile={req.mobile}, dryrun={req.dryrun}'
            )
            for account in accounts:
                if STATE.stop_flag.is_set():
                    STATE.log(f'Stop requested, skipping {account.name}')
                    break
                STATE.log(f'Running account: {account.name}')
                app_cdp.run_account_searches(
                    account=account,
                    config=config,
                    modes=(req.desktop, req.mobile),
                    words_gen=words_gen,
                    dryrun=req.dryrun,
                )
                STATE.log(f'Account {account.name} complete')
            STATE.status = 'idle'
            STATE.log('Run complete')
        except Exception as e:
            STATE.status = 'error'
            STATE.log(f'Error: {e}')

    STATE.run_thread = threading.Thread(target=run, daemon=True)
    STATE.run_thread.start()
    return {'ok': True}


@app.post('/api/stop')
def stop_run():
    """Request the current run to stop after the current account completes."""
    if STATE.status != 'running':
        raise HTTPException(400, f'No run in progress (status: {STATE.status})')
    STATE.stop_flag.set()
    STATE.log('Stop requested; finishing current account then halting.')
    return {'ok': True}


@app.get('/')
def index():
    return FileResponse(INDEX)
