# SPDX-FileCopyrightText: 2026 jack-mil
# SPDX-License-Identifier: MIT

"""Core search logic using CDP driver for multi-account, headless, and Linux support."""

from __future__ import annotations

import io
import random
import shutil
import sys
import webbrowser
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from bing_rewards import options as app_options
from bing_rewards.cdp_driver import CDPDriver


def word_generator() -> Iterator[str]:
    """Infinitely generate terms from the word file.

    Starts reading from a random position in the file.
    If end of file is reached, close and restart.
    Handles file operations safely and ensures uniform random distribution.

    Yields:
        str: A random keyword from the file, stripped of whitespace.

    Raises:
        OSError: If there are issues accessing or reading the file.
    """
    word_data = resources.files('bing_rewards').joinpath('data', 'keywords.txt')

    try:
        while True:
            with (
                resources.as_file(word_data) as p,
                p.open(mode='r', encoding='utf-8') as fh,
            ):
                # Get the file size of the Keywords file
                fh.seek(0, io.SEEK_END)
                size = fh.tell()

                if size == 0:
                    raise ValueError('Keywords file is empty')

                # Start at a random position in the stream
                fh.seek(random.randint(0, size - 1), io.SEEK_SET)

                # Read and discard partial line to ensure we start at a clean line boundary
                fh.readline()

                # Read lines until EOF
                for raw_line in fh:
                    stripped_line = raw_line.strip()
                    if stripped_line:  # Skip empty lines
                        yield stripped_line

                # If we hit EOF, seek back to start and continue
                fh.seek(0)
                for raw_line in fh:
                    stripped_line = raw_line.strip()
                    if stripped_line:
                        yield stripped_line
    except OSError as e:
        print(f'Error accessing keywords file: {e}')
        raise
    except Exception as e:
        print(f'Unexpected error in word generation: {e}')
        raise


def resolve_browser_path(exe_arg: str | Path) -> Path:
    """Resolve browser executable path; exit if not found."""
    exe = Path(exe_arg)
    if exe.is_file() and exe.exists():
        return exe.resolve()
    if pth := shutil.which(str(exe)):
        return Path(pth)
    print(
        f'Command "{exe}" could not be found.\n'
        'Make sure it is available on PATH, '
        'or use the --exe flag to give an absolute path.'
    )
    sys.exit(1)


def run_account_searches(
    account: app_options.Account,
    config: app_options.Config,
    modes: tuple[bool, bool],
    words_gen: Iterator[str],
    dryrun: bool,
):
    """Run searches for a single account using CDP driver.

    Args:
        account: Account configuration.
        config: Global config.
        modes: (desktop, mobile) booleans for which search modes to run.
        words_gen: Word generator.
        dryrun: If True, skip actual browser launch.
    """
    desktop, mobile = modes
    exe = None if dryrun else resolve_browser_path(config.browser_path)

    desktop_count = account.desktop_count or config.desktop_count
    mobile_count = account.mobile_count or config.mobile_count

    if desktop:
        print(f'[{account.name}] Doing {desktop_count} desktop searches')
        if not dryrun:
            driver = CDPDriver(
                exe=exe,
                user_agent=config.desktop_agent,
                profile_dir=account.profile_dir,
                user_data_dir=account.user_data_dir or None,
                headless=config.headless,
            )
            try:
                driver.start()
                driver.search(
                    count=desktop_count,
                    words_gen=words_gen,
                    search_url=config.search_url,
                    search_delay=config.search_delay,
                    load_delay=config.load_delay,
                )
            finally:
                driver.close()
        print(f'[{account.name}] Desktop searches complete!\n')

    if mobile:
        print(f'[{account.name}] Doing {mobile_count} mobile searches')
        if not dryrun:
            driver = CDPDriver(
                exe=exe,
                user_agent=config.mobile_agent,
                profile_dir=account.profile_dir,
                user_data_dir=account.user_data_dir or None,
                headless=config.headless,
            )
            try:
                driver.start()
                driver.search(
                    count=mobile_count,
                    words_gen=words_gen,
                    search_url=config.search_url,
                    search_delay=config.search_delay,
                    load_delay=config.load_delay,
                )
            finally:
                driver.close()
        print(f'[{account.name}] Mobile searches complete!\n')


def main():
    """Program entrypoint with CDP-based multi-account support."""
    options = app_options.get_options()
    words_gen = word_generator()

    # Determine which modes to run
    desktop = options.desktop or (not options.mobile and not options.desktop)
    mobile = options.mobile or (not options.mobile and not options.desktop)

    # Get accounts from config (multi-account or legacy profile)
    config_obj = app_options.Config(
        desktop_count=options.desktop_count,
        mobile_count=options.mobile_count,
        load_delay=options.load_delay,
        search_delay=options.search_delay,
        search_url=options.search_url,
        desktop_agent=options.desktop_agent,
        mobile_agent=options.mobile_agent,
        browser_path=options.browser_path,
        bing=options.bing,
        open_rewards=options.open_rewards,
        headless=getattr(options, 'headless', False),
        ime=options.ime,
        accounts=getattr(options, 'accounts', []),
        profile=options.profile,
    )

    accounts = config_obj.get_accounts()

    print(f'Running searches for {len(accounts)} account(s)')

    for account in accounts:
        run_account_searches(
            account=account,
            config=config_obj,
            modes=(desktop, mobile),
            words_gen=words_gen,
            dryrun=options.dryrun,
        )

    # Open rewards dashboard
    if options.open_rewards and not options.dryrun:
        webbrowser.open_new('https://account.microsoft.com/rewards')


if __name__ == '__main__':
    main()
