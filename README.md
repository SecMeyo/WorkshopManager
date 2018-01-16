# WorkshopManager
WorkshopManager is a CLI tool to install and maintain steam workshop items.
## Environment
- Python 3.6
## Setup
```
pip install -r requirements.txt
```
## Usage
```
usage: wm.py [-h] [-y] [-v | -q]
             {search,install,remove,update,info,list,set} ...

Command line interface for installing steam workshop mods and keeping them up-
to-date - https://github.com/astavinu/WorkshopManager

positional arguments:
  {search,install,remove,update,info,list,set}
    search              searches the steam workshop
    install             installs list of steam workshop items
    remove              removes list of steam workshop items
    update              updates either all installed or specified list of
                        workshop items
    info                provides detailed information about one specific mod
    list                lists all installed mods
    set                 sets workshop manager environment variables

optional arguments:
  -h, --help            show this help message and exit
  -y, --yes             agree to all confirmations
  -v, --verbosity       increase output verbosity
  -q, --quiet
 ```