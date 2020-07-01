#!/bin/bash
remoteSrc='192.168.1.250'
remoteUsr='pi'
remoteDir='/dr_models/'
destDir='/home/pi/dr_models/'
loopDur=30

while :
do
  httpConns=$(netstat -at | grep -E '^(\S+\s+){3}\S+:http\s+\S+:\S+\s+ESTABLISHED$' | wc -l)
  if [ $httpConns -eq 0 ]
  then
    echo "$httpConns ESTABLISHED http connections found. Executing rsync..."
    rsync --delete --ignore-existing --include='*.tar.gz' --exclude='*' -rzPvv $remoteUsr@$remoteSrc:$remoteDir $destDir
    echo rsync complete. Sleeping for $loopDur seconds...
  else
    echo "$httpConns ESTABLISHED http connection were found. Sleeping for $loopDur seconds..."
  fi
  sleep $loopDur
done

