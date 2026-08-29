# SPDX-FileCopyrightText: 2026 jack-mil
# SPDX-License-Identifier: MIT

"""Chrome DevTools Protocol driver: browser automation without keyboard hijacking."""

from __future__ import annotations

import contextlib
import json
import os
import random
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

import websocket

if TYPE_CHECKING:
    from collections.abc import Iterator

CDP_CONNECT_TIMEOUT = 30  # seconds to wait for the DevTools HTTP endpoint


class CDPDriver:
    """Chrome DevTools Protocol driver for headless/headed browser control."""

    def __init__(
        self,
        exe: str | Path,
        user_agent: str,
        profile_dir: str = '',
        user_data_dir: str | None = None,
        headless: bool = False,
    ):
        """Initialize CDP driver.

        Args:
            exe: Path to Chrome/Chromium executable.
            user_agent: User-agent string to spoof.
            profile_dir: Chrome profile directory name (e.g. 'Default', 'Profile 1').
            user_data_dir: User data directory path; if None, uses a temp dir.
            headless: Run in headless mode.
        """
        self.exe = Path(exe)
        self.user_agent = user_agent
        self.profile_dir = profile_dir
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.debug_port = self._find_free_port()
        self.process: subprocess.Popen | None = None
        self.ws: websocket.WebSocket | None = None
        self.msg_id = 0
        self.tab_id: str | None = None

    def _find_free_port(self) -> int:
        """Find an available port for remote debugging."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    def start(self):
        """Launch Chrome with remote debugging enabled and connect to its first tab."""
        cmd = [
            str(self.exe),
            f'--remote-debugging-port={self.debug_port}',
            f'--user-agent={self.user_agent}',
            '--no-first-run',
            '--no-default-browser-check',
        ]
        if self.user_data_dir:
            cmd.append(f'--user-data-dir={self.user_data_dir}')
        if self.profile_dir:
            cmd.append(f'--profile-directory={self.profile_dir}')
        if self.headless:
            cmd.extend(['--headless=new', '--disable-gpu'])

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=sys.platform != 'win32',
            )
        except FileNotFoundError:
            print(f'Browser executable not found: {self.exe}')
            sys.exit(1)

        print(f'Opening browser [{self.process.pid}] on debug port {self.debug_port}')
        self._connect(self._wait_for_endpoint())

    def _wait_for_endpoint(self) -> str:
        """Poll the DevTools HTTP endpoint until Chrome's debugger is ready."""
        deadline = time.time() + CDP_CONNECT_TIMEOUT
        last_error: OSError | ValueError | None = None
        while time.time() < deadline:
            try:
                response = urllib.request.urlopen(
                    f'http://127.0.0.1:{self.debug_port}/json/version', timeout=2
                )
                json.loads(response.read().decode())
                break
            except (OSError, ValueError) as e:
                last_error = e
            time.sleep(0.2)
        else:
            print(f'Chrome DevTools endpoint failed to start: {last_error}')
            self.close()
            sys.exit(1)

        # Grab the first page target's WebSocket (tab-level, not browser-level)
        tabs_response = urllib.request.urlopen(
            f'http://127.0.0.1:{self.debug_port}/json/list', timeout=5
        )
        tabs = json.loads(tabs_response.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        if not page_tabs:
            print(f'No page targets found: {tabs}')
            self.close()
            sys.exit(1)
        return page_tabs[0]['webSocketDebuggerUrl']

    def _connect(self, ws_url: str):
        """Connect to a page target's WebSocket."""
        try:
            self.ws = websocket.create_connection(
                ws_url, timeout=10, suppress_origin=True
            )
            self.tab_id = ws_url.rsplit('/', 1)[-1]
            print('CDP WebSocket connected')
        except (OSError, websocket.WebSocketException) as e:
            print(f'Failed to connect to CDP: {e}')
            self.close()
            sys.exit(1)

    def send_command(self, method: str, params: dict | None = None) -> dict:
        """Send a CDP command to the page target and return its result."""
        if not self.ws:
            raise RuntimeError('WebSocket not connected')

        self.msg_id += 1
        self.ws.send(json.dumps({'id': self.msg_id, 'method': method, 'params': params or {}}))

        # Skip events until the response with our id arrives
        while True:
            response = json.loads(self.ws.recv())
            if response.get('id') == self.msg_id:
                if 'error' in response:
                    raise RuntimeError(f'CDP error: {response["error"]}')
                return response.get('result', {})

    def navigate(self, url: str):
        """Navigate the page to a URL."""
        self.send_command('Page.navigate', {'url': url})

    def search(
        self,
        count: int,
        words_gen: Iterator[str],
        search_url: str,
        search_delay: float | list[float],
        load_delay: float,
    ):
        """Perform Bing searches via CDP.

        Args:
            count: Number of searches to perform.
            words_gen: Generator of search terms.
            search_url: Base Bing search URL.
            search_delay: Delay between searches (fixed value or [min, max]).
            load_delay: Initial page load delay.
        """
        self.send_command('Page.enable')
        time.sleep(load_delay)

        for i in range(count):
            query = next(words_gen)
            url = search_url + quote_plus(query)

            self.navigate(url)
            print(f'Search {i + 1}: {query}')

            match search_delay:
                case int(x) | float(x):
                    delay = x
                case (min_s, max_s):
                    delay = random.uniform(min_s, max_s)
                case _:
                    delay = 6.0

            time.sleep(delay)

    def close(self):
        """Close WebSocket and terminate the browser process."""
        if self.ws:
            with contextlib.suppress(OSError, websocket.WebSocketException):
                self.ws.close()
            self.ws = None

        if self.process:
            try:
                self._terminate_browser()
                self.process.wait(timeout=5)
                print(f'Closing browser [{self.process.pid}]')
            except (OSError, subprocess.SubprocessError):
                self.process.kill()
            self.process = None

    def _terminate_browser(self):
        """Terminate the browser process group cross-platform."""
        if sys.platform == 'win32':
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                capture_output=True,
                check=True,
                timeout=5,
            )
        else:
            os.killpg(self.process.pid, signal.SIGTERM)
