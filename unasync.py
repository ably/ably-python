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
    "AsyncClient": "Client",
    "aclose": "close"
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
        async_await_block_started = False
        async_await_offset = 0
        while token_counter < len(tokens):
            token = tokens[token_counter]

            if async_await_block_started:
                if token.src == '\n':
                    new_tokens.append(token)
                    token_counter = token_counter + 1
                    next_newline_token = tokens[token_counter]
                    if len(next_newline_token.src) >= 6 and tokens[token_counter+1].utf8_byte_offset > async_await_offset:
                        new_tab_indentation = next_newline_token.src[:-6]  # remove last 6 white spaces
                        next_newline_token = next_newline_token._replace(src=new_tab_indentation)
                        new_tokens.append(next_newline_token)
                    else:
                        new_tokens.append(next_newline_token)
                    token_counter = token_counter + 1
                    continue

            if token.src == ')':
                async_await_block_started = False
                async_await_offset = 0

            if token.src in ["async", "await"]:
                # When removing async or await, we want to skip the following whitespace
                token_counter = token_counter + 2
                if (tokens[token_counter].src == 'def' or tokens[token_counter + 1].src == '(' or
                     tokens[token_counter + 2].src == '(' or tokens[token_counter + 3].src == "("):
                    # Fix indentation issues for async/await fn definition/call
                    async_await_offset = token.utf8_byte_offset
                    async_await_block_started = True
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
        if len(_IMPORTS_REPLACE.keys()) == 0:
            return lib_name_counter

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
                new_tokens.pop()
                return lib_name_counter

        lib_name_counter = token_counter + 2
        return lib_name_counter

    def _unasync_name(self, name):
        if name in self.token_replacements:
            return self.token_replacements[name]
        # Convert classes prefixed with 'Async' into 'Sync'
        # elif len(name) > 5 and name.startswith("Async") and name[5].isupper():
        #     return "Sync" + name[5:]
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


_IMPORTS_REPLACE["ably"] = "ably.sync"

Token = collections.namedtuple("Token", ["type", "string", "start", "end", "line"])

src_dir_path = os.path.join(os.getcwd(), "ably")
dest_dir_path = os.path.join(os.getcwd(), "ably", "sync")
_DEFAULT_RULE = Rule(fromdir=src_dir_path, todir=dest_dir_path)

os.makedirs(dest_dir_path, exist_ok=True)


def find_files(dir_path, file_name_regex) -> list[str]:
    return glob.glob(os.path.join(dir_path, "**", file_name_regex), recursive=True)


relevant_src_files = (set(find_files(src_dir_path, "*.py")) -
                      set(find_files(dest_dir_path, "*.py")))

unasync_files(list(relevant_src_files), (_DEFAULT_RULE,))