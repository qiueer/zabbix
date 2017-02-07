#-*- encoding:utf-8 -*-

import platform
import datetime
import os
import time
import signal

from subprocess import PIPE, Popen

class cmds(object):
    
    def __init__(self, *args, **kwargs):
        self.ps = None
        self.stdout = None
        self.stderr = None
        self.retcode = 0
        self.cmds(*args, **kwargs)
        
    def cmds(self, command, env=None, stdout=PIPE, stderr=PIPE, timeout=None):
            
            if platform.system() == "Linux":
                    self.ps = Popen(command, stdout=stdout, stdin=PIPE, stderr=stderr, shell=True)
            else:
                    self.ps = Popen(command, stdout=stdout, stdin=PIPE, stderr=stdout, shell=False)
            
            if timeout:
                start = datetime.datetime.now()
                while self.ps.poll() is None:
                        time.sleep(0.2)
                        now = datetime.datetime.now()
                        if (now - start).seconds > timeout:
                                os.kill(self.ps.pid, signal.SIGINT)
                                self.retcode = -1
                                self.stdout = None
                                self.stderr = None
                                return self

            kwargs = {'input': self.stdout}
            (self.stdout, self.stderr) = self.ps.communicate(**kwargs)
            self.retcode = self.ps.returncode
            return self
        
    def __repr__(self):
        return self.stdo()

    def __unicode__(self):
        return self.stdo()
    
    def __str__(self):
        try:
            import simplejson as json
        except:
            import json
        res = {"stdout":self.stdout, "stderr": self.stderr, "retcode": self.retcode}
        return  json.dumps(res, separators=(',', ':'), ensure_ascii=False).encode('utf-8') 
    
    def stdo(self):
        if self.stdout:
            return self.stdout.strip().decode('UTF-8')
        return ''
    
    def stde(self):
        if self.stderr:
            return self.stderr.strip().decode('UTF-8')
        return ''
    
    def code(self):
        return self.retcode