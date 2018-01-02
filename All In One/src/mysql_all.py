#encoding=UTF8
'''
qiujingiqn
'''
import sys
from optparse import OptionParser
import re
import os
import getpass

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.filecache import filecache
from qiueer.python.utils import which

class Mysql(object):
    
    def __init__(self, iphost, username="monitor_user", password="m_D1Jo6Jj_xo", port=3306, force=False, debug=True):
        self._iphost = iphost
        self._username = username
        self._password = password
        self._port = port
        self._force = force
        curuser = getpass.getuser()
        self._logpath = "/tmp/zabbix_mysql_variables_slave_status_by_%s.log" % (curuser)
        self._file_cache_path = "/tmp/.zabbix_mysql_variables_slave_status_%s_by_%s.txt" % (port, curuser)
        self._file_cache = filecache(self._file_cache_path)
        self._logger = slog(self._logpath, debug=debug, size=5, count=5)
        
    def get_logger(self):
        return self._logger

    def get_mysql_cmd_output(self, cmdstr, hostname=None,username=None,password=None,port=None):
        try:
            hostname= hostname if hostname else self._iphost
            username = username if username else self._username
            passwd = password if password else self._password
            port = port if port else self._port

            bp = which("mysql")
            binpaths = [
                bp,
                "/data0/mysql/product/bin/mysql",
            ]
            mysql_bp = None
            for p in binpaths:
                if os.path.isfile(p):
                    mysql_path = p
                    break
                
            if not mysql_path:
                return
            sql_cmdstr = '%s -h%s -P%s -u%s -p%s -e "%s"' % (mysql_path,hostname,port,username,passwd, cmdstr)
            c2 = cmds(sql_cmdstr, timeout=2)
            stdo = c2.stdo()
            stde = c2.stde()
            retcode = c2.code()
            logdict = {
                #"cmdstr": cmdstr,
                "cmdstr": sql_cmdstr,
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
                line = str(line).strip().replace(" ", "").strip("|").lower()
                #line_ary = re.split(r"[\s]+", line)
                line_ary = re.split(r"[\s|\||:|;|,]+", line)
                if len(line_ary) < 2:continue
                if content.has_key(line_ary[0]):
                    pass
                content[line_ary[0]] = line_ary[1]
            return content
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)

    def get_value(self, key, hostname=None, username=None, password=None, port=None):
        force = self._force
        key = str(key).lower()
        #cmdstr = "SHOW VARIABLES; SHOW GLOBAL STATUS; SHOW SLAVE STATUS"
        cmdstr = "SHOW VARIABLES; SHOW GLOBAL STATUS; SHOW SLAVE STATUS\G"
        if force == True:
            content = self.get_mysql_cmd_output(cmdstr, hostname=hostname, username=username, password=password, port=port)
            self._file_cache.save_to_cache_file(content)
            return content.get(key, None)
        
        (value, code) = self._file_cache.get_val_from_json(key)
        logdict = {
            "msg": "Try To Get From Cache File: %s" % self._file_cache_path,
            "key": key,
            "value": value,
            "orders": ["msg", "key", "value"],
        }
        self._logger.dictlog(width=8, level="info", **logdict)
        if code == 0: return value
        if code in [1, 2]: ## 超时，或异常或文件不存在
            content = self.get_mysql_cmd_output(cmdstr, hostname=hostname, username=username, password=password, port=port)
            self._file_cache.save_to_cache_file(content)
            (value, code) = self._file_cache.get_val_from_json(key)
            return value
        return None
    
    def get_item_tval(self, key):
        val = self.get_value(key)
        try:
            if re.match("(\d+)", val):
                return int(val)
            if re.match("(\d+\.\d+)", val):
                fval = "%.2f" % (val)
                return float(fval)
            return val
        except:
            return val

    def get_repl_delay_time(self):
        '''
        主从复制延时
        '''
        key = 'Seconds_Behind_Master'
        val = self.get_item_tval(key)
        if str(val).lower().strip() == "null":
            val = -1  #主从同步已断开
        return val
    
    def check_replication(self):
        '''
        主从复制状态，返回值，2正常，其他异常
        '''
        item1 = 'Slave_IO_Running'
        item2 = 'Slave_SQL_Running'
        v1 = self.get_item_tval(item1)
        v2 = self.get_item_tval(item2)
        total = 0
        if str(v1).lower().strip() == "yes":
            total += 1
        if str(v2).lower().strip() == "yes":
            total += 1
        return total

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
        key = options.key
        value = None
        if key == "is_replication":
            value =  mysql.check_replication()
        elif key == "repl_delay_time":
            value = mysql.get_repl_delay_time()
        else:
            value = mysql.get_item_tval(key)
        if value:
            print value

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()
