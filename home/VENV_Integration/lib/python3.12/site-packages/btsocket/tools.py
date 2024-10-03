"""Location for tools/functions to be used across various files"""
import logging


def create_module_logger(module_name):
    """helper function to create logger in modules"""
    logger = logging.getLogger(module_name)
    strm_hndlr = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    strm_hndlr.setFormatter(formatter)
    logger.addHandler(strm_hndlr)
    return logger


def format_pkt(data):
    """Put data packets in a human readable format"""
    return ', '.join([f'{bite:#04x}' for bite in data])
