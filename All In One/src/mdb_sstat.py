#encoding=UTF8
'''
mongodb监控
@author: qiueer
2016-02-15
'''

import commands
import sys
import os
from optparse import OptionParser
import re
import time
import platform
import json
import pprint
import types

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.utils import which
from qiueer.python.filecache import filecache


def get_user_passwd_by_port(conffile, port):
    if os.path.exists(conffile) == False:
        return (None,None)
    with open(conffile,'r') as fd:
        alllines = fd.readlines()
        for line in alllines:
            line = str(line).strip()
            if not line or line.startswith("#"):continue
            ln_ary = re.split('[ ,;]+', line)
            if len(ln_ary) < 3:continue
            if str(port) == ln_ary[0]:
                return (ln_ary[1],ln_ary[2])
    return (None, None)

class MGdb(object):

    def __init__(self, iphost="127.0.0.1", port=27017, username=None, password=None, force=False, debug=True):
        self._iphost = iphost
        self._port = port
        self._username = username
        self._password = password
        self._force = force
        
        self._logpath = "/tmp/zabbix_mongodb.log"
        self._cache_file_path = "/tmp/.zabbix_mongodb_cache_%s.txt" %(port)
        if not port:
            self._cache_file_path = "/tmp/.zabbix_mongodb_cache.txt"
    
        self._file_cache = filecache(self._cache_file_path)
        self._logger = slog(self._logpath, debug=debug, size=5, count=2)
        
    def get_logger(self):
        return self._logger

    def get_port_list(self):
        # sudo权限，必须授予
        # [root@localhost ~]# tail -n 2 /etc/sudoers
        # Defaults:zabbix   !requiretty 
        # zabbix ALL=(root) NOPASSWD:/bin/netstat
        binname = "mongod"
        cmdstr = "sudo netstat  -nlpt | grep '%s' | awk '{print $4}' | awk -F: '{print $2}'" % (binname)
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
            port = int(str(port).strip())
            data.append({"{#MONGODB_PORT}": port})
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
    
    def _get_result(self, iphost=None, port=None, username=None, password=None):
        try:
            hostname= iphost if iphost else self._iphost
            port = port if port else self._port
            username = username if username else self._username
            password = password if password else self._password
            resobj = None

            binpt = which("mongo")
            pbinpaths = [
                 binpt,
                 "/usr/local/mongodb/bin/mongo",
                 "/home/albert/mongodb/mongodb-3.0.0/bin/mongo",
            ]
            cmdstr = None
            for bp in pbinpaths:
                if not bp:continue
                if not os.path.exists(bp): continue
                cmdstr = "echo 'db.serverStatus()' | %s admin --host '%s'  --port %s --quiet" % (bp, hostname, port)
                if username and password:
                    cmdstr = "echo 'db.serverStatus()' | %s admin --host '%s'  --port %s -u '%s' -p '%s' --quiet" % (bp, hostname, port, username, password)
                break
            if not cmdstr:
                return None

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
                    return
            else:
                self._logger.dictlog(width=8, level="info", **logdict)

            stdo_str = stdo
            stdo_str = stdo_str.replace("NumberLong(", "").replace(")", "").replace("ISODate(", "")
            #print stdo_str
            resobj = json.loads(stdo_str)
            return resobj
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)

    def get_item_val(self, *items):
        resobj = self._get_result()
        src_res = resobj
        for item in items:
            if resobj and type(resobj) == types.DictType and resobj.has_key(item):
                resobj = resobj[item]
        if resobj == None or resobj == src_res:
            resobj = 0
        return resobj
    
    def get_result(self):
        return self._get_result()
    
    def get_item_tval(self,  items, val_type="int"):
        val = self.get_item_val(*items)
        if val == None:return None  #0也满足此条件
        try:
            if val_type == "int":
                return int(val)
            if val_type == "float":
                fval = "%.2f" % (val)
                return float(fval)
            if val_type == "str":
                return str(val)
            return int(val)
        except:
            return val
        
    def get_value(self, key):
        if self._force == True:
            resobj = self._get_result()
            self._file_cache.save_to_cache_file(resobj)
            return resobj.get(key, None)
            
        (value, code) = self._file_cache.get_val_from_json(key)
        logdict = {
            "msg": "Try To Get From Cache File: %s" % self._cache_file_path,
            "key": key,
            "value": value,
            "orders": ["msg", "key", "value"],
        }
        self._logger.dictlog(width=8, level="info", **logdict)
        if code == 0: return value
        if code in [1, 2]: ## 超时，或异常或文件不存在
            resobj = self._get_result()
            self._file_cache.save_to_cache_file(resobj)
            (value, code) = self._file_cache.get_val_from_json(key)
            return value
        return None

    def print_all_key_val(self):
        resobj = self._get_result()
        print json.dumps(resobj, indent=4)

def main(password_file):

    usage = "usage: %prog [options]\n Fetch mongodb status"
    parser = OptionParser(usage)
    
    parser.add_option("-l", "--list",  
                      action="store_true", dest="is_list", default=False,  
                      help="if list all port")

    parser.add_option("-H", "--host",
                      action="store", dest="host", type="string", 
                      default='localhost', help="Connect to memcached host.")

    parser.add_option("-p",  "--port", 
                      action="store", dest="port", type="int", 
                      default=27017, help="the port for mongodb, for example: 27017")
    
    parser.add_option("-u", "--user", 
                      action="store", dest="username", type="string", 
                      default=None, help="username")
    
    parser.add_option("-P", "--password", 
                      action="store", dest="password", type="string", 
                      default=None, help="password")

    parser.add_option("-k", "--key", 
                      dest="key", action="store",type="string", 
                      default="network.bytesIn", help="which key to fetch")
    
    parser.add_option("-f", "--force",  
                      action="store_true", dest="force", default=False,  
                      help="if get from cache")
    
    parser.add_option("-d", "--debug",  
                      action="store_true", dest="debug", 
                      default=False,  help="if open debug mode")
    
    (options, args) = parser.parse_args()
    if 1 >= len(sys.argv):
        parser.print_help()
        return

    hostname = options.host
    port = options.port
    
    
    username = options.username
    password = options.password
    
    if password == None or username == None:
        (username, password) = get_user_passwd_by_port(password_file, port)
        #print "Get (username=%s,password=%s) From Config File By port:%s" % (username, password, port)

    monitor_obj = MGdb(iphost=hostname, port=port, username=username, password=password, debug=options.debug, force=options.force)
    
    if options.is_list == True:
        print monitor_obj.get_port_list()
        return
    
    try:
        key = options.key
        value = monitor_obj.get_value(key)
        if value != None:
            print value

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        monitor_obj.get_logger().error(tb)


if __name__ == '__main__':
    password_file = "/usr/local/public-ops/zabbix/.mongodb.passwd"
    main(password_file)