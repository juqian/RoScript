# -*- coding: utf-8 -*-
"""

@author: szy
"""

class RcsException(Exception):
    
    def __init__(self, ErrorInfo):
        super().__init__(self) #初始化父类
        self.errorinfo = ErrorInfo

    def __str__(self):
        return self.errorinfo

if __name__ == '__main__':
    try:
        raise RcsException('异常')
    except RcsException as e:
        print(e)
