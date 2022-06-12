from time import time

import tornado.gen
import tornado.web

import orjson
from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = 'osu_session'
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-session.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self) -> None:

        if not requestsManager.checkArguments(self.request.arguments, ['u', 'h', 'action']):
            raise exceptions.invalidArgumentsException(MODULE_NAME)

        if self.get_argument('action') != 'submit':
            self.write('Not yet')
            return

        content = orjson.loads(self.get_argument("content")) # TODO: type hint hell

        try:
            glob.db.execute('INSERT INTO osu_session (id, user, ip, operating_system, fullscreen, framesync, compatability_mode, spike_frame_count, aim_framerate, completion, start_time, end_time, time) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);', [
                userUtils.getID(self.get_argument('u')),
                self.getRequestIP(),
                content['Tags']['OS'],
                bool(content['Tags']['Fullscreen']),
                content['Tags']['FrameSync'],
                bool(content['Tags']['Compatibility']),
                content['SpikeFrameCount'],
                content['AimFrameRate'],
                content['Completion'],
                content['StartTime'],
                content['EndTime'],
                time()
            ])
        except: log.error(f'osu session failed to save!\n\n**Content**\n{content}', discord='ac_confidential')

        self.write("Not yet")
        return
