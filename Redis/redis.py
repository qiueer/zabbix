#encoding=UTF8
'''
2015-11-23
qiujingiqn
redis性能收集
'''

import commands
import sys
from optparse import OptionParser
import re
import platform

import logging
from logging.handlers import RotatingFileHandler
import os

def docmd(command,timeout=300, raw=False):
        '''
        功能：
                执行命令
        参数：command，命令以及其参数/选项
                timeout，命令超时时间，单位秒
                debug，是否debug，True输出debug信息，False不输出
                raw，命令输出是否为元素的输出，True是，False会将结果的每一行去除空格、换行符、制表符等，默认False
        返回：
                含有3个元素的元组，前两个元素类型是list，第三个元素类型是int，第一个list存储stdout的输出，第二个list存储stderr的输出，第三int存储命令执行的返回码，其中-1表示命令执行超时
        示例：
                cmd.docmd("ls -alt")
        '''
        import subprocess, datetime, os, time, signal
        start = datetime.datetime.now()

        ps = None
        retcode = 0
        if platform.system() == "Linux":
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        while ps.poll() is None:
                time.sleep(0.2)
                now = datetime.datetime.now()
                if (now - start).seconds > timeout:
                        os.kill(ps.pid, signal.SIGINT)
                        retcode = -1
                        return (None,None,retcode)
        stdo = ps.stdout.readlines()
        stde = ps.stderr.readlines()
        
        if not ps.returncode:
                retcode = ps.returncode
        
        if raw == True:  #去除行末换行符
                stdo = [line.strip("\n") for line in stdo]
                stde = [line.strip("\n") for line in stde]
        
        if raw == False: #去除行末换行符，制表符、空格等
                stdo = [str.strip(line) for line in stdo]
                stde = [str.strip(line) for line in stde]

        return (stdo,stde,retcode)


def get_logstr(list_dict, max_key_len=16, join_str="\n"):
    log_str = ""
    for conf in list_dict:
        for (key,val) in dict(conf).iteritems():
            log_str = log_str + str(key).ljust(max_key_len) + ": " + str(val) + join_str
    log_str = log_str.strip() # 去掉尾部 \n
    return log_str

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

class Log(object):
    '''
    log
    '''
    def __init__(self, filename, level="debug", logid="qiueer", mbs=20, count=10,is_console=False):
        '''
        mbs: how many MB
        count: the count of remain
        '''
        try:
            self._level = level
            self._filename = filename
            self._logid = logid
            self._logger = logging.getLogger(self._logid)

            if not len(self._logger.handlers):
                self._logger.setLevel(self.get_map_level(self._level))  
                
                fmt = '[%(asctime)s] %(levelname)s\n%(message)s'
                datefmt = '%Y-%m-%d %H:%M:%S'
                formatter = logging.Formatter(fmt, datefmt)
                
                maxBytes = int(mbs) * 1024 * 1024
                file_handler = RotatingFileHandler(self._filename, mode='a',maxBytes=maxBytes,backupCount=count)
                self._logger.setLevel(self.get_map_level(self._level))  
                file_handler.setFormatter(formatter)  
                self._logger.addHandler(file_handler)
                
                if is_console == True:
                    stream_handler = logging.StreamHandler(sys.stderr)
                    console_formatter = ColoredFormatter(fmt, datefmt)
                    stream_handler.setFormatter(console_formatter)
                    self._logger.addHandler(stream_handler)

        except Exception as expt:
            print expt
            
    def tolog(self, msg, level=None):
        try:
            level = level if level else self._level
            level = str(level).lower()
            level = self.get_map_level(level)
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
        except Exception as expt:
            print expt
            
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
            
    def get_map_level(self,level="debug"):
        level = str(level).lower()
        #print "get_map_level:",level
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
        

class Redis(object):        
    def __init__(self, logpath,  password=None, port=6379, debug=False):
        self._logpath = logpath
        self._password = password
        self._port = port if port else 6379
        self._debug = debug
        self._logger = Log(logpath,is_console=self._debug)

    def get_redis_port_list(self):
        # sudo权限，必须授予
        # [root@localhost ~]# tail -n 2 /etc/sudoers
        # Defaults:zabbix   !requiretty 
        # zabbix ALL=(root) NOPASSWD:/bin/netstat

        cmdstr = "sudo netstat  -nlpt | grep 'redis-server' | awk '{print $4}'|awk -F: '{print $2}'"
        disk_space_info = []
        (stdo_list, stde_list, retcode) = docmd(cmdstr, timeout=3, raw = False)
        
        log_da = [{"cmdstr": cmdstr},{"ret": retcode},{"stdo": "".join(stdo_list)}, {"stde": "".join(stde_list)}]
        logstr = get_logstr(log_da, max_key_len=10)
        
        if retcode !=0:
                self._logger.error(logstr)
                return disk_space_info
        else:
            self._logger.info(logstr)
            
        data = list()
            
        for port in stdo_list:
            port = int(str(port).strip())
            data.append({"{#REDIS_PORT}": port})
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
            
    def get_item(self,  key, port=None, password=None):
        """
        参数：
        """
        # cmdstr = "redis-cli -h 127.0.0.1 -p 6379 info | grep 'used_cpu_sys' "
        port = port if port else self._port
        password = password if password else self._password
        cmdstr = None
        cmdstr = "redis-cli -h 127.0.0.1 -p %s info | grep '%s' " % (port, key)
        if password:
            cmdstr = "redis-cli -h 127.0.0.1 -a %s -p %s info | grep '%s' " % (password, port, key)
        
        (stdo_list, stde_list, retcode) = docmd(cmdstr, timeout=5, raw = False)
        
        log_da = [{"cmdstr": cmdstr},{"ret": retcode},{"stdo": "".join(stdo_list)}, {"stde": "".join(stde_list)}]
        logstr = get_logstr(log_da, max_key_len=10)
        
        if retcode !=0:
                self._logger.error(logstr)
                return None
        else:
            self._logger.info(logstr)

        for line in stdo_list:
            line = str(line).strip()
            ln_ary = re.split(":", line)
            if ln_ary and len(ln_ary) != 2:continue
            dst_key = str(ln_ary[0]).strip()
            dst_val = str(ln_ary[1]).strip()
            if key == dst_key:
                return dst_val
        return None

def main():
    try:
        usage = "usage: %prog [options]\ngGet Redis Stat"
        parser = OptionParser(usage)
        
        parser.add_option("-l", "--list",  
                          action="store_true", dest="is_list", default=False,  
                          help="if list all redis port")
        
        parser.add_option("-k", 
                          "--key", 
                          action="store", 
                          dest="key", 
                          type="string", 
                          default='blocked_clients', 
                          help="execute 'redis-cli info' to see more infomation")
        
        parser.add_option("-a", 
                          "--password", 
                          action="store", 
                          dest="password", 
                          type="string", 
                          default="", 
                          help="the password for redis-server")
        
        parser.add_option("-p", 
                          "--port", 
                          action="store", 
                          dest="port", 
                          type="int", 
                          default=None, 
                          help="the port for redis-server, for example: 6379")
        
        parser.add_option("-d", "--debug",  
                          action="store_true", dest="debug", default=False,  
                          help="if output all")
        
        (options, args) = parser.parse_args()
        if 1 >= len(sys.argv):
            parser.print_help()
            return
        
        logpath = "/tmp/zabbix_redis_info.log"

        redis_ins = Redis(logpath, password=options.password, port=options.port, debug=options.debug)
        if options.is_list == True:
            print redis_ins.get_redis_port_list()
            return

        print redis_ins.get_item(options.key)

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        print tb

if __name__ == '__main__':
    main()