#-*- encoding:utf-8 -*-
'''
@author: qiueer
'''
import re, types
import platform


def docmd(command,timeout=300, debug=False, raw=False):
        '''
        功能：
                执行命令
        参数：command，命令以及其参数/选项
                timeout，命令超时时间，单位秒
                debug，是否debug，True输出debug信息，False不输出
                raw，命令输出是否为元素的输出，True是，False会将结果的每一行去除空格、换行符、制表符等，默认False
        返回：
                含有3个元素的元组，前两个元素类型是list，第三个元素类型是int，第一个list存储stdout的输出，第二个list存储stderr的输出，第三int存储命令执行的返回码，其中-1表示命令执行超时
        示例：
                cmd.docmd("ls -alt")
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

    
def docmd_ex(command,timeout=300, debug=False, raw=False, pure=True):
        '''
        功能：
                执行命令
        参数：command，命令以及其参数/选项
                timeout，命令超时时间，单位秒
                debug，是否debug，True输出debug信息，False不输出
                raw，命令输出是否为元素的输出，True是，False会将结果的每一行去除空格、换行符、制表符等，默认False
        返回：
                含有3个元素的元组，前两个元素类型是list，第三个元素类型是int，第一个list存储stdout的输出，第二个list存储stderr的输出，第三int存储命令执行的返回码，其中-1表示命令执行超时
        示例：
                cmd.docmd("ls -alt")
        '''
        import subprocess, datetime, os, time, signal
        start = datetime.datetime.now()
        (stdo,stde, retcode) = ([], [], -1)
        ps = None
        if platform.system() == "Linux":
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
                ps = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        while ps.poll() is None:
                time.sleep(0.2)
                now = datetime.datetime.now()
                if (now - start).seconds > timeout:
                        os.kill(ps.pid, signal.SIGINT)
                        return None,None,-1
                            
        if pure == True:
            stdo = ps.stdout.read()
            stde = ps.stderr.read()
        elif pure == False:
            stdo = ps.stdout.readlines()
            stde = ps.stderr.readlines()
            
        retcode = ps.returncode
        
        if raw == True and pure == False:  #去除行末换行符
                stdo = [line.strip("\n") for line in stdo]
                stde = [line.strip("\n") for line in stde]
        
        if raw == False and pure == False: #去除行末换行符，制表符、空格等
                stdo = [str.strip(line) for line in stdo]
                stde = [str.strip(line) for line in stde]
				
        return stdo,stde,retcode
 
def docmds(commands,timeout=300, debug=False, raw=False):
        '''
        功能：执行多个命令，每个命令之间用 , 或 ; 号分割
        返回：哈希，key为每个命令，key对应的value为一元组，元组值请参看docmd的说明  
        '''
        cmds = re.split('[,;]+' ,  commands)
        result = {}
        for cmdline in cmds:
                (stdo,stde,retcode) = docmd(cmdline, timeout, debug=debug, raw=raw)
                result[cmdline] = (stdo,stde,retcode)
        return result 
        

        
        
