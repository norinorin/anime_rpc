import argparse
from pathlib import Path

TEMPLATE = """
// ==UserScript==
// @name         Anime RPC - {name} Scraper
// @namespace    https://github.com/norinorin/anime_rpc
// @version      1.0.0
// @description  Adds {name} support to the Anime RPC Core Engine.
// @author       norinorin
// @downloadURL  https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/{base_filename}.user.js
// @updateURL    https://raw.githubusercontent.com/norinorin/anime_rpc/main/userscripts/services/{base_filename}.user.js
// @match        {match}
// @grant        unsafeWindow
// ==/UserScript==

(function () {{
  "use strict";

  const HOSTNAME = "{hostname}";

  function getState() {{
    return null;
  }}

  const registryInterval = setInterval(() => {{
    if (unsafeWindow.animeRPC_Scrapers) {{
      clearInterval(registryInterval);
      console.log("[{name} Scraper] Core engine found. Registering scraper.");
      unsafeWindow.animeRPC_Scrapers[HOSTNAME] = getState;
    }}
  }}, 100);
}})();
"""


class CLIArgs(argparse.Namespace):
    name: str
    base_filename: str
    match: str
    hostname: str
    force_overwrite: bool


parser = argparse.ArgumentParser("service_template_generator")
parser.add_argument(
    "-n",
    "--name",
    help="the name of service (should be stylised as needed, e.g., `YouTube` and not `youtube`)",
)
parser.add_argument(
    "-f",
    "--base-filename",
    help="base filename (in lower case) to write to, e.g., "
    "`-f youtube` will write to services/youtube.user.js",
    default=None,
)
parser.add_argument(
    "-m",
    "--match",
    help="the match pattern, e.g., `*://*.youtube.com/*`",
)
parser.add_argument(
    "--hostname",
    help="the hostname, e.g., `www.youtube.com`",
)
parser.add_argument(
    "-y",
    help="force overwrite if file exists",
    action="store_true",
    dest="force_overwrite",
)
args = parser.parse_args(namespace=CLIArgs)

if not args.base_filename:
    args.base_filename = args.name.lower()

TARGET = Path(f"userscripts/services/{args.base_filename}.user.js")

if TARGET.exists() and not args.force_overwrite:
    print(f"{TARGET} already exists, overwrite? [y/N] ", end="")
    if input().strip().lower() != "y":
        print("Not overwriting, exiting...")
        exit(1)

with open(TARGET, "w") as f:
    f.write(
        TEMPLATE.format(
            name=args.name,
            base_filename=args.base_filename,
            match=args.match,
            hostname=args.hostname,
        )
    )
print("Successfully wrote to", str(TARGET))
