"""
Chocolatey plugin by dufferZafar

https://keypirinha.com/api/plugin.html
https://keypirinha.com/api/plugin.html#keypirinha.Plugin.create_item
"""

import os
import traceback
import urllib.error
import urllib.parse
import ctypes
import xml.etree.ElementTree as ET

from enum import Enum
from collections import defaultdict

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet


def etree_to_dict(t):
    """
    Converts an etree.Element to dict

    Source: https://stackoverflow.com/a/10076823
    Uses a trick to remove namespaces: https://stackoverflow.com/a/25920989
    """
    _, _, tag = t.tag.rpartition("}")
    d = {tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        a = {}
        for k, v in t.attrib.items():
            _, _, g = k.rpartition("}")
            a["@" + g] = v
        d[tag].update(a)
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[tag]["#text"] = text
        else:
            d[tag] = text
    return d


class Chocolatey(kp.Plugin):
    """List and install chocolatey packages"""

    _debug = True

    API_ROOT = "https://chocolatey.org/api/v2/Search()"
    API_PARAMS = {
        "$filter": "IsLatestVersion",
        "$skip": "0",
        "$top": "15",  # 30
        # "$orderby": "DownloadCount%20desc",
        "searchTerm": "",
        "targetFramework": "''",
        "includePrerelease": "false",
    }
    API_USER_AGENT = "Mozilla/5.0"

    ITEMCAT_CHOCOLATEY = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 2

    ACTION = Enum(
        "ACTION",
        [
            "install",
            "open_project_url",
            "open_project_src_url",
            "open_choco_url",
            "open_pkg_src_url",
        ],
    )

    DEFAULT_IDLE_TIME = 0.25

    def __init__(self):
        super().__init__()

    def on_start(self):
        # Can do any heavy one-time initialization
        # Download icons? Download a list of ALL packages?
        actions = [
            self.create_action(
                name=self.ACTION.install.name,
                label="Install the package",
            ),
            self.create_action(
                name=self.ACTION.open_project_url.name,
                label="Open software site",
            ),
            self.create_action(
                name=self.ACTION.open_project_src_url.name,
                label="Open software source",
            ),
            self.create_action(
                name=self.ACTION.open_choco_url.name,
                label="Open chocolatey page",
            ),
            self.create_action(
                name=self.ACTION.open_pkg_src_url.name,
                label="Open chocolatey package source",
            ),
        ]
        self.set_actions(self.ITEMCAT_RESULT, actions)

    def on_catalog(self):
        catalog = []
        catalog.append(
            self.create_item(
                category=self.ITEMCAT_CHOCOLATEY,
                label="Chocolatey: Install",
                target="install",
                short_desc="Search and install packages via chocolatey",
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.KEEPALL,
            )
        )

        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):

        if (
            not user_input
            or not items_chain
            or items_chain[-1].category() != self.ITEMCAT_CHOCOLATEY
            or self.should_terminate(self.DEFAULT_IDLE_TIME)
        ):
            return

        # current_item = items_chain[-1]
        suggestions = []
        try:
            url = self._build_api_url(user_input)

            opener = kpnet.build_urllib_opener()
            opener.addheaders = [("User-agent", self.API_USER_AGENT)]
            with opener.open(url) as conn:
                response = conn.read()

            if self.should_terminate():
                return

            suggestions.extend(
                [
                    self._create_result_item(result)
                    for result in self._parse_api_response(response)
                ]
            )

        except urllib.error.HTTPError as exc:
            suggestions.append(
                self.create_error_item(label=user_input, short_desc=str(exc))
            )
        except Exception as exc:
            suggestions.append(
                self.create_error_item(
                    label=user_input, short_desc="Error: " + str(exc)
                )
            )
            traceback.print_exc()

        if suggestions:
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def _build_api_url(self, query):
        self.API_PARAMS["searchTerm"] = "'%s'" % urllib.parse.quote_plus(query)

        url = (
            self.API_ROOT
            + "?"
            + "&".join("%s=%s" % (k, v) for k, v in self.API_PARAMS.items())
        )

        return url

    def _parse_api_response(self, response):
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
        }
        tree = ET.fromstring(response)
        return tree.findall(".//atom:entry", ns)

    def __load_icon(self, icon_url):
        icon_handle = None
        try:
            if not icon_url:
                return icon_handle

            cache_dir = self.get_package_cache_path(True)
            icon_name = icon_url.split("/")[-1]
            icon_path = cache_dir + "\\" + icon_name

            if not os.path.exists(icon_path):
                opener = kpnet.build_urllib_opener()
                with opener.open(icon_url) as conn:
                    with open(icon_path, "wb") as out:
                        response = conn.read()
                        out.write(response)

            icon_handle = self.load_icon("cache://Chocolatey/" + icon_name)
        except Exception as exc:
            pass
        return icon_handle

    def _create_result_item(self, result):
        entry = etree_to_dict(result).pop("entry")

        title = entry.get("title", {}).get("#text", "")
        author = entry.get("author", {}).get("name", "")
        summary = entry.get("summary", {}).get("#text", "")

        props = entry.pop("properties")
        version = props["Version"] or ""
        icon_url = props["IconUrl"] or ""
        choco_url = props["GalleryDetailsUrl"] or ""
        pkg_src_url = props["PackageSourceUrl"] or ""
        project_url = props["ProjectUrl"] or ""
        project_src_url = props["ProjectSourceUrl"] or ""

        return self.create_item(
            category=self.ITEMCAT_RESULT,
            label="%s by %s" % (title, author),
            short_desc="[%s] %s" % (version, summary),
            target=title,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.KEEPALL,
            icon_handle=self.__load_icon(icon_url),
            data_bag="\n".join([choco_url, pkg_src_url, project_url, project_src_url]),
        )

    def on_execute(self, item, action):
        if item.category() != self.ITEMCAT_RESULT:
            return

        choco_url, pkg_src_url, project_url, project_src_url = item.data_bag().split(
            "\n"
        )

        if action and action.name() == self.ACTION.install.name:
            cmd = " ".join(
                ["-NoExit", "-Command", "& {choco install %s}" % item.target()]
            )
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", "powershell.exe", cmd, None, 1
            )

        if action and action.name() == self.ACTION.open_project_url.name:
            kpu.web_browser_command(url=project_url, execute=True)

        elif action and action.name() == self.ACTION.open_project_src_url.name:
            kpu.web_browser_command(url=project_src_url, execute=True)

        elif action and action.name() == self.ACTION.open_choco_url.name:
            kpu.web_browser_command(url=choco_url, execute=True)

        elif action and action.name() == self.ACTION.open_pkg_src_url.name:
            kpu.web_browser_command(url=pkg_src_url, execute=True)
