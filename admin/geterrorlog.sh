#!/bin/bash

if [ "$1" != "" ]
then
    ERROR=$(egrep 'WARNING|ERROR' "$1" |sort -rnk1,2 | head -10)
    if [ -z "$ERROR" ]
    then
        echo -e "No error or warning"
    else
        echo -e "$ERROR"
    fi
else
    echo "Missing log file !"
fi
