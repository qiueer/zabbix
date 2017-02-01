#encoding=UTF8
import os
import re
import types
import json
import time

class filecache(object):
    
    def __init__(self, cache_file):
        self._cache_file = cache_file
    
    def get_val_from_json(self, key, seconds=60):
        """
        cache文件的内容，第一行是时间戳，第二行是json数据内容
        """
        if os.path.exists(self._cache_file) == False:
            return None
        resobj = None
        fd = open(self._cache_file, "r")
        alllines = fd.readlines()
        fd.close()
        
        if not alllines or len(alllines)<1: return None
        old_unixtime = int(str(alllines[0]).strip())
        now_unixtime = int(time.time())
        ## 超过60s
        if (now_unixtime - old_unixtime) > seconds:
            return None
        resobj = str(alllines[1]).strip()
        resobj = json.loads(resobj)

        keys = re.split(r"\.", key)
        dict_or_val = resobj
        for k in keys:
            k = str(k).strip()
            if type(dict_or_val) != types.DictType: return dict_or_val
            dict_or_val = dict_or_val.get(k, None)
        return dict_or_val
    
    def get_val_from_lines(self, key, separator=":", seconds=60):
        """
        cache文件的内容，第一行是时间戳，其余行是具体的数据内容
        """
        if os.path.exists(self._cache_file) == False:
            return None

        fd = open(self._cache_file, "r")
        alllines = fd.readlines()
        fd.close()
        
        if not alllines or len(alllines)<1: return None
        old_unixtime = int(str(alllines[0]).strip())
        now_unixtime = int(time.time())
        ## 超过60s
        if (now_unixtime - old_unixtime) > seconds:  return None
        lines = alllines[1:]
        for line in lines:
            line = str(line).replace(" ", "").strip()
            ln_ary = re.split(separator, line)
            if len(ln_ary) < 2: continue
            if ln_ary[0] == key:
                return ln_ary[1]
        return None

    def save_to_cache_file(self, content):
        ## 如果是dict，则先转换为json字符串再写入
        if type(content) == types.DictType:
            content = json.dumps(content)
        now_unixtime = int(time.time())
        with open(self._cache_file, "w") as fd:
            fd.write(str(now_unixtime)+"\n")
            fd.write(content)
            fd.close()
