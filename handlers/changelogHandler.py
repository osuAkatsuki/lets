from datetime import datetime as dt

import tornado.gen
import tornado.web

from common.web import requestsManager


class ChangelogDate:
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def __str__(self):
        return dt.fromtimestamp(self.timestamp).strftime("%b %d, %Y")


class ChangelogEntry:
    def __init__(self, timestamp, author, description, repo):
        self.timestamp = ChangelogDate(int(timestamp))
        self.author = author.strip()
        self._description = description.strip()
        self.repo = repo.strip()

    @property
    def description(self):
        return self._description.lstrip("*").strip().lstrip("+").strip().replace("🔺", "^").replace("🔼", "^")

    @property
    def symbol(self):
        return \
            "*" if self.description.startswith(("Fix", "*")) else \
            "+" if self.description.startswith(("Add", "+")) else \
            ""

    def __str__(self):
        return f"{self.symbol}\t{self.author}\t{self.repo}: {self.description}"


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        output = ""

        try:
            lines = []
            with open("../changelog.txt", "r") as f:
                for i, l in enumerate(f):
                    if i >= 100:
                        break
                    lines.append(l)

            changelog_entries = []
            for line in lines:
                parts = line.split("|")
                if len(parts) != 5:
                    continue
                changelog_entries.append(ChangelogEntry(*parts[1:]))

            if not changelog_entries:
                return
            last_day = changelog_entries[0].timestamp.timestamp // 86400
            output = f"{changelog_entries[0].timestamp}"
            for i, entry in enumerate(changelog_entries):
                this_day = entry.timestamp.timestamp // 86400
                if this_day != last_day:
                    last_day = this_day
                    output += f"\n{entry.timestamp}"
                output += f"\n{entry}"
        finally:
            self.write(output)
