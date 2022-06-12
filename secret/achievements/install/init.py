import db


def run():
    db.run()

def setup_args():
    db.make_connect(
        {
            "host": input("Host: "),
            "user": input("User: "),
            "passwd": input("Password: "),
            "db": input("Database: ")
        }
    )

def pass_args(obj):
    db.make_connect(obj)

if __name__ == "__main__":
    setup_args()
    run()
