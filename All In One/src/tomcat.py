# -*- encoding=utf-8 -*-
'''
Tomcat Stat
qjq@2017-01-24
'''

import sys
from optparse import OptionParser
import re
import platform

import os
import xml.sax

from qiueer.python.slog import slog
from qiueer.python.cmds import cmds
from qiueer.python.utils import which

reload(sys) 
sys.setdefaultencoding('utf8')

def get_realpath():
    return os.path.split(os.path.realpath(__file__))[0]

def get_binname():
    return os.path.split(os.path.realpath(__file__))[1]

class TCSerHandler(xml.sax.ContentHandler):
    def __init__(self):
        self._connectors = list()
    
    def startElement(self, tag, attributes):
        if tag == "Connector":
            protocal = attributes["protocol"]
            confitem = dict(attributes)
            self._connectors.append(confitem)
            
    def get_connectors(self):
        return self._connectors
    
    def get_biz_port(self):
        cons = self.get_connectors()
        for item in cons:
            protocol = item.get("protocol", None)
            if protocol == "HTTP/1.1":
                biz_port = item.get("port", None)
                return int(biz_port)
        return None

class JTomcat(object):
    def __init__(self, logpath, debug=False):
        self._logpath = logpath
        self._debug = debug
        self._java_path = which("java")
        self._cmdclient_jar = get_realpath()+"/" +"cmdline-jmxclient-0.10.3.jar"
        self._logger = slog(self._logpath, debug=debug, size=5, count=2)

    def get_port_list(self):
        cmdstr = "ps -ef | grep tomcat | grep 'jmxremote.port='| grep -v grep 2>/dev/null"
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
            pid = ln_ary[1]
            runuser = ln_ary[0]
            (jmxport, catalina_home, tc_dirname, buz_port) = (None, None, None, None)
            for field in ln_ary:
                if "jmxremote.port=" in field:
                    jmxport = str(field).split("jmxremote.port=")[1]
                if "catalina.home=" in field:
                    catalina_home = str(field).split("catalina.home=")[1]
                    tc_dirname =  str(catalina_home).split("/")[-1]
                
            confitem = {
                "{#RUNUSER}": runuser,
                "{#PID}": int(pid),
            }
            
            if jmxport:
                confitem["{#JVMPORT}"] = int(jmxport)
                
            if catalina_home:
                confitem["{#CTLN_HOME}"] = catalina_home
                server_xml = "%s/conf/server.xml" % (catalina_home)
                if os.path.exists(server_xml):
                   parser = xml.sax.make_parser()
                   parser.setFeature(xml.sax.handler.feature_namespaces, 0)
                   handler = TCSerHandler()
                   parser.setContentHandler( handler )
                   parser.parse(server_xml)
                   biz_port = handler.get_biz_port()
                   if biz_port:
                       confitem["{#BIZPORT}"] = biz_port
                
            if tc_dirname:
                confitem["{#DIRNAME}"] = tc_dirname
            
            if confitem:
                data.append(confitem)
        import json
        return json.dumps({'data': data}, sort_keys=True, indent=7, separators=(",",":"))
            
    def _parse_beanstr(self, beanstr):
        ptstr = r'name=http-(nio|bio|apr)-(\d+)'
        if not re.search(ptstr, beanstr):
            return beanstr
        if "," not in beanstr: return beanstr
        lst_beanstr = ""
        for kvstr in str(beanstr).split(","):
            kv = str(kvstr).split("=")
            if len(kv) == 2:
                k = kv[0]
                v = kv[1]
                if "name" == str(k).strip():
                    lst_beanstr = '%s,%s="%s"' % (lst_beanstr,k,v)
                else:
                    lst_beanstr = '%s,%s=%s' % (lst_beanstr,k,v)
            else:
                lst_beanstr = '%s,%s' % (lst_beanstr, kvstr)
        return lst_beanstr.strip(",")
    
    def get_item(self,  beanstr, key, port):
        """
        java -jar cmdline-jmxclient-0.10.3.jar - localhost:12345 java.lang:type=Memory NonHeapMemoryUsage
        参数：
        """
        pre_key = key
        sub_key = None
        if "." in key:
            pos = str(key).rfind(".")
            pre_key = key[0:pos]
            sub_key = key[pos+1:]
            
        lst_beanstr = self._parse_beanstr(beanstr)
        cmdstr = "%s -jar %s - localhost:%s '%s' '%s'" % (self._java_path, self._cmdclient_jar, port, lst_beanstr, pre_key)

        c2 = cmds(cmdstr, timeout=3)
        stdo = c2.stdo()
        stde = c2.stde()
        retcode = c2.code()
        
        (stdo_list, stde_list) = (re.split("\n", stdo), re.split("\n", stde))
        logdict = {
            "beanstr": beanstr,
            "lst_beanstr": lst_beanstr,
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
            
        ## without sub attr
        if not sub_key and stdo_list:
            line = stdo_list[-1]
            ln_ary = re.split(" ", line)
            if ln_ary and len(ln_ary) >= 2:
                if pre_key in ln_ary[-2]:
                    return ln_ary[-1]
            
        #print stdo_list,"###"
        ## with sub attr
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
        usage = "usage: %prog [options]\nGet Tomcat Stat"
        parser = OptionParser(usage)
        
        parser.add_option("-l", "--list",  
                          action="store_true", dest="is_list", default=False,  
                          help="if list all port")
        
        parser.add_option("-b", 
                          "--beanstr", 
                          action="store", 
                          dest="beanstr", 
                          type="string", 
                          default='Catalina:type=ThreadPool,name="http-nio-8080"',
                          help="such as:Catalina:type=ThreadPool,name=\"http-nio-8080\"")
        
        parser.add_option("-k", 
                          "--key", 
                          action="store", 
                          dest="key", 
                          type="string", 
                          default='currentThreadCount', 
                          help="such as:currentThreadCount")

        parser.add_option("-p", 
                          "--port", 
                          action="store", 
                          dest="port", 
                          type="int", 
                          default=None, 
                          help="the port for tomcat")
        
        parser.add_option("-d", "--debug",  
                          action="store_true", dest="debug", default=False,  
                          help="if output all")

        (options, args) = parser.parse_args()
        if 1 >= len(sys.argv):
            parser.print_help()
            return
        
        logpath = "/tmp/zabbix_tomcat_info.log"

        zbx_ex_obj = JTomcat(logpath, debug=options.debug)
        if options.is_list == True:
            print zbx_ex_obj.get_port_list()
            return

        beanstr = options.beanstr
        key = options.key
        port = options.port
        
        if beanstr and key and port:
            res = zbx_ex_obj.get_item(beanstr, key, port)
            ## if have value
            if res:
                print res

    except Exception as expt:
        import traceback
        tb = traceback.format_exc()
        print tb

if __name__ == '__main__':
    main()
