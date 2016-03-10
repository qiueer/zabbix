#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
### 实现zabbix trapper协议
import socket 
import struct
import time

socket.setdefaulttimeout(20)

try:
    import simplejson as json
except:
    import json
    
class ZSender: 
    zbx_header = 'ZBXD' 
    zbx_version = 1 
    zbx_sender_data = {u'request': u'sender data', u'data': []}
    zbx_sender_items = []
    send_data = ''
    
    def __init__(self, server_host, server_port = 10051): 
        self.server_ip = server_host
        self.server_port = server_port

    def SetItems(self, items):
        self.zbx_sender_items = items
        
    def AddItem(self, key, value, clock = None, ip=True): 
        iphost = None
        if ip == True:
            import commands
            cmdstr = "/sbin/ifconfig |grep 'inet addr' | awk '{print $2}'|awk -F: '{print $2}' | head -n 1"
            (retcode, output) = commands.getstatusoutput(cmdstr)
            iphost = str(output).strip()
        else:
            iphost = socket.gethostname()

        item = {u'host': iphost, u'key': key, u'value': value} 
        if clock != None: item[u'clock'] = clock 
        if clock == None: item[u'clock'] = int(time.time())
        self.zbx_sender_items.append(item) 
        
    def _ClearData(self): 
        self.zbx_sender_items = []
        
    def __MakeSendData(self): 
        self.zbx_sender_data["data"] = self.zbx_sender_items
        zbx_sender_json = json.dumps(self.zbx_sender_data, separators=(',', ':'), ensure_ascii=False).encode('utf-8') 
        json_byte = len(zbx_sender_json) 
        self.send_data = struct.pack("<4sBq" + str(json_byte) + "s", self.zbx_header, self.zbx_version, json_byte, zbx_sender_json)
        
    def Send(self): 
        try:
            self.__MakeSendData()
            if len(self.zbx_sender_items) == 0:
                return {}
            so = socket.socket() 
            so.connect((self.server_ip, self.server_port)) 
            wobj = so.makefile(u'wb') 
            wobj.write(self.send_data) 
            wobj.close() 
            robj = so.makefile(u'rb') 
            recv_data = robj.read() 
            robj.close() 
            so.close() 
            tmp_data = struct.unpack("<4sBq" + str(len(recv_data) - struct.calcsize("<4sBq")) + "s", recv_data) 
            recv_result = json.loads(tmp_data[3]) 
            self._ClearData()
            info = recv_result["info"]
            ln_ary = str(info).split(";")
            res = {}
            for a in ln_ary:
                kp = str(a).split(":")
                key = str(kp[0]).strip()
                val = str(kp[1]).strip()
                if key in ["failed", "processed", "total"]:
                    res[key] = int(val)
                else:
                    res[key] = val
            return res
        except Exception as expt:
            import traceback
            tb = traceback.format_exc()
            return tb

if __name__ == '__main__': 
    clock = int(time.time())
    sender = ZSender(u'127.0.0.1', 10051) 
    sender.AddItem(u'test', 1, clock=clock) 
    res = sender.Send() 
    print sender.zbx_sender_data 
    print res
