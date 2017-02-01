#-*- encoding:utf-8 -*-
'''
Created on 2016-06-18
@author: albertqiu
'''

'''
格式：\033[显示方式;前景色;背景色m
 
说明：
前景色            背景色           颜色
---------------------------------------
30                40              黑色
31                41              红色
32                42              绿色
33                43              黃色
34                44              蓝色
35                45              紫红色
36                46              青蓝色
37                47              白色
显示方式           意义
-------------------------
0                终端默认设置
1                高亮显示
4                使用下划线
5                闪烁
7                反白显示
8                不可见
 
例子：
\033[1;31;40m    <!--1-高亮显示 31-前景色红色  40-背景色黑色-->
\033[0m          <!--采用终端默认设置，即取消颜色设置-->
'''

class scolor(object):
    """
    显示风格
    """
    DST_DEFAULT = 0 #默认
    DST_HIGHLIGHT = 1 # 高亮
    DST_UNDERLINE = 4 #下划线
    DST_GLITTER = 5 # 闪烁
    DST_REVERSED = 7  # 反白
    DST_INVISIBLE = 8 #不可见
    
    """
    前景颜色
    """
    FRONT_BLACK = 30
    FRONT_RED = 31
    FRONT_GREEN = 32
    FRONT_YELLOW = 33
    FRONT_BLUE = 34
    FRONT_FUCHSIA = 35  # 紫红色
    FRONT_CYAN = 36 # 青蓝色
    FRONT_WHITE = 37 # 白色
    
    """
    背景颜色
    """
    BACK_BLACK = 40
    BACK_RED = 41
    BACK_GREEN = 42
    BACK_YELLOW = 44
    BACK_BLUE = 44
    BACK_FUCHSIA = 45  # 紫红色
    BACK_CYAN = 46 # 青蓝色
    BACK_WHITE = 47 # 白色

        
    @classmethod
    def _output(cls, msg, front_col, back_col, display_style, isback=False):
        fmt = "\033[%s;%s;%sm%s\033[0m" % (display_style, front_col, back_col, msg)
        if isback == True:
            return fmt
        print fmt
        
    @classmethod
    def custom(cls, msg, front_col, back_col, display_style, isback=False):
        return cls._output(msg, front_col, back_col, display_style, isback=isback)
        
    @classmethod
    def _tpl(cls, msg, front_color, isback=False):
        return cls._output(msg, front_color, cls.BACK_BLACK, cls.DST_HIGHLIGHT, isback=isback)
       
    @classmethod 
    def error(cls, msg, isback=False):
        return cls._tpl(msg, cls.FRONT_RED, isback=isback)
        
    @classmethod
    def info(cls, msg, isback=False):
        return cls._tpl(msg, cls.FRONT_GREEN, isback=isback)
        
    @classmethod
    def warn(cls, msg, isback=False):
        return cls._tpl(msg, cls.FRONT_FUCHSIA, isback=isback)
        
    @classmethod
    def emphasize(cls, msg, isback=False):
        return cls.error(msg, isback=isback)

if __name__ == "__main__":
        scolor().error("what")
        scolor().info("what")
        