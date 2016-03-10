#encoding=UTF8
'''
@author: qiueer
2016-01-19
'''

import commands
import sys
import os
from optparse import OptionParser
import re

from qiueer.QLog import Log

class Mysql(object):
    logpath = "/tmp/zabbix_mysql_status.log"
    
    def __init__(self, iphost, username="your_username", password="your_password", port=3306, debug=True):
        self._iphost = iphost
        self._username = username
        self._password = password
        self._port = port
        self._logger = Log(self.logpath,is_console=debug)
        
    def get_logger(self):
        return self._logger
        

    def get_mysql_cmd_output(self, hostname=None,username=None,password=None,port=None):
        try:
            hostname= hostname if hostname else self._iphost
            username = username if username else self._username
            passwd = password if password else self._password
            port = port if port else self._port

            cmdstr = "extended-status"
            mysql_path = "mysqladmin"
            if os.path.isfile("/data/mysql/product/bin/mysqladmin"):
                mysql_path = "/data/mysql/product/bin/mysqladmin"
            sql_cmstr = '%s -h%s -P%s -u%s -p%s %s' % (mysql_path,hostname,port,username,passwd, cmdstr)
            (ret, result) = commands.getstatusoutput(sql_cmstr)
            
            logstr = "sql_cmdstr:%s\nret:%s\nresult:%s\n" % (sql_cmstr,ret,result)
            if ret == 0:
                self._logger.info(logstr)
                return result
            else:
                self._logger.error(logstr)
                result = None
    
            return result
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)
    
    def get_item_from_sql_output(self,result, item):
        try:
            if not result:
                return '0'

            output_list = re.split("[\n]+", str(result).strip())
            item = str(item).lower().strip()
            for line in output_list:
                line = str(line).strip().replace(" ", "").lower().strip("|")
                line_ary = re.split("\|", line)
                if item == line_ary[0]:
                    return line_ary[1]
    
            return '0'
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)
                
    def get_item_val(self, item, hostname=None, port=None):
        result = self.get_mysql_cmd_output(hostname=hostname,port=port)
        return self.get_item_from_sql_output(result,item)


def main():

    usage = "usage: %prog [options]\n Fetch mysql status"
    parser = OptionParser(usage)
    parser.add_option("-H", "--host", action="store", dest="host", type="string", default='localhost', help="Connect to mysql host.")
    parser.add_option("-d", "--debug",  
                      action="store_true", dest="debug", default=False,  
                      help="if output all process")
    parser.add_option("-i", 
                      "--item", 
                      action="store", 
                      dest="item", 
                      type="string", 
                      default='Uptime', 
                      help="which item to fetch")
    
    (options, args) = parser.parse_args()
    if 1 >= len(sys.argv):
        parser.print_help()
        return

    hostname = options.host
    mysql = Mysql(hostname,debug=options.debug)
    try:
        print mysql.get_item_val(options.item)

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()