import tornado.gen
import tornado.web

from common.web import requestsManager


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        self.write("Hey! You're connected to Akatsuki, although the login servers are currently down. (Score server is up).")

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self) -> None:
        self.write("Hey! You're connected to Akatsuki, although the login servers are currently down. (Score server is up).")
