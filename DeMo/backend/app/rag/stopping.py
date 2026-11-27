"""Stop-sequence helpers (pure Python, no torch needed, so easy to unit test)."""

STOP_SEQUENCES = [
    "User:",
    "Human:",
    "\n\nQ:",
    "\nAssistant:",
    "<|im_start|>",
    "<|im_end|>",
]


def find_stop(text, stops=STOP_SEQUENCES):
    """Index of the earliest stop sequence in text, or None."""
    hits = [i for s in stops if (i := text.find(s)) != -1]
    return min(hits) if hits else None


def truncate_at_stop(text, stops=STOP_SEQUENCES):
    cut = find_stop(text, stops)
    return (text if cut is None else text[:cut]).strip()


class StopFilter:
    """Filter a token stream so a stop sequence is never shown to the user.

    The last (longest_stop - 1) characters are held back until we know they
    are not the beginning of a stop sequence.
    """

    def __init__(self, stops=STOP_SEQUENCES):
        self.stops = stops
        self.hold = max(len(s) for s in stops) - 1
        self.buf = ""
        self.sent = 0
        self.stopped = False

    def feed(self, piece):
        if self.stopped:
            return ""
        self.buf += piece
        cut = find_stop(self.buf, self.stops)
        if cut is not None:
            self.stopped = True
            out, self.sent = self.buf[self.sent:cut], cut
            return out
        safe = len(self.buf) - self.hold
        if safe > self.sent:
            out, self.sent = self.buf[self.sent:safe], safe
            return out
        return ""

    def flush(self):
        if self.stopped:
            return ""
        out, self.sent = self.buf[self.sent:], len(self.buf)
        return out
