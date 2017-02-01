#encoding=UTF8
'''
qiueer@2015-11-23
update: 20170131
redis性能收集
'''
import sys
import os
from optparse import OptionParser
import re

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.filecache import filecache
from qiueer.python.utils import which

class Redis(object):        
    def __init__(self, logpath,  password=None, port=6379, debug=False):
        self._logpath = logpath
        self._password = password
        self._port = port if port else 6379
        self._debug = debug
        self._file_cache_path = "/tmp/.zabbix_memcache_%s.log" % (port)
        self._file_cache = filecache(self._file_cache_path)
        self._logger = slog(self._logpath, debug=debug, size=5, count=5)

    def get_redis_port_list(self):
        # sudo权限，必须授予，在root用户下执行如下命令
        """
        echo "zabbix ALL=(root) NOPASSWD:/bin/netstat" > /etc/sudoers.d/zabbix
        echo 'Defaults:zabbix   !requiretty'  >>  /etc/sudoers.d/zabbix
        chmod 600  /etc/sudoers.d/zabbix
        """

        cmdstr = "sudo netstat  -nlpt | grep 'redis-server' | awk '{print $4}'|awk -F: '{print $2}'"
        c2 = cmds(cmdstr, timeout=3)
        stdo = c2.stdo()
        stde = c2.stde()
        retcode = c2.code()
        
        (stdo_list, stde_list) = (re.split("\n", stdo), re.split("\n", stde))
        logdict = {
            "cmdstr": cmdstr,
            "stdo": stdo,
            "stde": stde,
            "retcode": retcode,
            "orders": ["cmdstr", "stdo", "stde", "retcode"],
        }
        
        if retcode !=0:
                self._logger.dictlog(width=8, level="error", **logdict)
                return
        else:
            self._logger.dictlog(width=8, level="info", **logdict)
            
        data = list()
        for port in stdo_list:
            if not port:continue
            port = int(str(port).strip())
            data.append({"{#REDIS_PORT}": port})
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
            
    def get_item(self,  key, port=None, password=None, force=False):
        """
        参数：
        """
        # cmdstr = "redis-cli -h 127.0.0.1 -p 6379 info | grep 'used_cpu_sys' "
        port = port if port else self._port
        password = password if password else self._password
        
        if force == False:
            value = self._file_cache.get_val_from_json(key)
            logdict = {
                "msg": "Try To Get From Cache File: %s" % self._file_cache_path,
                "key": key,
                "value": value,
                "orders": ["msg", "key", "value"],
            }
            self._logger.dictlog(width=8, level="info", **logdict)
            if value: return value
        
        rds_cli_path = which("redis-cli")
        ## 适配编译安装，这里设置常用的路径
        rds_paths_def = ["/usr/bin/redis-cli", "/bin/redis-cli", "/usr/local/redis-server/bin/redis-cli"]
        
        cmdstr = None
        if rds_cli_path:
            cmdstr = "%s -h 127.0.0.1 -p %s info" % (rds_cli_path, port)
            if password:
                cmdstr = "%s -h 127.0.0.1 -a %s -p %s info" % (rds_cli_path, password, port)
        else:
            for p in rds_paths_def:
                if os.path.exists(p) == False: continue
                cmdstr = "%s -h 127.0.0.1 -p %s info" % (p, port)
                if password: cmdstr = "%s -h 127.0.0.1 -a %s -p %s info" % (p, password, port)
                break

        c2 = cmds(cmdstr, timeout=3)
        stdo = c2.stdo()
        stde = c2.stde()
        retcode = c2.code()
        
        (stdo_list, stde_list) = (re.split("\n", stdo), re.split("\n", stde))
        logdict = {
            "cmdstr": cmdstr,
            "stdo": stdo,
            "stde": stde,
            "retcode": retcode,
            "orders": ["cmdstr", "stdo", "stde", "retcode"],
        }

        if retcode !=0:
            self._logger.dictlog(width=8, level="error", **logdict)
            return
        else:
            self._logger.dictlog(width=8, level="info", **logdict)

        resobj = {}
        for line in stdo_list:
            line = str(line).strip()
            ln_ary = re.split(":", line)
            if ln_ary and len(ln_ary) != 2:continue
            dst_key = str(ln_ary[0]).strip()
            dst_val = str(ln_ary[1]).strip()
            resobj[dst_key] = dst_val
        self._file_cache.save_to_cache_file(resobj)
        return resobj.get(key, "")

def main(passwd_file):
    try:
        usage = "usage: %prog [options]\ngGet Redis Stat"
        parser = OptionParser(usage)
        
        parser.add_option("-l", "--list",  
                          action="store_true", dest="is_list", default=False,  help="if list all redis port")
        
        parser.add_option("-k", "--key", 
                          action="store", dest="key", type="string", 
                          default='blocked_clients', help="execute 'redis-cli info' to see more infomation")
        
        parser.add_option("-a", "--password", 
                          action="store", dest="password", type="string", 
                          default=None, help="the password for redis-server")
        
        parser.add_option("-p", "--port", 
                          action="store", dest="port", type="int", 
                          default=6379, help="the port for redis-server, for example: 6379")
        
        parser.add_option("-d", "--debug",  
                          action="store_true", dest="debug", default=False,  
                          help="if output all")
        
        parser.add_option("-f", "--force",  
                          action="store_true", dest="force", default=False,  
                          help="if force to parse command oupout")
        
        (options, args) = parser.parse_args()
        if 1 >= len(sys.argv):
            parser.print_help()
            return
        
        
        password = options.password
        if not password and os.path.exists(passwd_file):
            fd = open(passwd_file, 'r')
            lines = fd.readlines()
            fd.close()
            for line in lines:
                line = str(line).strip()
                if line == "" or line.startswith("#"):continue
                ln_ary = re.split(r"[|;|,|\s]+", line)
                fport = int(ln_ary[0])
                if fport == int(options.port):
                    password = ln_ary[1]
                    break

        logpath = "/tmp/zabbix_redis_info.log"
        redis_ins = Redis(logpath, password=password, port=options.port, debug=options.debug)
        if options.is_list == True:
            print redis_ins.get_redis_port_list()
            return

        print redis_ins.get_item(options.key, port=options.port, force=options.force)

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        print tb

if __name__ == '__main__':
    redis_passwd_file = "/usr/local/public-ops/zabbix/.redis.passwd"
    main(redis_passwd_file)