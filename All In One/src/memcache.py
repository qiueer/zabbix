#encoding=UTF8
'''
@author: qiueer
2016-01-29
'''

import commands
import sys
import os
from optparse import OptionParser
import re
import platform
import telnetlib
import json
import time
import getpass

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds

class MCache(object):

    def __init__(self, iphost="127.0.0.1", port=11211, force=False, debug=True):
        self._iphost = iphost
        self._port = port
        self._force = force
        curuser = getpass.getuser()
        self._logpath = "/tmp/zabbix_memcached_by_%s.log" % (curuser)
        self._cache_file = "/tmp/zabbix_memcached_cache_%s_by_%s.txt" % (port,curuser)
        if not port:
            self._cache_file = "/tmp/zabbix_memcached_cache_by_%s.txt" % (curuser)
        self._logger = slog(self._logpath, debug=debug, size=5, count=2)
        
    def get_logger(self):
        return self._logger

    def get_port_list(self):
        # sudo权限，必须授予
        # [root@localhost ~]# tail -n 2 /etc/sudoers
        # Defaults:zabbix   !requiretty 
        # zabbix ALL=(root) NOPASSWD:/bin/netstat

        cmdstr = "sudo netstat  -nlpt | grep 'memcached' | awk '{print $4}'|awk -F: '{print $2}'"
        port_conf = None
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
                return port_conf
        else:
            self._logger.dictlog(width=8, level="info", **logdict)
            
        data = list()
        for port in stdo_list:
            if not port:continue
            port = int(str(port).strip())
            data.append({"{#MEMCACHED_PORT}": port})
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
    
    def get_result_dict_from_cache(self, seconds=60):
        """
        cache文件的内容，第一行是时间戳，第二行是内容
        """
        if os.path.exists(self._cache_file) == False:
            return None
        resobj = None
        with open(self._cache_file, "r") as fd:
            alllines = fd.readlines()
            fd.close()
            if alllines and len(alllines)>1:
                old_unixtime = int(str(alllines[0]).strip())
                now_unixtime = int(time.time())
                if (now_unixtime - old_unixtime) <= seconds: ## 1min内
                    resobj = str(alllines[1]).strip()
                    resobj = json.loads(resobj)
        return resobj
    
    def write_result_dict_to_cache(self, res_dict):
            jsonstr = json.dumps(res_dict)
            now_unixtime = int(time.time())
            with open(self._cache_file, "w") as fd:
                fd.write(str(now_unixtime)+"\n")
                fd.write(jsonstr)
                fd.close()
    
    def _get_result(self, iphost=None, port=None):
        try:
            hostname= iphost if iphost else self._iphost
            port = port if port else self._port
            
            resobj = dict()
            if self._force == False:
                resobj = self.get_result_dict_from_cache()
                
                
            if resobj:
                logdict = {
                    "msg": "Get From FileCache:%s" % (self._cache_file),
                    "content": str(resobj),
                    "orders": ["msg", "content"],
                }
                self._logger.dictlog(width=8, level="info", **logdict)
                return resobj
                
            command = "stats\n"
            tn = telnetlib.Telnet(hostname,port) 
            tn.read_very_eager() 
            tn.write(command)
            ret = tn.read_until('END')
            tn.close()
            
            resobj = dict()
            alllines = re.split("\n", ret)
            for line in alllines:
                line = str(line).strip()
                ln_ary = re.split("[ ,;]+", line)
                if len(ln_ary) < 3:continue
                key = ln_ary[1]
                val = ln_ary[2]
                resobj[key] = val

            logdict = {
                "cmdstr": command,
                "result": str(resobj),
                "orders": ["cmdstr", "result"],
            }
            self._logger.dictlog(width=8, level="info", **logdict)
            
            self.write_result_dict_to_cache(resobj)
            return resobj
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)

    def get_all_key_val(self):
        resobj = self._get_result()
        return json.dumps(resobj, indent=4)
    
    def get_item_val(self, item):
        resobj = self._get_result()
        if resobj and dict(resobj).has_key(item):
            return resobj[item]
        return 0
    
    def get_item_tval(self, item):
        val = self.get_item_val(item)
        if val == None:return 0
        val = str(val)
        try:
            val = int(val)
        except Exception:
            try:
                val = float(val)
                val = "%.2f" % (val)
            except Exception:
                val = str(val)
        return val
    
    def get_item_tval_bak(self, item, val_type="int"):
        val = self.get_item_val(item)
        if val == None:return 0
        if val_type == "int":
            return int(val)
        if val_type == "float":
            fval = "%.2f" % (val)
            return float(fval)
        if val_type == "str":
            return str(val)
        
        return int(val)

def get_key_for_zabbix():
    memc = MCache()
    ds = memc._get_result()
    keyname = "memcached.status"
    macro = "{#MEMCACHED_PORT}"
    for key in dict(ds).keys():
        print "%s[%s,%s]" % (keyname, key, macro)


def main():

    usage = "usage: %prog [options]\n Fetch memcache status"
    parser = OptionParser(usage)
    
    parser.add_option("-l", "--list",  
                      action="store_true", 
                      dest="is_list", 
                      default=False,  
                      help="list all memcache port"
    )

    parser.add_option("-H", "--host", 
                      action="store", 
                      dest="host", 
                      type="string", 
                      default='127.0.0.1', 
                      help="Connect to memcached host."
    )

    parser.add_option("-p", 
                      "--port", 
                      action="store", 
                      dest="port", 
                      type="int", 
                      default=11211, 
                      help="the port for memcached, for example: 11211"
    )
    
    parser.add_option("-d", "--debug",  
                      action="store_true", 
                      dest="debug", 
                      default=False,  
                      help="if open debug mode"
    )
    
    parser.add_option("-a", "--all",  
                      action="store_true", 
                      dest="all", 
                      default=False,  
                      help="print all")
    
    parser.add_option("-i", 
                      "--item", 
                      action="store", 
                      dest="item", 
                      type="string", 
                      default='Uptime', 
                      help="which item to fetch"
    )
    
    (options, args) = parser.parse_args()
    if 1 >= len(sys.argv):
        parser.print_help()
        return

    hostname = options.host
    port = options.port
    memc = MCache(iphost=hostname, port=port, debug=options.debug)
    
    if options.is_list == True:
        print memc.get_port_list()
        return
    
    if options.all == True:
        print memc.get_all_key_val()
        return
        
    try:
        item = options.item
        print memc.get_item_tval(item)

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        memc.get_logger().error(tb)


if __name__ == '__main__':
    main()
