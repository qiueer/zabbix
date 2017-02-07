#-*- encoding:utf-8 -*-
'''
@author: qiueer
'''
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import traceback
import threading

lock = threading.RLock() 

class ColoredFormatter(logging.Formatter):
    '''A colorful formatter.'''

    def __init__(self, fmt = None, datefmt = None):
        logging.Formatter.__init__(self, fmt, datefmt)
        # Color escape string
        COLOR_RED='\033[1;31m'
        COLOR_GREEN='\033[1;32m'
        COLOR_YELLOW='\033[1;33m'
        COLOR_BLUE='\033[1;34m'
        COLOR_PURPLE='\033[1;35m'
        COLOR_CYAN='\033[1;36m'
        COLOR_GRAY='\033[1;37m'
        COLOR_WHITE='\033[1;38m'
        COLOR_RESET='\033[1;0m'
         
        # Define log color
        self.LOG_COLORS = {
            'DEBUG': '%s',
            'INFO': COLOR_GREEN + '%s' + COLOR_RESET,
            'WARNING': COLOR_YELLOW + '%s' + COLOR_RESET,
            'ERROR': COLOR_RED + '%s' + COLOR_RESET,
            'CRITICAL': COLOR_RED + '%s' + COLOR_RESET,
            'EXCEPTION': COLOR_RED + '%s' + COLOR_RESET,
        }
 
    def format(self, record):
        level_name = record.levelname
        msg = logging.Formatter.format(self, record)
        return self.LOG_COLORS.get(level_name, '%s') % msg

class slog(object):
    '''
    slog
    '''
    __logger = None
    
    def __new__(cls, *args, **kwd):
        if slog.__logger is None:
            slog.__logger = object.__new__(cls, *args, **kwd)
        return slog.__logger
    
    @classmethod
    def getLogger(cls):
        cls.__new__(cls)
        return cls.__logger
    
    def __init__(self, filename, size=10, count=5, level= None, debug=False):
        try:
            self._level = level if level else "debug"
            self._size = size if size else 10 #MB
            self._count = count if count else 5 # five pieces
            self._filename = filename
            self._logid = "qiueer"
            if os.path.exists(filename) == False:
                pass
            self._logger = logging.getLogger(self._logid)

            self._logger.handlers = []
            if not len(self._logger.handlers):
                self._logger.setLevel(self._get_map_level(self._level))  
                
                fmt = '[%(asctime)s] %(levelname)s\n%(message)s'
                datefmt = '%Y-%m-%d %H:%M:%S'
                formatter = logging.Formatter(fmt, datefmt)
                
                file_handler = RotatingFileHandler(self._filename, mode='a',maxBytes=self._size*1024*1024,backupCount=self._count)
                self._logger.setLevel(self._get_map_level(self._level))  
                file_handler.setFormatter(formatter)  
                self._logger.addHandler(file_handler)
    
                if debug == True:
                    stream_handler = logging.StreamHandler(sys.stderr)
                    console_formatter = ColoredFormatter(fmt, datefmt)
                    stream_handler.setFormatter(console_formatter)
                    self._logger.addHandler(stream_handler)
        except Exception , expt:
            print traceback.format_exc()
        
    def _is_chinese(self, uchar):
        """判断一个unicode是否是汉字"""
        if uchar >= u'\u4e00' and uchar <= u'\u9fa5':
            return True
        else:
            return False
            
    def _str_rpad(self, text, width=12, fill=" "):
        stext = str(text)
        utext = stext.decode("utf-8")
        cn_count = 0
        for u in utext:
            if self._is_chinese(u):
                cn_count += 1
        return fill * (width - cn_count - len(utext)) + stext

    def _get_right_content(self, content):
        try:
            content = content.decode("utf8")
        except Exception:
            try:
                content = content.decode("gbk")
            except Exception:
                try:
                    content = content.decode("GB2312")
                except Exception:
                    pass
        return content

    def tolog(self, msg, level=None):
        try:
            lock.acquire()
            if not level:
                level = self._level
            level = str(level).lower()
            level = self._get_map_level(level)
            if level == logging.DEBUG:
                self._logger.debug(msg)
            if level == logging.INFO:
                self._logger.info(msg)
            if level == logging.WARN:
                self._logger.warn(msg)
            if level == logging.ERROR:
                self._logger.error(msg)
            if level == logging.CRITICAL:
                self._logger.critical(msg)
            lock.release()
        except Exception , expt:
            print traceback.format_exc()
            
    def dictlog(self, level=None, width=12, fill=u"", **kwargs):
        '''
        kwargs: dict类型，如果包含orders，则按orders的先后顺序
        '''
        try:
            order_keys = []
            if kwargs.has_key("orders") == True:
                order_keys = kwargs["orders"]
            if kwargs.has_key("orders"):
                del(kwargs["orders"]) 
            msgstr = u""
            if order_keys:
                for key in order_keys:
                    if not kwargs.has_key(key): continue
                    val = kwargs[key]
                    key = self._str_rpad(key, width)
                    key = unicode(key, "UTF-8")
                    msgstr = u"%s%s: %s\n" % (msgstr, key, self._get_right_content(val))
            for (key, val) in kwargs.iteritems():
                if kwargs.has_key(key) and key not in order_keys:
                    val = kwargs[key]
                    key = self._str_rpad(key, width)
                    key = unicode(key, "UTF-8")
                    msgstr = u"%s%s: %s\n" % (msgstr, key, self._get_right_content(val))
            msgstr = self._get_right_content(msgstr)
            self.tolog(msgstr, level=level)
        except Exception,expt:
            print traceback.format_exc()
            
    def debug(self,msg):
        self.tolog(msg, level="debug")
        
    def info(self,msg):
        self.tolog(msg, level="info")
        
    def warn(self,msg):
        self.tolog(msg, level="warn")
        
    def error(self,msg):
        self.tolog(msg, level="error")
        
    def critical(self,msg):
        self.tolog(msg, level="critical")
            
    def _get_map_level(self,level="debug"):
        level = str(level).lower()
        if level == "debug":
            return logging.DEBUG
        if level == "info":
            return logging.INFO
        if level == "warn":
            return logging.WARN
        if level == "error":
            return logging.ERROR
        if level == "critical":
            return logging.CRITICAL
        return logging.WARN