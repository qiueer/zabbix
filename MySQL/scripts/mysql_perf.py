#encoding=UTF8
'''
@author: qiueer
2016-01-26
'''

import commands
import sys
import os
from optparse import OptionParser
import re

from qiueer.QLog import Log

class Mysql(object):
    logpath = "/tmp/zabbix_mysql_perf.log"
    
    def __init__(self, iphost, username="your_account", password="your_password", port=3306, debug=True):
        self._iphost = iphost
        self._username = username
        self._password = password
        self._port = port
        self._logger = Log(self.logpath,is_console=debug, mbs=5, count=5)
        self._sql_result = self._get_mysql_cmd_output()
        
    def get_logger(self):
        return self._logger

    def _get_mysql_cmd_output(self, hostname=None,username=None,password=None,port=None):
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
    
    def _get_item_from_sql_output(self, item):
        try:
            result = self._sql_result
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
                
    def get_item_val(self,item):
        return self._get_item_from_sql_output(item)
    
    def get_item_tval(self, item, val_type="int"):
        val = self.get_item_val(item)
        if val_type == "int":
            return int(val)
        if val_type == "float":
            fval = "%.2f" % (val)
            return float(fval)
        if val_type == "str":
            return str(val)
        
        return int(val)

    def get_keybuf_read_hit_rate(self):
        """
        key Buffer 命中率  -- 读
        """
        key_reads = self.get_item_tval("key_reads")
        key_read_requests = self.get_item_tval("key_read_requests")

        if key_read_requests == 0:
            return 100.0
        
        hitrate = "%.2f" % ((1 - key_reads/float(key_read_requests))*100)
        return float(hitrate)
    
    def get_keybuf_write_hit_rate(self):
        """
        key Buffer 命中率  -- 写
        """
        key_writes = self.get_item_tval("key_writes")
        key_write_requests = self.get_item_tval("key_write_requests")

        if key_write_requests == 0:
            return 100.0
        
        hitrate = "%.2f" % ((1 - key_writes/float(key_write_requests))*100)
        return float(hitrate)
    
    def get_innodbbuf_read_hit_rate(self):
        """
        Innodb Buffer 命中率  -- 写
        """
        innodb_buffer_pool_reads = self.get_item_tval("innodb_buffer_pool_reads")
        innodb_buffer_pool_read_requests = self.get_item_tval("innodb_buffer_pool_read_requests")

        if innodb_buffer_pool_read_requests == 0:
            return 100.0

        hitrate = "%.2f" % ((1 - innodb_buffer_pool_reads/float(innodb_buffer_pool_read_requests))*100)
        return float(hitrate)
    
    def get_query_hit_rate(self):
        """
        Query Cache命中率
        """
        Qcache_hits = self.get_item_tval("Qcache_hits")
        Qcache_inserts = self.get_item_tval( "Qcache_inserts")

        total = int(Qcache_hits) + int(Qcache_inserts)
        if total == 0:
            return 100.0
        
        hitrate = "%.2f" % (Qcache_hits/float(total)*100)
        return float(hitrate)
    
    def get_thread_cache_hit_rate(self):
        """
        Thread Cache命中率
        """
        Threads_created = self.get_item_tval("Threads_created")
        Connections = self.get_item_tval( "Connections")

        if Connections == 0:
            return 100.0
        
        hitrate = "%.2f" % ((1-Threads_created/float(Connections))*100)
        return float(hitrate)
    
    def get_lock_scale(self):
        """
        Table_locks_waited/Table_locks_immediate=0.3%  如果这个比值比较大的话，说明表锁造成的阻塞比较严重 
        """
        Table_locks_waited = self.get_item_tval("Table_locks_waited")
        Table_locks_immediate = self.get_item_tval( "Table_locks_immediate")
        if Table_locks_immediate == 0:
            return 100.0
        hitrate = Table_locks_waited/float(Table_locks_immediate)*100
        hitrate = "%.2f" % (hitrate)
        return float(hitrate)
    
    def get_table_scale(self):
        """
        Created_tmp_disk_tables/Created_tmp_tables比值最好不要超过10%，如果Created_tmp_tables值比较大， 可能是排序句子过多或者是连接句子不够优化
        """
        Created_tmp_disk_tables = self.get_item_tval("Created_tmp_disk_tables")
        Created_tmp_tables = self.get_item_tval( "Created_tmp_tables")
        if Created_tmp_tables == 0:
            return 100.0
        hitrate = Created_tmp_disk_tables/float(Created_tmp_tables)*100
        hitrate = "%.2f" % (hitrate)
        return float(hitrate)
        

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
        item = options.item
        keys = ["Key_read_hitrate", "Key_write_hitrate", "Innodb_buf_read_hitrate", "Query_hitrate"]
        if item == "Key_read_hitrate":
            print mysql.get_keybuf_read_hit_rate()
        if item == "Key_write_hitrate":
            print mysql.get_keybuf_write_hit_rate()
        if item == "Innodb_buf_read_hitrate":
            print mysql.get_innodbbuf_read_hit_rate()
        if item == "Query_hitrate":
            print mysql.get_query_hit_rate()
        if item == "Thread_cached_hitrate":
            print mysql.get_thread_cache_hit_rate()
        if item == "Lock_status":
            print mysql.get_lock_scale()
        if item == "Tmp_table_status":
            print mysql.get_table_scale()
            
    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()