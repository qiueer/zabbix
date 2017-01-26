# -*- encoding=utf-8 -*-
'''
Tomcat Stat
qjq@2017-01-24
'''

import sys
from optparse import OptionParser
import re
import platform

import logging
from logging.handlers import RotatingFileHandler
import os
import xml.sax

reload(sys) 
sys.setdefaultencoding('utf8')

try:
    from shutil import which  # Python >= 3.3
except ImportError:
    import os, sys
    
    # This is copied from Python 3.4.1
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.
    
        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.
    
        """
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode)
                    and not os.path.isdir(fn))

        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None
    
        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)
    
        if sys.platform == "win32":
            if not os.curdir in path:
                path.insert(0, os.curdir)
    
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]
    
        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if not normdir in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None

def get_realpath():
    return os.path.split(os.path.realpath(__file__))[0]

def get_binname():
    return os.path.split(os.path.realpath(__file__))[1]



def docmd(command,timeout=300, raw=False):
        '''
        '''
        import subprocess, datetime, os, time, signal
        start = datetime.datetime.now()

        ps = None
        retcode = 0
        if platform.system() == "Linux":
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        while ps.poll() is None:
                time.sleep(0.2)
                now = datetime.datetime.now()
                if (now - start).seconds > timeout:
                        os.kill(ps.pid, signal.SIGINT)
                        retcode = -1
                        return (None,None,retcode)
        stdo = ps.stdout.readlines()
        stde = ps.stderr.readlines()
        
        if not ps.returncode:
                retcode = ps.returncode
        
        if raw == True:  #去除行末换行符
                stdo = [line.strip("\n") for line in stdo]
                stde = [line.strip("\n") for line in stde]
        
        if raw == False: #去除行末换行符，制表符、空格等
                stdo = [str.strip(line) for line in stdo]
                stde = [str.strip(line) for line in stde]

        return (stdo,stde,retcode)

def get_logstr(list_dict, max_key_len=16, join_str="\n"):
    log_str = ""
    for conf in list_dict:
        for (key,val) in dict(conf).iteritems():
            log_str = log_str + str(key).ljust(max_key_len) + ": " + str(val) + join_str
    log_str = log_str.strip() # 去掉尾部 \n
    return log_str

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

class ColoredFormatter(logging.Formatter):
    '''A colorful formatter.'''
 
    def __init__(self, fmt = None, datefmt = None):
        logging.Formatter.__init__(self, fmt, datefmt)
        # Color escape string
        COLOR_RED='\033[1;31m'
        COLOR_GREEN='\033[1;32m'
        COLOR_YELLOW='\033[1;33m'
        COLOR_BLUE='\033[1;34m'
        COLOR_PURPLE='\033[1;35m'
        COLOR_CYAN='\033[1;36m'
        COLOR_GRAY='\033[1;37m'
        COLOR_WHITE='\033[1;38m'
        COLOR_RESET='\033[1;0m'
         
        # Define log color
        self.LOG_COLORS = {
            'DEBUG': '%s',
            'INFO': COLOR_GREEN + '%s' + COLOR_RESET,
            'WARNING': COLOR_YELLOW + '%s' + COLOR_RESET,
            'ERROR': COLOR_RED + '%s' + COLOR_RESET,
            'CRITICAL': COLOR_RED + '%s' + COLOR_RESET,
            'EXCEPTION': COLOR_RED + '%s' + COLOR_RESET,
        }

    def format(self, record):
        level_name = record.levelname
        msg = logging.Formatter.format(self, record)
        return self.LOG_COLORS.get(level_name, '%s') % msg

class Log(object):
    '''
    log
    '''
    def __init__(self, filename, level="debug", logid="qiueer", mbs=20, count=10,is_console=False):
        '''
        mbs: how many MB
        count: the count of remain
        '''
        try:
            self._level = level
            self._filename = filename
            self._logid = logid
            self._logger = logging.getLogger(self._logid)

            if not len(self._logger.handlers):
                self._logger.setLevel(self.get_map_level(self._level))  
                
                fmt = '[%(asctime)s] %(levelname)s\n%(message)s'
                datefmt = '%Y-%m-%d %H:%M:%S'
                formatter = logging.Formatter(fmt, datefmt)
                
                maxBytes = int(mbs) * 1024 * 1024
                file_handler = RotatingFileHandler(self._filename, mode='a',maxBytes=maxBytes,backupCount=count)
                self._logger.setLevel(self.get_map_level(self._level))  
                file_handler.setFormatter(formatter)  
                self._logger.addHandler(file_handler)
                
                if is_console == True:
                    stream_handler = logging.StreamHandler(sys.stderr)
                    console_formatter = ColoredFormatter(fmt, datefmt)
                    stream_handler.setFormatter(console_formatter)
                    self._logger.addHandler(stream_handler)

        except Exception as expt:
            print expt
            
    def tolog(self, msg, level=None):
        try:
            level = level if level else self._level
            level = str(level).lower()
            level = self.get_map_level(level)
            if level == logging.DEBUG:
                self._logger.debug(msg)
            if level == logging.INFO:
                self._logger.info(msg)
            if level == logging.WARN:
                self._logger.warn(msg)
            if level == logging.ERROR:
                self._logger.error(msg)
            if level == logging.CRITICAL:
                self._logger.critical(msg)
        except Exception as expt:
            print expt
            
    def debug(self,msg):
        self.tolog(msg, level="debug")
        
    def info(self,msg):
        self.tolog(msg, level="info")
        
    def warn(self,msg):
        self.tolog(msg, level="warn")
        
    def error(self,msg):
        self.tolog(msg, level="error")
        
    def critical(self,msg):
        self.tolog(msg, level="critical")
            
    def get_map_level(self,level="debug"):
        level = str(level).lower()
        #print "get_map_level:",level
        if level == "debug":
            return logging.DEBUG
        if level == "info":
            return logging.INFO
        if level == "warn":
            return logging.WARN
        if level == "error":
            return logging.ERROR
        if level == "critical":
            return logging.CRITICAL
        

class JTomcat(object):
    def __init__(self, logpath, debug=False):
        self._logpath = logpath
        self._debug = debug
        self._java_path = which("java")
        self._cmdclient_jar = get_realpath()+"/" +"cmdline-jmxclient-0.10.3.jar"
        self._logger = Log(logpath,is_console=self._debug)

    def get_port_list(self):
        cmdstr = "ps -ef | grep tomcat | grep 'jmxremote.port='| grep -v grep 2>/dev/null"
        plst = []
        (stdo_list, stde_list, retcode) = docmd(cmdstr, timeout=3, raw = False)
        
        log_da = [{"cmdstr": cmdstr},{"ret": retcode},{"stdo": "".join(stdo_list)}, {"stde": "".join(stde_list)}]
        logstr = get_logstr(log_da, max_key_len=10)
        
        if retcode !=0:
                self._logger.error(logstr)
                return plst
        else:
            self._logger.info(logstr)
            
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
        (stdo_list, stde_list, retcode) = docmd(cmdstr, timeout=3, raw = False)
        
        #log_da = [{"cmdstr": cmdstr},{"ret": retcode},{"stdo": "".join(stdo_list)}, {"stde": "".join(stde_list)}]
        log_da = [
                {"beanstr": beanstr},{"lst_beanstr": lst_beanstr},{"key": key}, 
                {"cmdstr": cmdstr}, {"ret": retcode}, {"stdo": "".join(stdo_list)}, {"stde": "".join(stde_list)}
        ]
        logstr = get_logstr(log_da, max_key_len=10)
        
        if retcode !=0:
            self._logger.error(logstr)
            return None
        else:
            self._logger.info(logstr)

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
