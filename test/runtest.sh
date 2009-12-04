#!/bin/bash

checkret() {
    if [ $? != 0 ]; then
        echo "[ERROR] $1"
        exit 1
    fi
}

WORKDIR=`pwd`
SLAPD="/usr/sbin/slapd"
DBDIR="$WORKDIR/test/openldap/db"
SCHEMADIR="$WORKDIR/test/openldap/schema"
SLAPDCONF="$WORKDIR/test/openldap/db/slapd.conf"

rm -fr "$DBDIR"/*
cp "$WORKDIR"/test/openldap/DB_CONFIG "$DBDIR"/

SCHEMADIRSED=`echo $SCHEMADIR | awk {'gsub("/", "\\\/", $1); print'}`
DBDIRSED=`echo $DBDIR | awk {'gsub("/", "\\\/", $1); print'}`
cat "$WORKDIR"/test/openldap/slapd.conf | sed s/"SCHEMADIR"/"$SCHEMADIRSED"/g | sed s/"DBDIR"/"$DBDIRSED"/g > "$SLAPDCONF"
checkret "Can't create new slapd.conf"

slapadd -f "$SLAPDCONF" -l "$WORKDIR"/test/openldap/base.ldif
checkret "Can't import base.ldif into openldap server"

slaptest -f "$SLAPDCONF"
checkret "Broken slapd.conf, exiting"

$SLAPD -f "$SLAPDCONF" -h ldap://localhost:1389
SLAPD_PID=`ps aux | grep slapd | grep "$SLAPDCONF" | grep -v grep | awk '{print $2}'`

echo "Openldap server ready"
echo "====================="

rm -f .coverage
nosetests \
-s \
--with-coverage \
--cover-package=pumpkin \
--with-doctest \
./test/test.py

if [ "$SLAPD_PID" != "" ]; then
    kill -s 9 $SLAPD_PID
else
    if [ "$(pidof slapd)" != "" ]; then
        echo "slapd still running, kill it manualy"
    fi
fi
rm -fr "$DBDIR"/*