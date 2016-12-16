# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from pyload.plugin.internal.multihoster import MultiHoster

from pyload.common.json_layer import json_loads
from pyload.network.requestfactory import get_url


class PremiumizeMe(MultiHoster):
    __name__ = "PremiumizeMe"
    __version__ = "0.12"
    __type__ = "hook"
    __description__ = """Premiumize.me hook plugin"""

    __config__ = [("activated", "bool", "Activated", False),
                  ("hosterListMode", "all;listed;unlisted", "Use for hosters (if supported):", "all"),
                  ("hosterList", "str", "Hoster list (comma separated)", ""),
                  ("unloadFailing", "bool", "Revert to stanard download if download fails", False),
                  ("interval", "int", "Reload interval in hours (0 to disable)", 24)]

    __author_name__ = "Florian Franzen"
    __author_mail__ = "FlorianFranzen@gmail.com"

    def get_hoster(self):
        # If no accounts are available there will be no hosters available
        if not self.account or not self.account.can_use():
            return []

        # Get account data
        (user, data) = self.account.select_account()

        # Get supported hosters list from premiumize.me using the
        # json API v1 (see https://secure.premiumize.me/?show=api)
        answer = get_url("https://api.premiumize.me/pm-api/v1.php?method=hosterlist&params[login]=%s&params[pass]=%s" % (
                        user, data['password']))
        data = json_loads(answer)

        # If account is not valid thera are no hosters available
        if data['status'] != 200:
            return []

        # Extract hosters from json file
        return data['result']['hosterlist']

    def core_ready(self):
        # Get account plugin and check if there is a valid account available
        self.account = self.pyload.accountmanager.get_account_plugin("PremiumizeMe")
        if not self.account.can_use():
            self.account = None
            self.log_error(_("Please add a valid premiumize.me account first and restart pyLoad."))
            return

        # Run the overwriten core ready which actually enables the multihoster hook
        return MultiHoster.coreReady(self)
