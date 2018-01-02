#encoding=UTF8
'''
qiueer@201706
'''
import sys
from optparse import OptionParser
import re
import os
import socket
import urllib
import getpass

from qiueer.python.cmds import cmds
from qiueer.python.slog import slog
from qiueer.python.filecache import filecache

socket.setdefaulttimeout(2)

class NginxPerf(object):
    
    def __init__(self, uri, port=80, iphost="localhost", force=False, debug=True):
        self._uri = uri
        self._iphost = iphost
        self._port = port
        self._force = force
        curuser = getpass.getuser()
        self._logpath = "/tmp/nginx_perf_by_%s.log" % (curuser)
        self._file_cache_path = "/tmp/.nginx_perf_cache_%s_by_%s.txt" % (port, curuser)
        self._file_cache = filecache(self._file_cache_path)
        self._logger = slog(self._logpath, debug=debug, size=5, count=5)
        
    def get_logger(self):
        return self._logger

    def get_port_list(self):
        # sudo权限，必须授予，在root用户下执行如下命令
        """
        echo "zabbix ALL=(root) NOPASSWD:/bin/netstat" > /etc/sudoers.d/zabbix
        echo 'Defaults:zabbix   !requiretty'  >>  /etc/sudoers.d/zabbix
        chmod 600  /etc/sudoers.d/zabbix
        """

        cmdstr = "sudo netstat  -nlpt | grep 'nginx' | awk '{print $4}'|awk -F: '{print $2}'"
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
            data.append({"{#NGINX_PORT}": port})
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
    
    def get(self, uri, port=80, iphost="localhost"):
        try:
            uri = uri if uri else self._uri
            iphost = iphost if iphost else self._iphost
            port = port if port else self._port
            
            url = "http://{iphost}:{port}{uri}".format(iphost=self._iphost, port=self._port, uri=self._uri)
            response = urllib.urlopen(url) 
            status = response.getcode()
            htmls = response.readlines()

            logdict = {
                "url": url,
                "response": "".join(htmls),
                "orders": ["url", "response"],
            }
            
            if status not in [200]:
                    self._logger.dictlog(width=8, level="error", **logdict)
                    return None
            else:
                self._logger.dictlog(width=8, level="info", **logdict)
    
            content = dict()
            if len(htmls) < 4: return content
            active_conn = re.split(r":\s+", htmls[0].strip())[1]
            fds = re.split(r"[\s]+", htmls[2].strip())
            (accepts, handled, requests) = (fds[0], fds[1], fds[2])
            fds = re.split(r"[\s]+", htmls[3].strip())
            (reading, writing, waiting) = (fds[1], fds[3], fds[5])
            content = {
                "active_conn": int(active_conn),
                "accepts": int(accepts),
                "handled": int(handled),
                "requests": int(requests),
                "reading": int(reading),
                "writing": int(writing),
                "waiting": int(waiting),
            }
            
            return content
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            self._logger.error(tb)

    def get_value(self, key, uri, port=80, iphost="localhost"):
        force = self._force
        key = str(key).lower()
        if force == True:
            content = self.get(uri, port=port, iphost=iphost)
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
            content = self.get(uri, port=port, iphost=iphost)
            self._file_cache.save_to_cache_file(content)
            (value, code) = self._file_cache.get_val_from_json(key)
            return value
        return None
    
    def get_item_tval(self, key, uri, port=80, iphost="localhost"):
        val = self.get_value(key, uri, port=port, iphost=iphost)
        try:
            if re.match("(\d+)", val):
                return int(val)
            if re.match("(\d+\.\d+)", val):
                fval = "%.2f" % (val)
                return float(fval)
            return val
        except:
            return val

def main():
    script_name = sys.argv[0]
    usage = "usage: python {0} [options]".format(script_name)
    parser = OptionParser(usage)
    parser.add_option("-l", "--list",  action="store_true", dest="is_list_port", default=False,  help="if list all nginx port")
    parser.add_option("-i", "--iphost", action="store", dest="iphost", type="string", default='localhost', help="iphost")
    parser.add_option("-p", "--port", action="store", dest="port", type="string", default=80, help="port")
    parser.add_option("-u", "--uri", action="store", dest="uri", type="string", default='/ngx_status', help="uri")
    parser.add_option("-k", "--key", action="store", dest="key", type="string", default='active_conn', help="which key to fetch")
    parser.add_option("-d", "--debug",  action="store_true", dest="debug", default=False,  help="debug")
    parser.add_option("-f", "--force",  action="store_true", dest="force", default=False,  help="force")
    
    (options, args) = parser.parse_args()
    
    iphost = options.iphost
    port = options.port
    uri = options.uri
    key = options.key
    debug = options.debug
    force = options.force

    ngx = NginxPerf(uri, port=port, iphost=iphost, force=force, debug=debug)
    try:
        if options.is_list_port == True:
            print ngx.get_port_list()
            return
            
        if not key:
            parser.print_help()
            return
        
        value = ngx.get_item_tval(key, uri)
        if value != None:
            print value

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        ngx.get_logger().error(tb)


if __name__ == '__main__':
    main()
