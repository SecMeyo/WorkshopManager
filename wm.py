from argparse import ArgumentParser as ArgParser
import pickle as pkl
import urllib.parse   # https://docs.python.org/3/library/urllib.request.html#module-urllib.request
import urllib.request
import urllib.error
import re
import subprocess


class Mod:
    def __init__(self, id):
        self.id = id
        self.name = ""
        self.logo_url = ""
        self.require = []
        self.size = 0
        self.update()

    def str_one_line(self) -> str:
        return '{:10} {: >14}   {}'.format(self.id, self.str_get_size(), self.name)

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
        new = SteamWorkshop.details(self.id)
        if "message" in new.keys():
            print("Mod", self.id, "was not found!")
            return

        self.name = new["name"]
        self.logo_url = new["logo_url"]
        for m in new["require"]:
            self.require += [Mod(m)]
        self.set_size(new["size"])

    def set_size(self, string):
        suffix = ["", "kb", "mb", "gb", "tb"]
        string = string.split(" ")
        assert len(string) == 2

        bytes = pow(1024, suffix.index(string[1].lower()))
        bytes *= float(string[0].replace(",", ""))

        self.size = bytes

    def str_get_size(self):
        mb = self.size/pow(1024, 2)
        return "{:.2f} MB".format(mb)


class Params:
    FILE_NAME = "params.pkl"

    def __init__(self):
        self.params = {}
        self._load()

    def set(self, param, value):
        self.params[param] = value
        self._save()

    def get(self, param):
        return self.params[param]

    def isset(self, param):
        return param in self.params.keys()

    def _save(self):
        with open(self.FILE_NAME, 'wb') as f:
            pkl.dump(self.params, f)

    def _load(self):
        try:
            with open(self.FILE_NAME, 'rb') as f:
                self.params = pkl.load(f)
        except FileNotFoundError:
            return


class DB:
    FILE_NAME = "mods.pkl"

    def __init__(self):
        self.mods = []
        self.load()

    def save(self):
        with open(self.FILE_NAME, 'wb') as f:
            pkl.dump(self.mods, f)

    def load(self):
        try:
            with open(self.FILE_NAME, 'rb') as f:
                self.mods = pkl.load(f)
        except FileNotFoundError:
            return

    def install(self, modId):
        mod = None
        if type(modId) == str:
            mod = Mod(modId)
        elif type(modId) == Mod:
            mod = modId

        if mod is not None:
            if mod not in self.mods:
                self.mods += [mod]
                self.save()

    def remove(self, modId):
        for m in self.mods:
            if modId == m.id:
                self.mods.remove(m)
                self.save()

    def exists(self, modId):
        for m in self.mods:
            if modId == m.id:
                return True
        return False

    def get(self, modId):
        for m in self.mods:
            if modId == m.id:
                return m
        return None


class SteamWorkshop:
    @classmethod
    def exists(cls, modId):
        details = SteamWorkshop.details(modId)
        return "message" not in details.keys()

    @classmethod
    def download(cls, modId):
        install_dir = Params().get("install_dir")
        login = Params().get("login")
        mods = ['+workshop_download_item 107410 {} validate'.format(m) for m in modId]
        try:
            cmd = ['steamcmd', '+login', login[0], login[1], '+force_install_dir', install_dir]
            for m in mods:
                cmd.append(m)
            cmd.append("+quit")
            subprocess.run(cmd)

        except FileNotFoundError:
            print("Please install steamcmd first: https://duckduckgo.com/?q=install+steamcmd&t=ffsb&ia=web")

    @classmethod
    def details(cls, modId):
        details = {}

        link = "https://steamcommunity.com/sharedfiles/filedetails/"
        data = {"id": modId}

        data = urllib.parse.urlencode(data)
        link = link + "?" + data
        r = urllib.request.urlopen(link)

        html = r.read()

        details.update(SteamWorkshop._parse_filedetails(html.decode("utf-8")))
        return details

    @classmethod
    def search(cls, search_text, sort):
        """
        Searches the Steam Workshop for search_text and returns a list of Workshop IDs
        :param search_text:
        :param sort:
        :return:
        """
        from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/

        html = SteamWorkshop._get_search_html(search_text, sort=sort)

        soup = BeautifulSoup(html, "html.parser")
        tags = soup.find_all(href=re.compile("(filedetails/\?id)"))

        workshop_ids = []
        for x in tags:
            link = x.get("href")
            workshop_id = SteamWorkshop._find_ids(link)[0]
            if workshop_id not in workshop_ids:
                workshop_ids += [workshop_id]

        return workshop_ids

    @classmethod
    def _get_search_html(cls, search_text, tags="Mod", sort="mostrecent"):
        parameters = {}
        parameters.update({"appid": "107410"})
        parameters.update({"searchtext": search_text})
        parameters.update({"childpublishedfileid": "0"})
        parameters.update({"browsesort": sort})
        parameters.update({"section": "readytouseitems"})
        parameters.update({"requiredtags[]": tags})
        url = "http://steamcommunity.com/workshop/browse/"

        data = urllib.parse.urlencode(parameters)
        req = urllib.request.Request(url + "?" + data)
        html = None
        try:
            r = urllib.request.urlopen(req)
            html = r.read()
        except urllib.error.URLError as e:
            print(e.reason)
        return html.decode("utf-8")

    @classmethod
    def _find_ids(cls, s):
        workshop_id = re.findall("\d{4,15}", s)
        return workshop_id

    @classmethod
    def _parse_filedetails(cls, html):
        from bs4 import BeautifulSoup  # https://www.crummy.com/software/BeautifulSoup/bs4/doc/

        details = {}
        soup = BeautifulSoup(html, "html.parser")

        # Workshop error handling
        message = soup.find(id="message")
        if message is not None:
            details["message"] = str(message.string)
            return details

        link = soup.find(href=re.compile("(filedetails/\?id)")).get("href")
        details["id"] = SteamWorkshop._find_ids(link)[0]

        html_details = soup.find(id="mainContents")
        details["name"] = html_details.find("div", "workshopItemTitle").string

        if html_details.find(id="previewImageMain") is not None:
            details["logo_url"] = html_details.find(id="previewImageMain").get("src")
        if html_details.find(id="previewImage") is not None:
            details["logo_url"] = html_details.find(id="previewImage").get("src")

        items = html_details.find(id="RequiredItems")
        items = str(items)
        details["require"] = SteamWorkshop._find_ids(items)

        details["size"] = html_details.find("div", "detailsStatRight").string

        for i in details.keys():
            if i != "require":
                details[i] = str(details[i])

        return details


def parser_args():
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

    parser.add_argument("-y", "--yes", action="store_true", default=False,
                        help='yes to all confirmations')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbosity", action="count", default=0,
                       help="increase output verbosity")
    group.add_argument("-q", "--quiet", action="store_true", default=False,
                       help="")

    options = parser.parse_args()
    if isinstance(options, tuple):
        args = options[0]
    else:
        args = options

    return args


class CLI:

    @staticmethod
    def main(args, method_name=None):
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
        text = ""
        for s in args.args:
            text += s+" "
        mods = SteamWorkshop.search(text, args.sort)
        print("Found:")
        for m in mods:
            mod = Mod(m)
            print("", mod.str_one_line())
            if len(mod.require) > 0:
                names = ""
                size = 0
                for d in mod.require:
                    names += d.name+", "
                    size += d.size
                print(" Dependencies: {:8.2f} MB   {}".format(size/pow(1024, 2), names[:-2]))

    @staticmethod
    def set(args):
        if args.var == "login":
            Params().set(args.var, [args.username, args.password])
        if args.var == "install_dir":
            Params().set(args.var, args.directory)

    @staticmethod
    def info(args):
        mod = Mod(args.workshop_id)
        print(mod)

    @staticmethod
    def list(args):
        mods = DB().mods
        sizes = [m.size for m in mods]
        dependencies = []
        print("Installed:")
        for mod in mods:
            for m in mod.require:
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
        # fail early and gracefully
        error = False
        if not Params().isset("install_dir"):
            error = True
            print("Please set installation directory.")
            print("use: set install_dir <directory>")
        if not Params().isset("login"):
            error = True
            print("Please set steam login first.")
            print("use: set login <login_name> <password>")
        if error:
            return 0

        # group mods
        install = []
        installed = []
        not_found = []
        for mod_id in args.workshop_ids:
            if SteamWorkshop.exists(mod_id):
                if not DB().exists(mod_id):
                    if mod_id not in install:
                        install += [mod_id]
                else:
                    installed += [mod_id]
            else:
                not_found += [mod_id]

        sizes = []
        mods = [Mod(mod) for mod in install]
        dependencies = []
        if len(install) > 0:
            print("Installing:")
            for mod in mods:
                sizes += [mod.size]
                for m in mod.require:
                    if not DB().exists(m.id):
                        if m not in mods:
                            if m not in dependencies:
                                dependencies += [m]
                                install += [m.id]
                print("", mod.str_one_line())
        if len(dependencies) > 0:
            print("Installing dependencies:")
            for mod in dependencies:
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
            DB().install(mod)

        SteamWorkshop.download(install)

    @staticmethod
    def remove(args):
        for m in args.workshop_ids:
            if not DB().exists(m):
                print(m, "not installed.")
            else:
                mod = DB().get(m)
                DB().remove(m)
                print(mod.name, "removed.")

    @staticmethod
    def update(args):
        if args.workshop_ids[0] == "all":
            install = []
            for mod in DB().mods:
                install += [mod.id]
                for mod in mod.require:
                    install += [mod.id]
            SteamWorkshop.download(install)
        else:
            for mod_id in args.workshop_ids:
                if DB().exists(mod_id):
                    mod = DB().get(mod_id)
                    print("updating", mod.name)
                    SteamWorkshop.download(mod.id)
                    for mod in mod.require:
                        print("updating", mod.name)
                        SteamWorkshop.download(mod.id)
                else:
                    print(mod_id, "not installed.")


if __name__ == "__main__":
    args = parser_args()
    try:
        exit(CLI.main(args))
        pass
    except KeyboardInterrupt:
        pass
