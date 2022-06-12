import MySQLdb

import install_glob as glob


def run():
    c = glob.sqlcon.cursor()
    make_0(c)
    alt_0(c)
    print("Eyy! Database has been updated.")

def make_0(c):
    c.execute("CREATE TABLE users_achievements (id int(11) NOT NULL,user_id int(11) NOT NULL,achievement_id int(11) NOT NULL,time int(11) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=latin1")
    c.execute("ALTER TABLE users_achievements ADD PRIMARY KEY (id)")
    c.execute("ALTER TABLE users_achievements MODIFY id int(11) NOT NULL AUTO_INCREMENT")

def alt_0(c):
    c.execute("ALTER TABLE users ADD achievements_version INT NOT NULL DEFAULT '0' AFTER rank")

def make_connect(obj):
    glob.sqlcon = MySQLdb.connect(**obj)
