# -*- coding: utf-8 -*-
"""
What does this do......!
"""

import os
import time

import logging

log = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(levelname)-8s-> %(message)s  '
                           '(%(module)s: %(lineno)s)',
                    datefmt='%m/%d/%Y %I:%M:%S')
logging.getLogger(__name__).setLevel(logging.NOTSET)
# logging.getLogger('soco').setLevel(logging.NOTSET)
#logging.getLogger('requests').setLevel(logging.NOTSET)


if __name__ == '__main__':
    pass

