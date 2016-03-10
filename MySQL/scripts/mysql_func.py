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
from qiueer import QCmd

class Mysql(object):
    logpath = "/tmp/zabbix_mysql_func.log"
    
    def __init__(self, iphost, username="your_db_account", password="user_password", port=3306, debug=True):
        self._iphost = iphost
        self._username = username
        self._password = password
        self._port = port
        self._logger = Log(self.logpath,is_console=debug, mbs=10, count=5)
        
    def get_logger(self):
        return self._logger
        

    def get_mysql_cmd_output(self, cmdstr, hostname=None,username=None,password=None,port=None):
        try:
            hostname= hostname if hostname else self._iphost
            username = username if username else self._username
            passwd = password if password else self._password
            port = port if port else self._port

            mysql_bin_path = "mysql"
            if os.path.isfile("/data/mysql/product/bin/mysql"):
                mysql_bin_path = "/data/mysql/product/bin/mysql"
            sql_cmstr = '%s -h%s -P%s -u%s -p%s -e "%s"' % (mysql_bin_path,hostname,port,username, passwd, cmdstr)
            
            (stdo,stde,retcode) = QCmd.docmd(sql_cmstr, timeout=1, raw=True)
            #(ret, result) = commands.getstatusoutput(sql_cmstr)
            
            logstr = "sql_cmdstr:%s\nret:%s\nstdo:%s\nstde:%s" % (sql_cmstr, retcode, stdo, stde)
            if retcode == 0:
                self._logger.info(logstr)
                return stdo
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
                
    def is_mysql_can_write(self, hostname=None, port=None):
        cmdstr = "insert into test.t_zabbix(insert_timestamp)values(current_timestamp());"
        result = self.get_mysql_cmd_output(cmdstr,hostname=hostname,port=port)
        if result == None: ## 超时写入，判定为不可写入
            return 0
        return 1


def main():

    usage = "usage: %prog [options]\n Check MySQL Function"
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
        
        item = options.item
        if item == "is_can_write":
            print mysql.is_mysql_can_write()
        #print mysql.get_item_val(options.item)

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()