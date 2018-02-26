# WorkshopManager
WorkshopManager is a CLI tool to install and maintain steam workshop items.

## Environment
- Python 3.6

## Getting Started
Pull the project and setup the required parameters.
These parameters are stored in ``params.pkl`` in your current working directory.
Because of this, it is easy to create different environments for different game servers.

```
pip install -r requirements.txt
python wm.py set login <username> <password>    # sets steam username and password
python wm.py set install_dir <directory>        # sets steam installation directory
python wm.py set appid <appid>                  # sets steam application id
```

Please note, that the steam password has to be stored in plaintext in ``params.pkl``.
You might want to adjust file permissions accordingly.

## Usage
WorkshopManager is used just like any linux package manager.
Installed mods are stored in ``mods.pkl`` in your current working directory.

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

## Examples
For downloading workshop items for Team Fortress 2, your initial setup might look like this
```
pip install -r requirements.txt
python wm.py set login anonymous ""    # steam anonymous login
python wm.py set install_dir .         # install mods in current directory
python wm.py set appid 440             # appid 440 = Team Fortress 2
```
As Team Fortress 2 is a free-to-play title, no ownership of the game is required
to download its workshop items.
Therefore, we use the anonymous login.

To install a mod we need the mod id.
This id may be found by browsing the steam workshop for our desired game,
or by searching for a specific mod via WorkshopManager.
```
python wm.py search Haywire
```
By either one of this methods we get the mod id.
```
python wm.py install 1308849071
```
Multiple mods may be installed simultaneously.
WorkshopManager will find required mods and suggest to install them in the confirmation dialog.
```
python wm.py install 1308849071 1308849072 1308849073
```
All mods installed in the current working directory are kept up-to-date by using the update command.
```
python wm.py update
```
