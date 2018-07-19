#!/bin/bash

if [ "$1" != "" ]
then
    ERROR=$(egrep -A 10 'WARNING|ERROR' "$1")
    if [ -z "$ERROR" ]
    then
        echo -e "No error or warning"
    else
        echo -e "$ERROR"
    fi
else
    echo "Missing log file !"
fi
