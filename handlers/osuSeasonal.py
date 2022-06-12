import tornado.gen
import tornado.web

from common.web import requestsManager


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        backgrounds = [
            f'https://akatsuki.pw/static/seasonal/{id}.jpg'
            for id in ('dopamine', 'hype', 'dropzline')
        ]

        self.write(str(backgrounds).replace('/', '\/'))
