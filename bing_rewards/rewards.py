# SPDX-FileCopyrightText: 2026 jack-mil
# SPDX-License-Identifier:: MIT

"""Fetch Microsoft Rewards points for each account via CDP.

Opens the account's Chrome profile, navigates to bing.com, and reads the
Rewards API endpoint from within the logged-in session.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from bing_rewards.app import resolve_browser_path
from bing_rewards.cdp_driver import CDPDriver

if TYPE_CHECKING:
    from bing_rewards import options as app_options


# Endpoint that the bing.com rewards dashboard itself uses (JSON, no auth headers
# needed beyond the session cookies of the logged-in profile).
REWARDS_API = 'https://www.bing.com/rewardsapp/getuserdata?checkBetaOffer=true&style=expiringrpm'
HTTP_OK = 200


def fetch_account_points(
    account: app_options.Account,
    config: app_options.Config,
) -> dict:
    """Return rewards points info for one account.

    Launches a short-lived headless browser on the account's profile and reads
    the rewards JSON from inside the logged-in session.

    Args:
        account: Account whose profile to inspect.
        config: Global config (for browser_path / agents).

    Returns:
        Dict with keys: name, available_points, lifetime_points, pc_search,
        mobile_search (progress dicts with current/count/complete).
    """

    driver = CDPDriver(
        exe=resolve_browser_path(config.browser_path),
        user_agent=config.desktop_agent,
        profile_dir=account.profile_dir,
        user_data_dir=account.user_data_dir or None,
        headless=True,
    )
    driver.start()
    try:
        driver.navigate('https://www.bing.com/?form=BRNMID')
        # Let the page settle so session cookies are attached to fetch().
        time.sleep(2)
        js = (
            'fetch(' + json.dumps(REWARDS_API) + ', {credentials: "include"})'
            '.then(r => r.text().then(t => JSON.stringify({status: r.status, body: t})))'
        )
        raw = driver.evaluate(js, await_promise=True)
        data = json.loads(raw)
        if data['status'] != HTTP_OK:
            raise RuntimeError(
                f'Rewards API returned HTTP {data["status"]} (profil belum login akun Microsoft?)'
            )
        body = json.loads(data['body'])
        return _parse_rewards_response(account.name, body)
    finally:
        driver.close()


def _parse_rewards_response(name: str, body: dict) -> dict:
    """Extract point balances and search progress from the rewards API JSON."""
    dashboard = body.get('dashboard', {})
    user = dashboard.get('userStatus', {})

    def search_progress(counter_set: dict) -> dict:
        return {
            'current': counter_set.get('pointProgress', 0) if counter_set else 0,
            'target': counter_set.get('pointProgressMax', 0) if counter_set else 0,
            'complete': bool(counter_set and counter_set.get('complete')),
        }

    pc = user.get('pcSearch', {})
    mobile = user.get('mobileSearch', {})
    return {
        'name': name,
        'available_points': user.get('availablePoints'),
        'lifetime_points': user.get('lifetimePoints'),
        'pc_search': search_progress(pc),
        'mobile_search': search_progress(mobile),
    }


def fetch_all_points(
    accounts: list[app_options.Account],
    config: app_options.Config,
    log=None,
) -> list[dict]:
    """Fetch points for every account; failures become error entries, never raise."""
    results = []
    for account in accounts:
        if log:
            log(f'Fetching points: {account.name}')
        results.append(_safe_fetch(account, config))
    return results


def _safe_fetch(account: app_options.Account, config: app_options.Config) -> dict:
    """Fetch one account; any failure (incl. SystemExit from CLI helpers) becomes an error entry."""
    try:
        return fetch_account_points(account, config)
    except SystemExit as e:
        return {'name': account.name, 'error': f'browser not found (exit {e.code})'}
    except Exception as e:  # noqa: BLE001 -- per-account boundary: one bad profile must not kill the rest
        return {'name': account.name, 'error': str(e)}
