from typing import Optional

import tornado.gen
import tornado.web

from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/lastfm.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        if not requestsManager.checkArguments(self.request.arguments, ('us', 'ha', 'b')):
            self.write('Not yet')
            return

        username: Optional[str] = self.get_argument("us", None)
        userID: int = userUtils.getID(username)

        if not userUtils.checkLogin(userID, self.get_argument("ha", None), self.getRequestIP()):
            self.write("Not yet")
            return

        # Get beatmap_id™ argument
        b = self.get_argument("b", None)

        if (
            b.startswith('a') and
            not userUtils.checkDelayBan(userID) and
            not userUtils.isRestricted(userID)
        ):
            flags = int(b[1:]) if b[1:].isdigit() else None
            if not flags or flags == 4: # 4 = extra threads running (can be other things)
                return

            readable: list[str] = []
            if flags & 1 << 0: readable.append("[1] osu! run with -ld")
            if flags & 1 << 1: readable.append("[2] osu! has a console open")
            if flags & 1 << 2: readable.append("[4] osu! has extra threads running")
            if flags & 1 << 3: readable.append("[8] osu! is hqosu! (check #1)")
            if flags & 1 << 4: readable.append("[16] osu! is hqosu! (check #2)")
            if flags & 1 << 5: readable.append("[32] osu! has special launch settings in registry")
            if flags & 1 << 6: readable.append("[64] AQN is loaded (check #1)")
            if flags & 1 << 7: readable.append("[128] AQN is loaded (check #2)")
            if flags & 1 << 8: readable.append("[256] notify_1 was run while out of the editor (AQN sound on program open)")

            # Enqueue the users restriction.
            if flags not in {32, 36}:
                userUtils.setDelayBan(userID, True)

            # Send our webhook to Discord.
            log.warning('\n\n'.join([
                f'[{username}](https://akatsuki.pw/u/{userID}) sent flags **{b}**',
                '**Breakdown**\n' + '\n'.join(readable),
                f'**[IP Matches](https://old.akatsuki.pw/index.php?p=136&uid={userID})**'
            ]), discord='ac_confidential')

        self.write("Not yet")
