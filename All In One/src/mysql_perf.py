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
        self._logpath = "/tmp/zabbix_mysql_perf_by_%s.log" % (curuser)
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
        mmap = {
            "Key_read_hitrate": mysql.get_keybuf_read_hit_rate,
            "Key_write_hitrate": mysql.get_keybuf_write_hit_rate,
            "Innodb_buf_read_hitrate": mysql.get_innodbbuf_read_hit_rate,
            "Query_hitrate": mysql.get_query_hit_rate,
            "Thread_cached_hitrate": mysql.get_thread_cache_hit_rate,
            "Lock_status": mysql.get_lock_scale,
            "Tmp_table_status": mysql.get_table_scale,
        }
        mt = mmap.get(key, None)
        if mt:
            val = mt()
            if val != None:
                print val

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        mysql.get_logger().error(tb)


if __name__ == '__main__':
    main()
