import logging
from functools import partialmethod
from logging.handlers import WatchedFileHandler
from datetime import datetime
from os import makedirs
import coloredlogs
# from utils.DiscordWebhookLoggerHandler import WebhookHandler, WhFormatter
from utils.SteelSeriesLoggerHandler import SteelSeriesHandler, SsFormatter


class MyLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def addLevel(cls, name, lvl, style):
        """Don't forget to call self.install() afterwards if you wish to add colored levels after mylogger.init()"""
        setattr(cls, name.lower(), partialmethod(cls._anyLog, lvl))
        logging.addLevelName(lvl, name)
        coloredlogs.DEFAULT_LEVEL_STYLES.update({name.lower(): style})

    def _anyLog(self, level, message, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, message, args, stacklevel=2, **kwargs)

    def __call__(self, message, *args, **kwargs):
        if self.isEnabledFor(logging.INFO):
            self._log(logging.INFO, message, args, **kwargs)

    def install(self):
        """if you wish to add more colored levels, call this after calling logger.addLevel()"""
        coloredlogs.install(level=self.getEffectiveLevel(), logger=self, fmt=FORMAT, style="{")


# formatting the colorlogger
# fmt = "[ %(asctime)s %(name)s (%(filename)s) %(lineno)d %(funcName)s() %(levelname)s ] %(message)s"
FORMAT = "[ {asctime} {name} {filename} {lineno} {funcName}() {levelname} ] {message}"
coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {'color': 100}, 'lineno': {'color': 'magenta'}, 'levelname': {'bold': True, 'color': 'black'}, 'filename': {'color': 25}, 'name': {'color': 'blue'}, 'funcname': {'color': 'cyan'}}
coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'bold': True, 'color': 'red'}, 'debug': {'bold': True, 'color': 'black'}, 'error': {'color': 'red'}, 'info': {'color': 'green'}, 'notice': {'color': 'magenta'}, 'spam': {'color': 'green', 'faint': True}, 'success': {'bold': True, 'color': 'green'}, 'verbose': {'color': 'blue'}, 'warning': {'color': 'yellow'}}

logging.setLoggerClass(MyLogger)
baselogger: MyLogger = logging.getLogger("main")
baselogger.propagate = False
baselogger.addLevel("Event", 25, {"color": "white"})
baselogger.addLevel("React", 19, {"color": "white"})
baselogger.addLevel("Highlight", 51, {"color": "magenta", "bold": True})
# baselogger.addLevel("Blue", 23, {"color": 25})
# baselogger.addLevel("Gold", 22, {"color": 214})
# https://coloredlogs.readthedocs.io/en/latest/api.html#available-text-styles-and-colors


def init(args=None):
    # if True: #if you need a text file
    if args and args.logfile: #if you need a text file

        formatter = logging.Formatter(FORMAT, style="{")  # this is for default logger
        filename = f"./logs/log_{datetime.now().strftime('%m-%d-%H-%M-%S')}.txt"
        makedirs(r"./logs", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as _:
            pass
        fl = WatchedFileHandler(filename, encoding="utf-8") #not for windows but if i ever switch to linux
        fl.setFormatter(formatter)
        fl.setLevel(19)
        # fl.addFilter(lambda rec: rec.levelno >= 25)
        baselogger.addHandler(fl)

    # wh_formatter = WhFormatter(github_url="https://github.com/theonlypeti/ppbot/tree/master")
    # wh_formatter.logcolor.update({25: 16777215})
    #
    # wh = WebhookHandler(url="https://discord.com/api/webhooks/1261335469447450684/QjBXJuj3rul9gEIEGAPntsArt60bORt1CH608Z9YRF7fyTEsa7ndYmT7TJfMb9Xt2aP2")
    # wh.setFormatter(wh_formatter)
    # wh.setLevel(logging.DEBUG)
    # wh.addFilter(lambda rec: rec.levelno < 25)
    # baselogger.addHandler(wh)
    #
    # whe = WebhookHandler(url="https://discord.com/api/webhooks/1261755329327267880/geyec85IIm9JtzTN12Fh4wrrXt_xYwlNioe-UBnxs7Tv_A9FNXR6Fwk2lEVJglIU8d6s")
    # whe.setFormatter(wh_formatter)
    # whe.setLevel(25)
    # baselogger.addHandler(whe)
    #
    sse = SteelSeriesHandler(name="poit")
    sse.setLevel(logging.INFO)

    ssf = SsFormatter(flash_freq=2, n_flashes=0, display_time=1000)
    if sse.ok(): #this check is only to supress a warning message, it's not necessary
        sse.setFormatter(ssf)

    baselogger.addHandler(sse)

    baselogger.setLevel(logging.DEBUG)  # base is debug, so the file handler could catch debug msgs too
    if args and args.debug:
        coloredlogs.install(level=logging.DEBUG, logger=baselogger, fmt=FORMAT, style="{")
    else:
        coloredlogs.install(level=logging.INFO, logger=baselogger, fmt=FORMAT, style="{")
    return baselogger
