#!/bin/sh

DEST_EXTEND_CONF_DIR=$1
DEST_SCRIPT_DIR=$2

CURDIR=$(cd $(dirname ${BASH_SOURCE[0]});pwd)
CURR_DT=$(date +"%Y%m%d%H%M%S")

if [ "x${DEST_EXTEND_CONF_DIR}" = "x" ] || [ "x${DEST_SCRIPT_DIR}" = "x" ];then
	echo "Usage: $0 \${extend_conf_dir} \${script_dir}"
	exit 1
fi

CONF_DIRNAME=confs
SCRIPT_DIRNAME=src
CONF_DIR="${CURDIR}/${CONF_DIRNAME}"
SCRIPT_DIR="${CURDIR}/${SCRIPT_DIRNAME}"

TMP_BACKUP_DIR=/tmp/zabbix_extend

mkdir -p ${TMP_BACKUP_DIR}

## backup
echo "[INFO] Backup To:"
echo "## ${TMP_BACKUP_DIR}"
if [ -d $DEST_EXTEND_CONF_DIR ];then
	tar czvfP ${TMP_BACKUP_DIR}/conf_${CURR_DT}.tar.gz $DEST_EXTEND_CONF_DIR
fi
if [ -d $DEST_SCRIPT_DIR ];then
	tar czvfP ${TMP_BACKUP_DIR}/script_${CURR_DT}.tar.gz $DEST_SCRIPT_DIR 
fi

## pre-set
mkdir -p ${DEST_EXTEND_CONF_DIR}
mkdir -p ${DEST_SCRIPT_DIR}

## swap
echo "[INFO] SWAP"
SWAP_DIR=/tmp/zabbix_extend_swap
mkdir -p ${SWAP_DIR}
rm -frv ${SWAP_DIR}/*
cp -Rv "${CONF_DIR}" ${SWAP_DIR}/
cp -Rv "${SCRIPT_DIR}" ${SWAP_DIR}/
FULL_DEST_SCRIPT_DIR=${DEST_SCRIPT_DIR}
sed -i "s#\$SCRIPPATH#${FULL_DEST_SCRIPT_DIR}#g" ${SWAP_DIR}/${CONF_DIRNAME}/*.conf

## update
echo "[INFO] Copy To:"
echo "## ${DEST_EXTEND_CONF_DIR}"
echo "## ${DEST_SCRIPT_DIR}"
cp -Rv ${SWAP_DIR}/${CONF_DIRNAME}/* ${DEST_EXTEND_CONF_DIR}/
cp -Rv ${SWAP_DIR}/${SCRIPT_DIRNAME}/* ${DEST_SCRIPT_DIR}/

## clean
echo "[INFO] Clean"
find ${TMP_BACKUP_DIR} -name "*.tar.gz" -mtime +14 -exec rm -rvf {} \;

## restart zabbix_agent
echo "[INFO] Restart Zabbix Agent"
/etc/init.d/zabbix-agent restart
