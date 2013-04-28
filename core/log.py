import logging

class logger(object):
    def __init__(self,logname):
        logging.basicConfig(
            filename = "%(logname)s.log",
            format = "%(levelname)-10s %(asctime)s %(message)s",
            level = logging.INFO)
        return logging.getLogger(logname)

# logging.basicConfig(
#     filename = "app.log",
#     format = "%(levelname)-10s %(asctime)s %(message)s",
#     level = logging.INFO)
log = logger("app")
# log.critical("can't open file")
        
