#encoding=UTF8
'''
@author: qiueer
2016-01-19
'''

import sys
import os
from optparse import OptionParser
import re
import getpass

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.filecache import filecache
from qiueer.python.utils import which

class Mysql(object):

    def __init__(self, iphost="localhost", username="your_username", password="your_password", port=3306, force=False, debug=True):
        self._iphost = iphost
        self._username = username
        self._password = password
        self._port = port
        self._force = force
        curuser = getpass.getuser()
        self._logpath = "/tmp/zabbix_mysql_status_by_%s.log" % (curuser)
        self._file_cache_path = "/tmp/.zabbix_mysql_status_%s_by_%s.txt" % (port, curuser)
        self._file_cache = filecache(self._file_cache_path)
        self._logger = slog(self._logpath, debug=debug, size=5, count=5)

    def get_logger(self):
        return self._logger

    def get_mysql_cmd_output(self, hostname=None, username=None, password=None, port=None):
        try:
            hostname= hostname if hostname else self._iphost
            username = username if username else self._username
            passwd = password if password else self._password
            port = port if port else self._port

            sys_binpath = which("mysqladmin")
            ## 适配编译安装，这里设置常用的路径
            binpaths = [sys_binpath, "/usr/bin/mysqladmin", "/data/mysql/product/bin/mysqladmin"]
            
            cmdstr = None
            command = "extended-status"
            for p in binpaths:
                if not p or os.path.exists(p) == False: continue
                cmdstr = "%s -h%s -P%s -u'%s' -p'%s' %s" % (p,hostname,port,username,passwd, command)

            if not cmdstr:return None
            
            c2 = cmds(cmdstr, timeout=3)
            stdo = c2.stdo()
            stde = c2.stde()
            retcode = c2.code()
            logdict = {
                "cmdstr": cmdstr,
                "stdo": stdo,
                "stde": stde,
                "retcode": retcode,
                "orders": ["cmdstr", "stdo", "stde", "retcode"],
            }
            
            if retcode !=0:
                    self._logger.dictlog(width=8, level="error", **logdict)
                    return None
            else:
                self._logger.dictlog(width=8, level="info", **logdict)
                
            output_list = re.split("[\n]+", str(stdo).strip())
            content = dict()
            for line in output_list:
                line = str(line).strip().replace(" ", "").lower().strip("|")
                line_ary = re.split("\|", line)
                if len(line_ary) < 2:continue
                content[line_ary[0]] = line_ary[1]
            return content
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)

    def get_value(self, key, hostname=None, username=None, password=None, port=None):
        force = self._force
        key = str(key).lower()
        if force == True:
            content = self.get_mysql_cmd_output(hostname=hostname, username=username, password=password, port=port)
            self._file_cache.save_to_cache_file(content)
            return content.get(key, None)
        
        (value,code) = self._file_cache.get_val_from_json(key)
        logdict = {
            "msg": "Try To Get From Cache File: %s" % self._file_cache_path,
            "key": key,
            "value": value,
            "orders": ["msg", "key", "value"],
        }
        self._logger.dictlog(width=8, level="info", **logdict)
        if code == 0: return value
        if code in [1, 2]: ## 超时，或异常或文件不存在
            content = self.get_mysql_cmd_output(hostname=hostname, username=username, password=password, port=port)
            self._file_cache.save_to_cache_file(content)
            (value, code) = self._file_cache.get_val_from_json(key)
            return value
        return None

def main():

    usage = "usage: %prog [options]\n Fetch mysql status"
    parser = OptionParser(usage)
    parser.add_option("-H", "--host", action="store", dest="host", type="string", default='localhost', help="Connect to mysql host.")
    parser.add_option("-d", "--debug",  
                      action="store_true", dest="debug", default=False,  
                      help="if output all process")
    parser.add_option("-f", "--force",  
                      action="store_true", dest="force", default=False,  
                      help="if force to fetch current value")
    parser.add_option("-u", "--user", 
                      action="store", dest="username", type="string", 
                      default=None, help="username")
    parser.add_option("-p", "--password", 
                      action="store", dest="password", type="string", 
                      default=None, help="password")
    parser.add_option("-P", "--port", 
                      action="store", dest="port", type="string", 
                      default=3306, help="port")
    parser.add_option("-k", "--key", 
                      action="store", dest="key", type="string", 
                      default='Bytes_sent', help="which key to fetch")
    
    (options, args) = parser.parse_args()
    if 1 >= len(sys.argv):
        parser.print_help()
        return

    hostname = options.host
    username = options.username if options.username else "dbmonitor"
    password = options.password if options.password else "monitor_md5_666"
    port = options.port
    mysql = Mysql(hostname, username=username, password=password, port=port, debug=options.debug, force=options.force)
    try:
        value = mysql.get_value(options.key)
        if value:
            print value

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()
