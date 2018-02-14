#!/bin/bash
cmd=("python3 wm.py -h"
     "python3 wm.py search"
     "python3 wm.py set appid 440"
     "python3 wm.py set install_dir test"
     "python3 wm.py set login anonymous \"\""
     "python3 wm.py search altitude"
     "python3 wm.py info 1293845868"
     "python3 wm.py install 1293845868"
     "python3 wm.py list"
)
rm -rf params.pkl
rm -rf mods.pkl

for c in "${cmd[@]}"
do
	read -p "$c"
	${c}
	echo ""
done
