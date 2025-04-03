#!/bin/sh
mkdir -p /download/$TT_USER
sed -i 's/\"sessionid_ss\": \".*\"\,$/\"sessionid_ss\": \"'"${SESSION_ID}"'\"\,/g' cookies.json
sed -i 's/\"\tt-target-idc": \".*\"\,$/\"\tt-target-idc": \"'"${TT_TARGET}"'\"\,/g' cookies.json
python main.py -user ${TT_USER} -output /download/${TT_USER} -mode automatic