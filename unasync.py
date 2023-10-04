"""Top-level package for unasync."""

import collections
import glob
import os
import tokenize as std_tokenize

import tokenize_rt

_ASYNC_TO_SYNC = {
    "__aenter__": "__enter__",
    "__aexit__": "__exit__",
    "__aiter__": "__iter__",
    "__anext__": "__next__",
    "asynccontextmanager": "contextmanager",
    "AsyncIterable": "Iterable",
    "AsyncIterator": "Iterator",
    "AsyncGenerator": "Generator",
    # TODO StopIteration is still accepted in Python 2, but the right change
    # is 'raise StopAsyncIteration' -> 'return' since we want to use unasynced
    # code in Python 3.7+
    "StopAsyncIteration": "StopIteration",
}

_IMPORTS_REPLACE = {

}


class Rule:
    """A single set of rules for 'unasync'ing file(s)"""

    def __init__(self, fromdir, todir, additional_replacements=None):
        self.fromdir = fromdir.replace("/", os.sep)
        self.todir = todir.replace("/", os.sep)

        # Add any additional user-defined token replacements to our list.
        self.token_replacements = _ASYNC_TO_SYNC.copy()
        for key, val in (additional_replacements or {}).items():
            self.token_replacements[key] = val

    def _match(self, filepath):
        """Determines if a Rule matches a given filepath and if so
        returns a higher comparable value if the match is more specific.
        """
        file_segments = [x for x in filepath.split(os.sep) if x]
        from_segments = [x for x in self.fromdir.split(os.sep) if x]
        len_from_segments = len(from_segments)

        if len_from_segments > len(file_segments):
            return False

        for i in range(len(file_segments) - len_from_segments + 1):
            if file_segments[i: i + len_from_segments] == from_segments:
                return len_from_segments, i

        return False

    def _unasync_file(self, filepath):
        with open(filepath, "rb") as f:
            encoding, _ = std_tokenize.detect_encoding(f.readline)

        with open(filepath, "rt", encoding=encoding) as f:
            tokens = tokenize_rt.src_to_tokens(f.read())
            tokens = self._unasync_tokens(tokens)
            result = tokenize_rt.tokens_to_src(tokens)
            outfilepath = filepath.replace(self.fromdir, self.todir)
            os.makedirs(os.path.dirname(outfilepath), exist_ok=True)
            with open(outfilepath, "wb") as f:
                f.write(result.encode(encoding))

    def _unasync_tokens(self, tokens: list):
        new_tokens = []
        token_counter = 0
        while token_counter < len(tokens):
            token = tokens[token_counter]

            if token.src in ["async", "await"]:
                token_counter = token_counter + 1  # When removing async or await, we want to skip the following whitespace
                continue
            elif token.name == "NAME":
                if token.src == "from":
                    if tokens[token_counter + 1].src == " ":
                        token_counter = self._replace_import(tokens, token_counter, new_tokens)
                        continue
                    else:
                        token = token._replace(src=self._unasync_name(token.src))
            elif token.name == "STRING":
                left_quote, name, right_quote = (
                    token.src[0],
                    token.src[1:-1],
                    token.src[-1],
                )
                token = token._replace(
                    src=left_quote + self._unasync_name(name) + right_quote
                )

            new_tokens.append(token)
            token_counter = token_counter + 1

        return new_tokens

        # for i, token in enumerate(tokens):
        #     if skip_next:
        #         skip_next = False
        #         continue
        #
        #     if token.src in ["async", "await"]:
        #         # When removing async or await, we want to skip the following whitespace
        #         # so that `print(await stuff)` becomes `print(stuff)` and not `print( stuff)`
        #         skip_next = True
        #     else:
        #         if token.name == "NAME":
        #             token = token._replace(src=self._unasync_name(token.src))
        #         elif token.name == "STRING":
        #             left_quote, name, right_quote = (
        #                 token.src[0],
        #                 token.src[1:-1],
        #                 token.src[-1],
        #             )
        #             token = token._replace(
        #                 src=left_quote + self._unasync_name(name) + right_quote
        #             )
        #
        #         yield token

    def _replace_import(self, tokens, token_counter, new_tokens: list):
        new_tokens.append(tokens[token_counter])
        new_tokens.append(tokens[token_counter + 1])

        full_lib_name = ''
        lib_name_counter = token_counter + 2
        while True:
            if tokens[lib_name_counter].src == " ":
                break
            full_lib_name = full_lib_name + tokens[lib_name_counter].src
            lib_name_counter = lib_name_counter + 1

        for key, value in _IMPORTS_REPLACE.items():
            if key in full_lib_name:
                updated_lib_name = full_lib_name.replace(key, value)
                for lib_name_part in updated_lib_name.split("."):
                    new_tokens.append(tokenize_rt.Token("NAME", lib_name_part))
                    new_tokens.append(tokenize_rt.Token("OP", "."))
                if full_lib_name == key:
                    new_tokens.pop()
            else:
                lib_name_counter = token_counter + 2
        return lib_name_counter

    def _unasync_name(self, name):
        if name in self.token_replacements:
            return self.token_replacements[name]
        # Convert classes prefixed with 'Async' into 'Sync'
        elif len(name) > 5 and name.startswith("Async") and name[5].isupper():
            return "Sync" + name[5:]
        return name


def unasync_files(fpath_list, rules):
    for f in fpath_list:
        found_rule = None
        found_weight = None

        for rule in rules:
            weight = rule._match(f)
            if weight and (found_weight is None or weight > found_weight):
                found_rule = rule
                found_weight = weight

        if found_rule:
            found_rule._unasync_file(f)


_IMPORTS_REPLACE["ably.http.paginatedresult"] = "ably.dong.paginatedresult"
Token = collections.namedtuple("Token", ["type", "string", "start", "end", "line"])

src_dir_path = os.path.join(os.getcwd(), "ably", "rest")
dest_dir_path = os.path.join(os.getcwd(), "ably", "sync", "rest")
_DEFAULT_RULE = Rule(fromdir=src_dir_path, todir=dest_dir_path)

os.makedirs(dest_dir_path, exist_ok=True)


def find_files(dir_path, file_name_regex) -> list[str]:
    return glob.glob(os.path.join(dir_path, "*" + file_name_regex))


src_files = find_files(src_dir_path, ".py")

unasync_files(src_files, (_DEFAULT_RULE,))

# round 2
src_dir_path = os.path.join(os.getcwd(), "ably", "http")
dest_dir_path = os.path.join(os.getcwd(), "ably", "sync", "http")
_DEFAULT_RULE = Rule(fromdir=src_dir_path, todir=dest_dir_path)

src_files = find_files(src_dir_path, ".py")

unasync_files(src_files, (_DEFAULT_RULE,))

# round 3

src_dir_path = os.path.join(os.getcwd(), "ably", "types")
dest_dir_path = os.path.join(os.getcwd(), "ably", "sync", "types")
_DEFAULT_RULE = Rule(fromdir=src_dir_path, todir=dest_dir_path)

src_files = find_files(src_dir_path, "presence.py")

unasync_files(src_files, (_DEFAULT_RULE,))

# class _build_py(orig.build_py):
#     """
#     Subclass build_py from setuptools to modify its behavior.
#
#     Convert files in _async dir from being asynchronous to synchronous
#     and saves them in _sync dir.
#     """
#
#     UNASYNC_RULES = (_DEFAULT_RULE,)
#
#     def run(self):
#         rules = self.UNASYNC_RULES
#
#         self._updated_files = []
#
#         # Base class code
#         if self.py_modules:
#             self.build_modules()
#         if self.packages:
#             self.build_packages()
#             self.build_package_data()
#
#         # Our modification!
#         unasync_files(self._updated_files, rules)
#
#         # Remaining base class code
#         self.byte_compile(self.get_outputs(include_bytecode=0))
#
#     def build_module(self, module, module_file, package):
#         outfile, copied = super().build_module(module, module_file, package)
#         if copied:
#             self._updated_files.append(outfile)
#         return outfile, copied
#
#
# def cmdclass_build_py(rules=(_DEFAULT_RULE,)):
#     """Creates a 'build_py' class for use within 'cmdclass={"build_py": ...}'"""
#
#     class _custom_build_py(_build_py):
#         UNASYNC_RULES = rules
#
#     return _custom_build_py
