# -*- coding: utf-8 -*-
"""

@author: szy
"""

class RcsException(Exception):
    def __init__(self, ErrorInfo):
        super().__init__(self)
        self.errorinfo = ErrorInfo

    def __str__(self):
        return self.errorinfo


if __name__ == '__main__':
    try:
        raise RcsException('error')
    except RcsException as e:
        print(e)
