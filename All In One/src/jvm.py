# -*- encoding=utf-8 -*-
'''
JVM Stat
qjq@2017-01-19
'''

import sys
from optparse import OptionParser
import re
import platform

import os
import json
import getpass

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.utils import which

reload(sys) 
sys.setdefaultencoding('utf8')

def get_realpath():
    return os.path.split(os.path.realpath(__file__))[0]

def get_binname():
    return os.path.split(os.path.realpath(__file__))[1]

class JMX(object):
    def __init__(self, logpath, debug=False):
        self._logpath = logpath
        self._debug = debug
        self._java_path = which("java")
        self._cmdclient_jar = get_realpath() + "/" + "cmdline-jmxclient-0.10.3.jar"
        self._logger = slog(self._logpath, debug=debug, size=5, count=5)

    def _get_jmx_port_list(self):
        cmdstr = "ps -ef | grep 'jmxremote.port='| grep -v grep 2>/dev/null"
        plst = []
        
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
        for line in stdo_list:
            if not line or str(line).strip() == "": continue
            line = str(line).strip()
            ln_ary = re.split("[\s]+", line)
            runuser=ln_ary[0]
            pid = ln_ary[1]
            gc = ""
            jmxport = None
            pattern=r'\-XX\:\+Use(\w+)GC'
            for field in ln_ary:
                if "jmxremote.port=" in field:
                    jmxport = str(field).split("jmxremote.port=")[1]
                    
                m = re.match(pattern, field)
                if m:
                    gc = m.group(1)

            confitem = {
                "{#PID}": int(pid),
                "{#RUNUSER}": runuser,
                "{#GC}": gc or "Parallel",
            }
            
            if jmxport:
                confitem["{#JVMPORT}"] = int(jmxport)
            
            if confitem:
                data.append(confitem)
        return data

    def get_port_list(self, GC=None):
        data = self._get_jmx_port_list()
        ## all jmx port
        if GC == None:
            return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",", ":"))
        
        ## jmx port for GC
        gc_data = list()
        for item in data:
            if item["{#GC}"] == GC:
                gc_data.append(item)
        return json.dumps({'data': gc_data}, sort_keys=True, indent=7, separators=(",", ":"))
            
    def get_item(self, beanstr, key, port, iphost='localhost', auth='-'):
        """
        java -jar cmdline-jmxclient-0.10.3.jar - localhost:12345 java.lang:type=Memory NonHeapMemoryUsage
        参数：
        """
        pre_key = key
        sub_key = None
        if "." in key:
            pos = str(key).rfind(".")
            pre_key = key[0:pos]
            sub_key = key[pos + 1:]
        
        if self._java_path == None:
            print "can not find java command, exit."
            return None
        
        cmdstr = "%s -jar %s %s %s:%s '%s' '%s'" % (self._java_path, self._cmdclient_jar, auth, iphost, port, beanstr, pre_key)
        
        c2 = cmds(cmdstr, timeout=3)
        stdo = c2.stdo()
        stde = c2.stde()
        retcode = c2.code()
        
        (stdo_list, stde_list) = (re.split("\n", stdo), re.split("\n", stde))
        logdict = {
            "beanstr": beanstr,
            "key": key,
            "cmdstr": cmdstr,
            "stdo": stdo,
            "stde": stde,
            "retcode": retcode,
            "orders": ["beanstr", "lst_beanstr", "key", "cmdstr", "stdo", "stde", "retcode"],
        }
        if retcode !=0:
                self._logger.dictlog(width=8, level="error", **logdict)
                return
        else:
            self._logger.dictlog(width=8, level="info", **logdict)

        if stde_list:
            stdo_list.extend(stde_list)
            
        # # without sub attr
        if not sub_key and stdo_list:
            line = stdo_list[-1]
            ln_ary = re.split(" ", line)
            if ln_ary and len(ln_ary) >= 2:
                if pre_key in ln_ary[-2]:
                    return ln_ary[-1]
            
        # print stdo_list,"###"
        # # with sub attr
        for line in stdo_list:
            line = str(line).strip()
            ln_ary = re.split(":", line)
            if ln_ary and len(ln_ary) != 2:continue
            dst_key = str(ln_ary[0]).strip()
            dst_val = str(ln_ary[1]).strip()
            if sub_key == dst_key:
                return dst_val
        return None

def main():
    try:
        usage = "usage: %prog [options]\nGet Java App Info By JMX Protocal"
        parser = OptionParser(usage)
        
        parser.add_option("-l", "--list",
                          action="store_true", dest="is_list", default=False,
                          help="list all localhost jmx_port")
        
        parser.add_option("-g",
                          "--gc",
                          action="store",
                          dest="gc",
                          type="string",
                          default=None,
                          help="such as: G1/ConcMarkSweep/Parallel/Serial")
        
        parser.add_option("-b",
                          "--beanstr",
                          action="store",
                          dest="beanstr",
                          type="string",
                          default='java.lang:type=Memory',
                          help="such as: java.lang:type=Memory")
        
        parser.add_option("-k",
                          "--key",
                          action="store",
                          dest="key",
                          type="string",
                          default='NonHeapMemoryUsage.max',
                          help="such as: NonHeapMemoryUsage")
        
        parser.add_option("-i",
                          "--iphost",
                          action="store",
                          dest="iphost",
                          type="string",
                          default="localhost",
                          help="iphost")

        parser.add_option("-p",
                          "--port",
                          action="store",
                          dest="port",
                          type="int",
                          default=None,
                          help="jmx port")
        
        parser.add_option("-a",
                          "--auth",
                          action="store",
                          dest="auth",
                          type="string",
                          default='-',
                          help="auth info, username:passowrd")
        
        parser.add_option("-d", "--debug",
                          action="store_true", dest="debug", default=False,
                          help="if output all")

        (options, args) = parser.parse_args()
        if 1 >= len(sys.argv):
            parser.print_help()
            return
        
        logpath = "/tmp/zabbix_jvm_info_by_%s.log" % (getpass.getuser())
        zbx_ex_obj = JMX(logpath, debug=options.debug)
        if options.is_list == True:
            gc = options.gc
            if gc in ["","None","Null"]:gc = None
            print zbx_ex_obj.get_port_list(GC=gc)
            return

        iphost = options.iphost
        port = options.port
        beanstr = options.beanstr
        key = options.key
        auth = options.auth
        
        if beanstr and key and port:
            res = zbx_ex_obj.get_item(beanstr, key, port, iphost=iphost, auth=auth)
            # # if have value
            if res:
                print res
        else:
            parser.print_help()

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        print tb

if __name__ == '__main__':
    main()
