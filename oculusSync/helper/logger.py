import logging

def get_logger(name, filename="auditor.log", level="INFO"):
    """common formated logger

    :param name: name of the logger
    :type name: str
    :param level: level of the logger(INFO,ERROR,DEBUG,WARNING,FATAL)
    :type level: str
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    channel = logging.StreamHandler()
    channel.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)-4s %(levelname)-4s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    channel.setFormatter(formatter)
    if (logger.hasHandlers()):
        logger.handlers.clear()
    logger.addHandler(channel)
    channel = logging.FileHandler(filename)
    channel.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)-4s %(levelname)-4s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d:%H:%M:%S",
    )
    channel.setFormatter(formatter)
    logger.addHandler(channel)
    return logger