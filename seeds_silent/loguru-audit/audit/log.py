"""Audit logging: write events to a file and read them back for the compliance report."""
import re

from loguru import logger

LINE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (?P<level>\w+)\s*\| (?P<where>[^ ]+) - (?P<message>.*)$")


def open_log(path):
    """Send audit events to `path` using the logger's standard line format."""
    logger.remove()
    return logger.add(path, colorize=False)


def record(user, action):
    logger.info("{} {}", user, action)


def parse_line(line):
    """Parse one line of the audit log into its fields; None when the line is not an audit record."""
    m = LINE.match(line.rstrip("\n"))
    return m.groupdict() if m else None


def read_events(path):
    """Every (user, action) pair recorded in the audit log, in order."""
    events = []
    with open(path) as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                user, _, action = parsed["message"].partition(" ")
                events.append((user, action))
    return events
