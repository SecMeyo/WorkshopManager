from argparse import ArgumentParser as ArgParser
import pickle as pkl
import urllib.parse   # https://docs.python.org/3/library/urllib.request.html#module-urllib.request
import urllib.request
import urllib.error
import re
import subprocess
import pathlib
import glob
import os


class Mod:
    def __init__(self, id):
        """Holds all information about one specific mod.

        This class is used to provide functionality and information via CLI

        :param id: Workshop ID
        """
        self.id = id
        self.name = ""
        self.logo_url = ""
        self.require = []
        self.size = 0
        self.update()

        self.dependencies = self.update_dependencies()

    def __str__(self) -> str:
        result = "{: >12}: {}\n".format("id", self.id)
        result += "{: >12}: {}\n".format("name", self.name)
        result += "{: >12}: {}\n".format("logo_url", self.logo_url)
        result += "{: >12}: {}\n".format("size", self.str_get_size())
        result += "{: >12}: [\n".format("require", "")
        for mod in self.require:
            result += "{:14} {:10} {},\n".format("", mod.id, mod.name)
        result += "{:12}  ]".format("")
        return result

    def __eq__(self, other):
        return type(other) == Mod and self.id == other.id

    def update(self):
        """Refreshes all information by reading the workshop page again

        :return: None
        """
        new = SteamWorkshop.details(self.id)
        if "message" in new.keys():
            print("Mod", self.id, "was not found!")
            return

        self.name = new["name"]
        self.logo_url = new["logo_url"]
        self.require.clear()
        for m in new["require"]:
            self.require += [m]
        self.set_size(new["size"])

    def set_size(self, string):
        """Reads workshop item size from human readable string and sets fields accordingly

        :param string: file size
        :return: None
        """
        suffix = ["", "kb", "mb", "gb", "tb"]
        string = string.split(" ")
        assert len(string) == 2

        bytes = pow(1024, suffix.index(string[1].lower()))
        bytes *= float(string[0].replace(",", ""))

        self.size = bytes

    def str_get_size(self):
        """Builds human readable file size from bytes

        :return: human readable file size
        """
        mb = self.size/pow(1024, 2)
        return "{:.2f} MB".format(mb)

    def str_one_line(self) -> str:
        """Short description about a mod without line break

        :return: info string
        """
        return '{:10} {: >14}   {}'.format(self.id, self.str_get_size(), self.name)

    def get_dependencies(self):
        if not hasattr(self, 'dependencies'):
            self.dependencies = self.update_dependencies()
        return self.dependencies

    def update_dependencies(self):
        return SteamWorkshop.get_dependencies(self.id)


class PklDB:

    def __init__(self, file_name):
        """Reads dictionaries from <file_name> with Pickle

        This class can be used as a persistent dictionary.
        It wraps Pickle around one single dictionary.

        :param file_name: name of Pickle file
        :return: None
        """
        self.__data = {}
        self.file = self.__get_file(file_name)
        self.__load()

    def values(self):
        return self.__data.values()

    def keys(self):
        return self.__data.keys()

    def get(self, *args, **kwargs):
        return self.__data.get(*args, **kwargs)

    def update(self, *args, **kwargs):
        result = self.__data.update(*args, **kwargs)
        self.__save()
        return result

    def pop(self, *args, **kwargs):
        result = self.__data.pop(*args, **kwargs)
        self.__save()
        return result

    def __save(self):
        with open(self.file, 'wb') as f:
            pkl.dump(self.__data, f)

    def __load(self):
        try:
            with open(self.file, 'rb') as f:
                self.__data = pkl.load(f)

            # backwards compatibility to list db
            if type(self.__data) == list:
                new_data = {}
                for m in self.__data:
                    new_data.update({m.id: m})
                self.__data = new_data
        except FileNotFoundError:
            return

    def __get_file(self, file_name):
        file = pathlib.Path(file_name)
        file = file.with_suffix(".pkl")
        return file


class Params(PklDB):
    def __init__(self):
        PklDB.__init__(self, "params")


class Mods(PklDB):
    def __init__(self):
        PklDB.__init__(self, "mods")

    def install(self, mod_id):
        """Takes a string or Mod and adds it to the dictionary

        This is an additional interface for update

        :param mod_id: Workshop ID or instance of Mod
        :return: None
        """
        mod = None
        if type(mod_id) == str:
            mod = Mod(mod_id)
        elif type(mod_id) == Mod:
            mod = mod_id

        if mod is not None:
            PklDB.update(self, {mod.id: mod})


class SteamWorkshop:
    @classmethod
    def get_dependencies(cls, modId, parent_dependencies=[]):
        new = SteamWorkshop.details(modId)["require"]
        list = []
        for n in new:
            if n not in parent_dependencies and n not in list:
                list += [n]
                temp = SteamWorkshop.get_dependencies(modId, list+parent_dependencies)
                if temp is not []:
                    list += temp

        return list

    @classmethod
    def exists(cls, modId):
        """Checks whether or not a workshop item exists

        :param modId: Workshop ID
        :return: True/False
        """
        details = SteamWorkshop.details(modId)
        return "message" not in details.keys()

    @classmethod
    def download(cls, modId, appid):
        """Uses steamcmd to download workshop items

        :param modId: Workshop ID
        :return: None
        """
        install_dir = Params().get("install_dir")
        login = Params().get("login")

        mods = ['+workshop_download_item {} {} validate'.format(Params().get("appid"), m) for m in modId]
        try:
            cmd = ['steamcmd', '+login', login.get("username"), login.get("password"), '+force_install_dir', install_dir]
            for m in mods:
                cmd.append(m)
            cmd.append("+quit")
            subprocess.run(cmd)

        except FileNotFoundError:
            print("Please install steamcmd first: https://duckduckgo.com/?q=install+steamcmd&t=ffsb&ia=web")

    @classmethod
    def details(cls, modId):
        """Crawls the steam workshop for item information

        :param modId: Workshop ID
        :return: dictionary of mod information
        """
        details = {}

        link = "https://steamcommunity.com/sharedfiles/filedetails/"
        data = {"id": modId}

        data = urllib.parse.urlencode(data)
        link = link + "?" + data
        r = urllib.request.urlopen(link)

        html = r.read()

        details.update(SteamWorkshop.__parse_filedetails(html.decode("utf-8")))
        return details

    @classmethod
    def search(cls, search_text, appid, sort="mostrecent"):
        """Searches the Steam Workshop for search_text and returns a list of Workshop IDs

        :param search_text: Text to search for in steam workshop
        :param sort: Steam sorting method (default "mostrecent")
        :return: list of Workshop IDs
        """
        from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/

        html = SteamWorkshop.__get_search_html(search_text, appid, sort=sort)

        soup = BeautifulSoup(html, "html.parser")
        tags = soup.find_all(href=re.compile("(filedetails/\?id)"))

        workshop_ids = []
        for x in tags:
            link = x.get("href")
            workshop_id = SteamWorkshop.__find_ids(link)[0]
            if workshop_id not in workshop_ids:
                workshop_ids += [workshop_id]

        return workshop_ids

    @classmethod
    def __get_search_html(cls, search_text, appid, tags="", sort=""):
        """Retrieves results from steam workshop search

        :param search_text:
        :param tags: steam workshop tags (default "Mod")
        :param sort: steam workshop sorting method (default "")
        :return: html bytes array
        """
        parameters = {}
        parameters.update({"appid": appid})
        parameters.update({"searchtext": search_text})
        parameters.update({"childpublishedfileid": "0"})
        parameters.update({"browsesort": sort})
        parameters.update({"section": "readytouseitems"})
        if tags != "": parameters.update({"requiredtags[]": tags})
        url = "http://steamcommunity.com/workshop/browse/"

        data = urllib.parse.urlencode(parameters)
        url = url + "?" + data
        print(url)
        req = urllib.request.Request(url)
        html = None
        try:
            r = urllib.request.urlopen(req)
            html = r.read()
        except urllib.error.URLError as e:
            print(e.reason)
        return html.decode("utf-8")

    @classmethod
    def __find_ids(cls, s):
        """Searches for steam Workshop IDs in string

        :param s: any string
        :return: list of Workshop IDs
        """
        workshop_id = re.findall("\d{5,15}", s)
        return workshop_id

    @classmethod
    def __parse_filedetails(cls, html):
        """Parses information from html bytes array

        :param html: html bytes array
        :return: dictionary of workshop item information
        """
        from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/

        details = {}
        soup = BeautifulSoup(html, "html.parser")

        # Workshop error handling
        message = soup.find(id="message")
        if message is not None:
            details["message"] = str(message.string)
            return details

        link = soup.find(href=re.compile("(filedetails/\?id)")).get("href")
        details["id"] = SteamWorkshop.__find_ids(link)[0]

        html_details = soup.find(id="mainContents")
        details["name"] = html_details.find("div", "workshopItemTitle").string

        if html_details.find(id="previewImageMain") is not None:
            details["logo_url"] = html_details.find(id="previewImageMain").get("src")
        if html_details.find(id="previewImage") is not None:
            details["logo_url"] = html_details.find(id="previewImage").get("src")

        items = html_details.find(id="RequiredItems")
        items = str(items)
        details["require"] = SteamWorkshop.__find_ids(items)

        details["size"] = html_details.find("div", "detailsStatRight").string

        for i in details.keys():
            if i != "require":
                details[i] = str(details[i])

        return details


def parser_args():
    """Parses user input via CLI and provides help

    :return: argument object
    """
    description = (
        'Command line interface for installing steam workshop mods '
        'and keeping them up-to-date - \n'
        'https://github.com/astavinu/xxx')

    parser = ArgParser(description=description)

    subparsers = parser.add_subparsers(dest="command")
    subparser = subparsers.add_parser("search",
                                      help='searches the steam workshop')
    subparser.add_argument("search_term", nargs="*")
    subparser.add_argument('-s', "--sort", choices=["mostrecent", "trend", "totaluniquesubscribers", "textsearch"],
                           default="textsearch",
                           help='when using "search" the mods may be sorted')

    subparser = subparsers.add_parser("install",
                                      help='installs list of steam workshop items')
    subparser.add_argument("workshop_ids", nargs="*")

    subparser = subparsers.add_parser("remove",
                                      help='removes list of steam workshop items')
    subparser.add_argument("workshop_ids", nargs="*")

    subparser = subparsers.add_parser("update",
                                      help='updates either all installed or specified list of workshop items')
    subparser.add_argument("workshop_ids", nargs="*", default=["all"],
                           help='list of workshop_ids to be updated')
    subparser.add_argument("-i", "--individual", action="store_true", default=False,
                           help="update each mod individually in steamcmd")

    subparser = subparsers.add_parser("info",
                                      help='provides detailed information about one specific mod')
    subparser.add_argument("workshop_id")

    subparser = subparsers.add_parser("list",
                                      help='lists all installed mods')

    subparser = subparsers.add_parser("set",
                                      help='sets workshop manager environment variables')
    subs = subparser.add_subparsers(dest="var")
    s = subs.add_parser("login")
    s.add_argument("username")
    s.add_argument("password")
    s = subs.add_parser("install_dir")
    s.add_argument("directory")
    s = subs.add_parser("appid")
    s.add_argument("appid")

    parser.add_argument("-y", "--yes", action="store_true", default=False,
                        help='yes to all confirmations')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbosity", action="count", default=0,
                       help="increase output verbosity")
    group.add_argument("-q", "--quiet", action="store_true", default=False,
                       help="")
    parser.add_argument("-wv", "--write-version", action="store_true", default=False,
                        help='writes version to every single workshop item as an empty file <version>.ver')

    options = parser.parse_args()
    if isinstance(options, tuple):
        args = options[0]
    else:
        args = options

    return args


class CLI:

    @staticmethod
    def main(args, method_name=None):
        """Maps CLI input to direct function calls

        :param args: arguments to pass over
        :param method_name: method to call (default None)
        :return: result of invoked method
        """

        if method_name is None:
            if args.command is None:
                return 1
            method_name = args.command
        class_name = CLI

        try:
            method = getattr(class_name, method_name)
        except AttributeError:
            raise NotImplementedError(
                "Class `{}` does not implement `{}`".format(class_name.__class__.__name__, method_name))
        return method(args)

    @staticmethod
    def search(args):
        """Searches the steam workshop

        :param args: parsed CLI arguments
        :return: None
        """
        # fail early and gracefully
        CLI.fail_on_missing_params(["appid"])

        text = ""
        for s in args.search_term:
            text += s+" "
        appid = Params().get("appid")
        mods = SteamWorkshop.search(text, appid, args.sort)
        print("Found:")
        for m in mods:
            mod = Mod(m)
            print("", mod.str_one_line())
            if len(mod.get_dependencies()) > 1:
                names = ""
                size = 0
                for d in mod.get_dependencies():
                    d = Mod(d)
                    names += d.name+", "
                    size += d.size
                print(" Dependencies: {:8.2f} MB   {}".format(size/pow(1024, 2), names[:-2]))

    @staticmethod
    def set(args):
        """Sets environment variables

        Increases convenience of use by remembering parameters used at each program run
        e.g. install directory, login credentials for steam, ...

        :param args: parsed CLI arguments
        :return: None
        """
        if args.var == "login":
            Params().update({args.var: {"username": args.username, "password": args.password}})
        if args.var == "install_dir":
            Params().update({args.var: args.directory})
        if args.var == "appid":
            Params().update({args.var: args.appid})

    @staticmethod
    def info(args):
        """Prints information about a workshop item

        :param args: parsed CLI arguments
        :return: None
        """
        # fail early and gracefully
        CLI.fail_on_missing_params(["appid"])

        mod = Mod(args.workshop_id)
        print(mod)

    @staticmethod
    def list(args):
        """Lists installed workshop items

        :param args: parsed CLI arguments
        :return: None
        """
        mods = Mods().values()
        sizes = [m.size for m in mods]
        dependencies = []
        print("Installed:")
        for mod in mods:
            for m in mod.get_dependencies():
                m = Mod(m)
                if m not in dependencies and m not in mods:
                    sizes += [m.size]
                    dependencies += [m]
            print("", mod.str_one_line())

        print("Dependencies:")
        for m in dependencies:
            print("", m.str_one_line())

        print("\nSummary\n==============================")
        print("{: >10} {: >12d} Workshop mod{}".format("Installed", len(sizes), "s" if len(sizes) != 1 else ""))
        print("{: >10} {: >12.2f} MB".format("Size", sum(sizes) / pow(1024, 2)))
        print("")

    @staticmethod
    def install(args):
        """Installs a list of workshop items

        :param args: parsed CLI arguments
        :return: None
        """
        # fail early and gracefully
        CLI.fail_on_missing_params(["install_dir", "appid", "login"])

        # group mods
        install = []
        installed = []
        not_found = []
        for mod_id in args.workshop_ids:
            if SteamWorkshop.exists(mod_id):
                if mod_id not in Mods().keys():
                    if mod_id not in install:
                        install += [mod_id]
                else:
                    installed += [mod_id]
            else:
                not_found += [mod_id]

        sizes = []
        mods = [Mod(mod) for mod in install]
        mods_ids = [m.id for m in mods]
        dependencies = []
        if len(install) > 0:
            print("Installing:")
            for mod in mods:
                sizes += [mod.size]
                for m in mod.get_dependencies():
                    if m not in Mods().keys():
                        if m not in mods_ids:
                            if m not in dependencies:
                                dependencies += [m]
                                install += [m]
                print("", mod.str_one_line())
        if len(dependencies) > 0:
            print("Installing dependencies:")
            for m in dependencies:
                mod = Mod(m)
                sizes += [mod.size]
                print("", mod.str_one_line())

        print("\nSummary\n==============================")
        if len(installed) > 0:
            print("{: >10} {: >12d} Workshop mod{}".format("Existing", len(installed), "s" if len(installed) != 1 else ""))
        if len(not_found) > 0:
            print("{: >10} {: >12d} {}".format("Not Found", len(not_found), not_found))
        print("{: >10} {: >12d} Workshop mod{}".format("Install", len(sizes), "s" if len(sizes) != 1 else ""))
        print("{: >10} {: >12.2f} MB".format("Size", sum(sizes)/pow(1024,2)))
        print("")
        if not args.yes:
            if "n" == input("Is this ok [Y|n]:").lower():
                print("Installation aborted.")
                return 0

        for mod in mods:
            Mods().install(mod)

        SteamWorkshop.download(install, Params().get("appid"))

        if args.write_version:
            for mod_id in install:
                Appworkshop().write_version(mod_id)

    @staticmethod
    def remove(args):
        """Removes a list of workshop items

        :param args: parsed CLI arguments
        :return: None
        """
        for m in args.workshop_ids:
            if m not in Mods().keys():
                print(m, "not installed.")
            else:
                mod = Mods().get(m)
                Mods().pop(m)
                print(mod.name, "removed.")

    @staticmethod
    def update(args):
        """Updates a list of workshop items

        :param args: parsed CLI arguments
        :return: None
        """
        # fail early and gracefully
        CLI.fail_on_missing_params(["install_dir", "appid", "login"])

        install = []
        if args.workshop_ids[0] == "all":
            mods = Mods().keys()
        else:
            mods = []
            for mod_id in args.workshop_ids:
                m = Mods().get(mod_id)
                if type(m) is Mod:
                    mods += [m.id]
                    mods += [md for md in m.get_dependencies()]

        for mod in mods:
            if mod not in Mods().keys():
                print(mod, "not installed.")
            elif mod in install:
                print(mod, "skipped, already updated.")
            else:
                install += [mod]

        store = Appworkshop()
        if args.individual:
            for mod in install:
                SteamWorkshop.download([mod], Params().get("appid"))
                if args.write_version:
                    store.write_version(mod)
        else:
            SteamWorkshop.download(install, Params().get("appid"))
            for mod in install:
                if args.write_version:
                    store.write_version(mod)

    @staticmethod
    def fail_on_missing_params(params):
        message = {"install_dir": "Please set installation directory.",
                   "appid": "Please set steam app id.",
                   "login": "Please set steam login first."}
        error = ""
        for p in params:
            if p not in Params().keys():
                error += message[p]+"\n"
        if error != "":
            print(error)
            print("use: set --help")
            exit(0)


class Appworkshop:
    def __init__(self):
        self.content = {}
        self.reload()

    def reload(self):
        self.content = self._load(self._find())

    def export(self, modid):
        self.reload()
        items = self.content["AppWorkshop"]["WorkshopItemsInstalled"]
        result = {}
        if modid in items.keys():
            result = items[modid]
        return result

    def write_version(self, modid):
        mod = self.export(modid)
        folder = glob.glob(Params().get("install_dir")+"/**/"+Params().get("appid")+"/"+modid, recursive=True)
        self._delete_versions(folder[0])
        file = folder[0]+"/"+mod["timeupdated"]+".ver"
        with open(file, "w+") as f:
            f.write("")

    @staticmethod
    def _parse_acf(content):
        result = {}
        nested = ""
        collect_nested_dict = False
        nested_count = 0
        last = ""

        for line in content.splitlines():
            line = line.strip().replace("\"", "")
            if collect_nested_dict:
                nested += line + "\n"
                if "{" in line:
                    nested_count += 1
                if "}" in line:
                    nested_count -= 1
                if nested_count < 0:
                    result[last] = Appworkshop._parse_acf(nested)
                    nested = ""
                    nested_count = 0
                    collect_nested_dict = False
                continue
            if "{" in line:
                collect_nested_dict = True
                continue

            if "\t\t" in line:
                vars = line.split("\t\t")
                result[vars[0]] = vars[1]

            last = line
        return result

    @staticmethod
    def _find():
        root = Params().get("install_dir")
        appid = Params().get("appid")
        dir = root + "/**/appworkshop_" + appid + ".acf"
        files = glob.glob(dir, recursive=True)
        if len(files) != 1:
            print(files)
            exit(1)
        return files[0]

    @staticmethod
    def _load(file):
        with open(file) as f:
            content = Appworkshop._parse_acf(f.read())
        return content

    @staticmethod
    def _delete_versions(path):
        for f in glob.glob(path+"/*.ver"):
            os.remove(f)


if __name__ == "__main__":
    args = parser_args()
    try:
        exit(CLI.main(args))
        pass
    except KeyboardInterrupt:
        pass
