## 项目说明
```
主要用来扩展zabbix的功能，增加对Tomcat/JVM/MYSQL/Redis/Memcache/Mongodb等的监控
```

## 目录结构说明
```
为方便使用，项目中所有中间的监控都移到了All In One目录，其目录下有readme.md说明文件，使用该目录下的配置文件、模板文件、脚本文件即可，具体按照说明文件操作即可；  
除了All In One目录外其余目录保留用作参考；  
```

## 变更历史
```
20170119：  
应朋友需求，增加tomcat监控，用于替换zabbix自带的tomcat监控。此监控实现应用了zabbix LLD功能，能自动发现tomcat实例并添加监控。  
zabbix自带的tomcat监控，存在如下不足：  
1）每台主机的监控item具有唯一性，如果一台主机有多个tomcat实例，则需要配置多个host；  
2）需要安装、配置zabbix_java_gateway；  
20170207：  
1）增加All In One目录，将涉及到的中间件监控统一起来，并提供一配置脚本，通过脚本进行统一的配置；  
2）BUG修复；  
3）代码优化；  
```

## 效果
![image](https://github.com/qiueer/zabbix/raw/master/All%20In%20One/effects/p1.png)   
   
![image](https://github.com/qiueer/zabbix/raw/master/All%20In%20One/effects/p2.png)   
  
![image](https://github.com/qiueer/zabbix/raw/master/All%20In%20One/effects/p3.png)   
  
![image](https://github.com/qiueer/zabbix/raw/master/All%20In%20One/effects/p4.png)   

