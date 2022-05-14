import os
import logging

LOG_LEVEL = logging.INFO
if 'DIALOG_DEBUG' in os.environ.keys():
    LOG_LEVEL = logging.DEBUG
FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
logging.basicConfig(
    filename='/var/log/dialog.log',
    format=FORMAT,
    encoding='utf-8',  # type: ignore # mypy doesn't like this...
    level=LOG_LEVEL
)
