#!/usr/bin/env python3.8

import ftplib
# General imports
import os
from multiprocessing.pool import ThreadPool
from os import chdir, makedirs, path

import redis
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web
from raven.contrib.tornado import AsyncSentryClient

from common import agpl, generalUtils
from common.constants import bcolors
from common.db import dbConnector
from common.ddog import datadogClient
from common.redis import pubSub
from common.web import schiavo
#from handlers import osuSessionHandler
from handlers import (apiCacheBeatmapHandler, apiPPHandler, apiStatusHandler,
                      banchoConnectHandler, beatmapSubmitGetIdHandler,
                      beatmapSubmitUploadHandler, changelogHandler,
                      commentHandler, defaultHandler, downloadMapHandler,
                      emptyHandler, getFullReplayHandler, getReplayHandler,
                      getScoresHandler, getScreenshotHandler, lastfmHandler,
                      osuMapsHandler, osuSearchHandler, osuSearchSetHandler,
                      osuSeasonal, rateHandler, redirectHandler,
                      submitModularHandler, uploadScreenshotHandler)
from helpers import config, consoleHelper
from objects import glob
from pubSubHandlers import beatmapUpdateHandler


def make_app():
    return tornado.web.Application([
        (r'/web/bancho_connect.php', banchoConnectHandler.handler),
        (r'/web/osu-osz2-getscores.php', getScoresHandler.handler),
        (r'/web/osu-submit-modular(-selector)?.php', submitModularHandler.handler),
        (r'/web/osu-osz2-bmsubmit-getid.php', beatmapSubmitGetIdHandler.handler),
        (r'/web/osu-osz2-bmsubmit-upload.php', beatmapSubmitUploadHandler.handler),
        (r'/web/osu-getreplay.php', getReplayHandler.handler),
        (r'/web/osu-rate.php', rateHandler.handler),
        (r'/web/osu-screenshot.php', uploadScreenshotHandler.handler),
        (r'/web/osu-search.php', osuSearchHandler.handler),
        (r'/web/osu-search-set.php', osuSearchSetHandler.handler),
        (r'/web/osu-comment.php', commentHandler.handler),
        (r'/web/osu-getseasonal.php', osuSeasonal.handler),
        (r'/ss/([A-Z\d]{8}\.png)', getScreenshotHandler.handler),
        (r'/web/maps/(.+)', osuMapsHandler.handler),
        (r'/(?:s|d)/(\d{1,10})', downloadMapHandler.handler),
        (r'/web/replays/(\d{1,10})', getFullReplayHandler.handler),
        (r'/p/changelog', changelogHandler.handler),

        (r'/web/check-updates.php', redirectHandler.handler, {'destination': 'https://osu.ppy.sh/web/check-updates.php'}),
        (r'/p/verify', redirectHandler.handler, {'destination': 'https://akatsuki.pw/index.php?p=2'}),
        (r'/u/(\d{1,10})', redirectHandler.handler, {'destination': 'https://akatsuki.pw/u/{0}'}),

        (r'/(?:lets)?api/v1/status', apiStatusHandler.handler),
        (r'/(?:lets)?api/v1/pp', apiPPHandler.handler),
        (r'/(?:lets)?api/v1/cacheBeatmap', apiCacheBeatmapHandler.handler),

        (r'/web/lastfm.php', lastfmHandler.handler),

        #(r'/web/osu-session.php', osuSessionHandler.handler),

        # Not done yet
        (r'/web/osu-(?:session|addfavourite|checktweets|markasread|'
         r'get-beatmap-topic|getbeatmapinfo|getfriends|error).php', emptyHandler.handler)

    ], default_handler_class=defaultHandler.handler)


def main() -> int:
    try:
        agpl.check_license('ripple', 'LETS')
    except agpl.LicenseError as e:
        print(str(e))
        return 1

    try:
        consoleHelper.printServerStartHeader(True)
        chdir(path.dirname(path.realpath(__file__)))

        # Read config
        consoleHelper.printNoNl('> Reading config file...')
        glob.conf = config.config('config.ini')

        if glob.conf.default:
            # We have generated a default config.ini, quit server
            consoleHelper.printWarning()
            consoleHelper.printColored('[!] config.ini not found. A default one has been generated.', bcolors.YELLOW)
            consoleHelper.printColored('[!] Please edit your config.ini and run the server again.', bcolors.YELLOW)
            return 1

        # If we haven't generated a default config.ini, check if it's valid
        if not glob.conf.checkConfig():
            consoleHelper.printError()
            consoleHelper.printColored('[!] Invalid config.ini. Please configure it properly', bcolors.RED)
            consoleHelper.printColored('[!] Delete your config.ini to generate a default one', bcolors.RED)
            return 1
        else:
            consoleHelper.printDone()

        # Create data/oppai maps folder if needed
        consoleHelper.printNoNl('> Checking folders...')

        osu_path = os.path.join(glob.BEATMAPS_PATH, 'osu')
        osz_path = os.path.join(glob.BEATMAPS_PATH, 'osz')

        for i in (
            '.data',
            '.data/replays',
            '.data/screenshots',
            '.data/oppai',
            '.data/catch_the_pp',
            '.data/beatmaps',
            glob.BEATMAPS_PATH,
            osu_path,
            osz_path
        ):
            if not path.exists(i):
                makedirs(i, 0o770)
        consoleHelper.printDone()

        # Connect to db
        try:
            consoleHelper.printNoNl('> Connecting to MySQL database...')
            glob.db = dbConnector.db(
                glob.conf.config['db']['host'],
                glob.conf.config['db']['username'],
                glob.conf.config['db']['password'],
                glob.conf.config['db']['database'],
                int(glob.conf.config['db']['workers'])
            )
            consoleHelper.printNoNl(" ")
            consoleHelper.printDone()
        except:
            # Exception while connecting to db
            consoleHelper.printError()
            consoleHelper.printColored('[!] Error while connecting to database. Please check your config.ini and run the server again', bcolors.RED)
            raise

        if generalUtils.stringToBool(glob.conf.config['ftp']['enable']):
            # Connect to ftp
            try:
                consoleHelper.printNoNl('> Connecting to backup (ftp) server...')

                glob.ftp = ftplib.FTP(
                    host = glob.conf.config['ftp']['host'],
                    user = glob.conf.config['ftp']['username'],
                    passwd = glob.conf.config['ftp']['password']
                )
                consoleHelper.printNoNl(' ')
                consoleHelper.printDone()
            except:
                consoleHelper.printError()
                consoleHelper.printColored('[!] Error while connecting to FTP. Please check your config.ini and run the server again', bcolors.RED)
                raise

        # Connect to redis
        try:
            consoleHelper.printNoNl('> Connecting to redis...')
            glob.redis = redis.Redis(
                glob.conf.config['redis']['host'],
                glob.conf.config['redis']['port'],
                glob.conf.config['redis']['database'],
                glob.conf.config['redis']['password']
            )
            glob.redis.ping()
            consoleHelper.printNoNl(' ')
            consoleHelper.printDone()
        except:
            # Exception while connecting to db
            consoleHelper.printError()
            consoleHelper.printColored('[!] Error while connecting to redis. Please check your config.ini and run the server again', bcolors.RED)
            raise

        # Empty redis cache
        try:
            glob.redis.eval("return redis.call('del', unpack(redis.call('keys', ARGV[1])))", 0, 'lets:*')
        except redis.exceptions.ResponseError:
            # Script returns error if there are no keys starting with peppy:*
            pass

        # Save lets version in redis
        glob.redis.set('lets:version', glob.VERSION)

        # Create threads pool
        try:
            consoleHelper.printNoNl('> Creating threads pool...')
            glob.pool = ThreadPool(int(glob.conf.config['server']['threads']))
            consoleHelper.printDone()
        except:
            consoleHelper.printError()
            consoleHelper.printColored('[!] Error while creating threads pool. Please check your config.ini and run the server again', bcolors.RED)
            return 1

        # Check osuapi
        if not generalUtils.stringToBool(glob.conf.config['osuapi']['enable']):
            consoleHelper.printColored("[!] osu!api features are disabled. If you don't have a valid beatmaps table, all beatmaps will show as unranked", bcolors.YELLOW)
            if int(glob.conf.config['server']['beatmapcacheexpire']) > 0:
                consoleHelper.printColored('\n'.join([
                    '[!] IMPORTANT! Your beatmapcacheexpire in config.ini is > 0 and osu!api features are disabled.',
                    'We do not reccoment this, because too old beatmaps will be shown as unranked.',
                    'Set beatmapcacheexpire to 0 to disable beatmap latest update check and fix that issue.'
                ]), bcolors.YELLOW)

        # Set achievements version
        glob.redis.set('lets:achievements_version', glob.ACHIEVEMENTS_VERSION)
        consoleHelper.printColored(f'Achievements version is {glob.ACHIEVEMENTS_VERSION}', bcolors.YELLOW)

        # Discord
        if generalUtils.stringToBool(glob.conf.config['discord']['enable']):
            glob.schiavo = schiavo.schiavo(glob.conf.config['discord']['boturl'], '**lets**')
        else:
            consoleHelper.printColored('[!] Warning! Discord logging is disabled!', bcolors.YELLOW)

        # Check debug mods
        glob.debug = generalUtils.stringToBool(glob.conf.config['server']['debug'])
        if glob.debug:
            consoleHelper.printColored('[!] Warning! Server running in debug mode!', bcolors.YELLOW)

        # Server port
        try:
            serverPort = int(glob.conf.config['server']['port'])
        except:
            consoleHelper.printColored('[!] Invalid server port! Please check your config.ini and run the server again', bcolors.RED)
            return 1

        # Make app
        glob.application = make_app()

        # Set up sentry
        try:
            glob.sentry = generalUtils.stringToBool(glob.conf.config['sentry']['enable'])
            if glob.sentry:
                glob.application.sentry_client = AsyncSentryClient(glob.conf.config['sentry']['dsn'], release=glob.VERSION)
            else:
                consoleHelper.printColored('[!] Warning! Sentry logging is disabled!', bcolors.YELLOW)
        except:
            consoleHelper.printColored('[!] Error while starting Sentry client! Please check your config.ini and run the server again', bcolors.RED)
            return 1

        # Set up Datadog
        try:
            if generalUtils.stringToBool(glob.conf.config['datadog']['enable']):
                glob.dog = datadogClient.datadogClient(glob.conf.config['datadog']['apikey'], glob.conf.config['datadog']['appkey'])
            else:
                consoleHelper.printColored('[!] Warning! Datadog stats tracking is disabled!', bcolors.YELLOW)
        except:
            consoleHelper.printColored('[!] Error while starting Datadog client! Please check your config.ini and run the server again', bcolors.RED)
            return 1

        # Connect to pubsub channels
        pubSub.listener(glob.redis, {
            'lets:beatmap_updates': beatmapUpdateHandler.handler(),
        }).start()

        # Server start message and console output
        consoleHelper.printColored(f'> L.E.T.S. is listening for clients on {glob.conf.config["server"]["host"]}:{serverPort}...', bcolors.GREEN)

        # Start Tornado
        glob.application.listen(serverPort, address=glob.conf.config['server']['host'])
        tornado.ioloop.IOLoop.instance().start()
    finally:
        # Perform some clean up
        print('> Disposing server...')
        glob.fileBuffers.flushAll()
        consoleHelper.printColored('Goodbye!', bcolors.GREEN)

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
