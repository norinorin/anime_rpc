import ast
import inspect
import re

import discordrpc  # type: ignore


# s: https://medium.com/@chipiga86/python-monkey-patching-like-a-boss-87d7ddb8098e
def source(o):  # type: ignore
    s = inspect.getsource(o).split("\n")  # type: ignore
    indent = len(s[0]) - len(s[0].lstrip())
    return "\n".join(i[indent:] for i in s)


source_ = source(discordrpc.RPC.set_activity)  # type: ignore
patched = re.sub(
    r"(remove_none\(act\))",
    r"\1 or None",
    source_,
)
patched = re.sub(
    r"(self._setup\(\))",
    r"\1\n\n    print(remove_none(act) or None)\n",
    patched,
)

loc = {}
exec(compile(ast.parse(patched), "<string>", "exec"), discordrpc.presence.__dict__, loc)  # type: ignore

discordrpc.RPC.set_activity = loc["set_activity"]
