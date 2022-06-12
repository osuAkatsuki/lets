from configparser import ConfigParser
from os import path


class config:
    """
    config.ini object

    config -- list with ini data
    default -- if true, we have generated a default config.ini
    """

    config = ConfigParser()
    fileName = '' # config filename
    default = True

    # Check if config.ini exists and load/generate it
    def __init__(self, __file):
        """Initialize a config object"""
        self.fileName = __file
        if path.isfile(self.fileName):
            # config.ini found, load it
            self.config.read(self.fileName)
            self.default = False
        else:
            # config.ini not found, generate a default one
            self.generateDefaultConfig()
            self.default = True

    # Check if config.ini has all needed the keys
    def checkConfig(self):
        """
        Check if this config has the required keys

        return -- True if valid, False if not
        """

        try:
            # Try to get all the required keys
            self.config.get('db','host')
            self.config.get('db','username')
            self.config.get('db','password')
            self.config.get('db','database')
            self.config.get('db','workers')

            self.config.get('ftp', 'enable')
            self.config.get('ftp', 'host')
            self.config.get('ftp', 'username')
            self.config.get('ftp', 'password')

            self.config.get('redis','host')
            self.config.get('redis','port')
            self.config.get('redis','database')
            self.config.get('redis','password')

            self.config.get('server','host')
            self.config.get('server','port')
            self.config.get('server', 'debug')
            self.config.get('server', 'beatmapcacheexpire')
            self.config.get('server', 'serverurl')
            self.config.get('server', 'banchourl')
            self.config.get('server', 'threads')
            self.config.get('server', 'apikey')

            self.config.get('cache', 'enable')
            self.config.get('cache', 'port')

            self.config.get('sentry','enable')
            self.config.get('sentry','dsn')

            self.config.get('datadog', 'enable')
            self.config.get('datadog', 'apikey')
            self.config.get('datadog', 'appkey')

            self.config.get('osuapi','enable')
            self.config.get('osuapi','apiurl')
            self.config.get('osuapi','apikey')

            self.config.get('mirror', 'apiurl')

            self.config.get('discord','enable')
            self.config.get('discord','boturl')
            self.config.get('discord', 'devgroup')
            self.config.get('discord', 'secretwebhook')

            self.config.get('cono', 'enable')

            """ Webhooks """
            self.config.get('webhooks', 'now_ranked')
            #self.config.get('webhooks', 'rank_requests')

            # Anticheat
            self.config.get('webhooks', 'ac_general') # GMT+
            self.config.get('webhooks', 'ac_confidential') # cmyui only

            self.config.get('cmyui', 'mac')
            self.config.get('cmyui', 'unique')
            self.config.get('cmyui', 'disk')

            return True
        except:
            return False


    # Generate a default config.ini
    def generateDefaultConfig(self):
        """Open and set default keys for that config file"""

        # Open config.ini in write mode
        f = open(self.fileName, 'w')

        # Set keys to config object
        self.config.add_section('db')
        self.config.set('db', 'host', 'localhost')
        self.config.set('db', 'username', 'root')
        self.config.set('db', 'password', '')
        self.config.set('db', 'database', 'ripple')
        self.config.set('db', 'workers', '16')

        self.config.add_section('ftp')
        self.config.set('ftp', 'enable', 'False')
        self.config.set('ftp', 'host', 'localhost')
        self.config.set('ftp', 'username', '')
        self.config.set('ftp', 'password', '')

        self.config.add_section('redis')
        self.config.set('redis', 'host', 'localhost')
        self.config.set('redis', 'port', '6379')
        self.config.set('redis', 'database', '0')
        self.config.set('redis', 'password', '')

        self.config.add_section('server')
        self.config.set('server', 'host', '0.0.0.0')
        self.config.set('server', 'port', '5002')
        self.config.set('server', 'debug', 'False')
        self.config.set('server', 'beatmapcacheexpire', '86400')
        self.config.set('server', 'serverurl', 'http://127.0.0.1:5002')
        self.config.set('server', 'banchourl', 'http://127.0.0.1:5001')
        self.config.set('server', 'threads', '16')
        self.config.set('server', 'apikey', 'changeme')

        self.config.add_section('cache')
        self.config.set('cache', 'enable', 'False')
        self.config.set('cache', 'port', '5000')

        self.config.add_section('sentry')
        self.config.set('sentry', 'enable', 'False')
        self.config.set('sentry', 'dsn', '')

        self.config.add_section('datadog')
        self.config.set('datadog', 'enable', 'False')
        self.config.set('datadog', 'apikey', '')
        self.config.set('datadog', 'appkey', '')

        self.config.add_section('osuapi')
        self.config.set('osuapi', 'enable', 'True')
        self.config.set('osuapi', 'apiurl', 'https://osu.ppy.sh')
        self.config.set('osuapi', 'apikey', 'YOUR_OSU_API_KEY_HERE')

        self.config.add_section('mirror')
        self.config.set('mirror', 'apiurl', 'http://pisstau.be/api')

        self.config.add_section('discord')
        self.config.set('discord', 'enable', 'False')
        self.config.set('discord', 'boturl', '')
        self.config.set('discord', 'devgroup', '')
        self.config.set('discord', 'secretwebhook', '')

        self.config.add_section('cono')
        self.config.set('cono', 'enable', 'False')

        self.config.add_section('webhooks')
        self.config.set('webhooks', 'now_ranked', 'https://discordapp.com/api/webhooks/')
        #self.config.set('webhooks', 'rank_requests', 'https://discordapp.com/api/webhooks/')

        # Anticheat
        self.config.set('webhooks', 'ac_general', 'https://discordapp.com/api/webhooks/') # GMT+
        self.config.set('webhooks', 'ac_confidential', 'https://discordapp.com/api/webhooks/') # cmyui only

        self.config.add_section('cmyui')
        self.config.set('cmyui', 'mac', '')
        self.config.set('cmyui', 'unique', '')
        self.config.set('cmyui', 'disk', '')

        # Write ini to file and close
        self.config.write(f)
        f.close()
