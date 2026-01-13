import random
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class AccountManager:
    """
    Manages a pool of accounts for stealth trading.
    Allows rotating through different pairs of accounts to disguise activity.
    """
    def __init__(self, account_configs: List[Dict]):
        self.accounts = account_configs
        self._validate_accounts()

    def _validate_accounts(self):
        if len(self.accounts) < 2:
            raise ValueError("AccountManager requires at least 2 accounts.")
        logger.info(f"AccountManager initialized with {len(self.accounts)} accounts.")

    def get_random_pair(self) -> Tuple[Dict, Dict]:
        """
        Selects two distinct accounts from the pool randomly.
        Returns (account_long, account_short).
        """
        if len(self.accounts) == 2:
            # If only 2 accounts, just shuffle them or return fixed?
            # User wants stealth, so swapping who is Long and who is Short is also good.
            pair = list(self.accounts)
            random.shuffle(pair)
            return pair[0], pair[1]

        # Pick 2 distinct indices
        selected = random.sample(self.accounts, 2)
        return selected[0], selected[1]

    def get_all_accounts(self) -> List[Dict]:
        return self.accounts
