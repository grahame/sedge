import os
import pipes
import sys
import urllib
from io import StringIO
from itertools import product

import requests

from .keylib import KeyNotFound


class SedgeException(Exception):
    pass


class SecurityException(SedgeException):
    pass


class ParserException(SedgeException):
    pass


class OutputException(SedgeException):
    pass


class Section:
    def __init__(self, name, with_exprs):
        self.name = name
        self.with_exprs = with_exprs
        self.lines = []
        self.types = []
        self.identities = []

    def has_lines(self):
        return len(self.lines) > 0

    def add_line(self, keyword, parts):
        self.lines.append((keyword, parts))

    def add_type(self, name):
        self.types.append(name)

    def add_identity(self, name):
        self.identities.append(name)

    def get_lines(self, config_access, visited_set):
        """
        get the lines for this section
        visited_set is used to avoid visiting same section
        twice, if we've got a diamond in the @is setup
        """
        if self in visited_set:
            return []
        lines = self.lines.copy()
        visited_set.add(self)
        for identity in self.identities:
            if config_access.get_keyfile(identity):
                lines.append(('IdentitiesOnly', ['yes']))
                lines.append(('IdentityFile', [pipes.quote(config_access.get_keyfile(identity))]))
        for section_name in self.types:
            section = config_access.get_section(section_name)
            lines += section.get_lines(config_access, visited_set)
        return lines

    def __repr__(self):
        s = "{_type}:{name}".format(_type=type(self).__name__, name=self.name)
        if self.with_exprs:
            s += '[' + ','.join(' '.join(t) for t in self.with_exprs) + ']'
        return '<%s>' % s


class Root(Section):
    def __init__(self):
        super(Root, self).__init__('Root', [])
        self.pending_with = []
        self.vals = {}

    def add_type(self, name):
        raise ParserException('Cannot set an @is type on root scope.')

    def add_pending_with(self, parts):
        self.pending_with.append(parts)

    def pop_pending_with(self):
        r = self.pending_with
        self.pending_with = []
        return r

    def has_pending_with(self):
        return len(self.pending_with) > 0

    def set_value(self, key, value):
        self.vals[key] = value

    def get_variables(self):
        return self.vals

    def output_lines(self):
        for keyword, parts in sorted(self.lines):
            yield ConfigOutput.to_line(keyword, parts)


class HostAttrs(Section):
    def __init__(self, name):
        super(HostAttrs, self).__init__(name, [])


class Host(Section):
    @classmethod
    def expand_with_token(cls, s):
        fmt_error = 'range should be format {A..B} or {A..B/C}'
        if not s.startswith('{') or not s.endswith('}'):
            return [s]
        try:
            range_defn = s[1:-1]
            incr = 1
            if '/' in range_defn:
                range_defn, incr = range_defn.rsplit('/', 1)
                incr = int(incr)
            range_parts = range_defn.split('..')
            if len(range_parts) != 2:
                raise ParserException(fmt_error)
            from_val, to_val = (int(t) for t in range_parts)
            to_val += 1  # inclusive end
            from_width = len('%0s' % range_parts[0])
            to_width = len('%0s' % range_parts[1])
        except ValueError:
            raise ParserException('expected an integer in range definition.')
        if from_width == to_width:
            return ["%0*d" % (to_width, t) for t in range(from_val, to_val, incr)]
        else:
            return list(str(t) for t in range(from_val, to_val, incr))

    @classmethod
    def expand_with(cls, defn):
        expanded = []
        for tok in defn:
            expanded += Host.expand_with_token(tok)
        return expanded

    def resolve_defn(self, config_access):
        visited = set()
        # we shove the name in here, then on the other end of the substitution
        # logic we can get it back out. FIXME clean this up.
        lines = [self.name]
        for keyword, parts in self.get_lines(config_access, visited):
            lines.append(ConfigOutput.to_line(keyword, parts, indent=4))
        return lines

    def apply_substitutions(self, lines, val_dict):
        for line in lines:
            for subst, value in val_dict.items():
                line = line.replace(subst, value)
            yield line

    def variable_iter(self, base):
        """
        returns iterator over the cross product of the variables
        for this stanza
        """
        base_substs = dict(('<' + t + '>', u) for (t, u) in base.items())
        substs = []
        vals = []
        for with_defn in self.with_exprs:
            substs.append('<' + with_defn[0] + '>')
            vals.append(Host.expand_with(with_defn[1:]))
        for val_tpl in product(*vals):
            r = base_substs.copy()
            r.update(dict(zip(substs, val_tpl)))
            yield r

    def host_stanzas(self, config_access):
        """
        returns a list of host definitions
        """
        defn_lines = self.resolve_defn(config_access)
        for val_dict in self.variable_iter(config_access.get_variables()):
            subst = list(self.apply_substitutions(defn_lines, val_dict))
            host = subst[0]
            lines = [ConfigOutput.to_line('Host', [host])] + subst[1:]
            yield host, lines


class SectionConfigAccess:
    """
    sections may require access to other parts of the file.
    this class provides that access.
    """

    def __init__(self, config):
        self._config = config

    def get_section(self, name):
        return self._config._get_section_by_name(name)

    def get_keyfile(self, name):
        try:
            fingerprints = self._config.keydefs[name]
        except KeyError:
            self._config.warn("identity '{}' is not defined (missing @key definition)".format(name))
            return None
        for fingerprint in fingerprints:
            try:
                return self._config._key_library.lookup(fingerprint)
            except KeyNotFound:
                pass
        self._config.warn("identity '{name}' (fingerprints {fingerprints}) not found in SSH key library".format(
            name=name,
            fingerprints='; '.join(fingerprints))
        )

    def get_variables(self):
        return self._config.sections[0].get_variables()


class ConfigOutput:
    def __init__(self, fd):
        self._fd = fd
        self.need_break = False

    def write_stanza(self, it):
        if self.need_break:
            self._fd.write('\n')
        for i, line in enumerate(it):
            if i == 0:
                self.need_break = True
            self._fd.write(line + '\n')

    @classmethod
    def to_line(cls, keyword, parts, indent=0):
        def add_indent(s):
            return ' ' * indent + s

        if len(parts) == 1:
            return add_indent(' '.join([keyword, '=', parts[0]]))
        out = [keyword]
        for part in parts:
            if '"' in part:
                raise OutputException("quotation marks may not be used in arguments")
            if ' ' in part:
                out.append("{}".format(part))
            else:
                out.append(part)
        return add_indent(' '.join(out))


class SedgeEngine:
    """
    base parser for a sedge configuration file.
    handles all directives and expansions
    """

    def __init__(self, key_library, fd, verify_ssl, url=None, args=None, parent_keydefs=None, via_include=False):
        self._key_library = key_library
        self._url = url
        self._args = args
        self._verify_ssl = verify_ssl
        self._via_include = via_include
        self.sections = [Root()]
        self.includes = []
        self.keydefs = {}
        if parent_keydefs is not None:
            self.keydefs.update(parent_keydefs)
        self.parse(fd)

    def warn(self, message):
        print("{url}: {msg}".format(url=self._url, msg=message), file=sys.stderr)

    @classmethod
    def parse_other_space(cls, other):
        in_quote = False
        args = []
        current = []

        def pop_current():
            val = ''.join(current)
            if val:
                args.append(val)
            current.clear()

        for c in other:
            if in_quote:
                if c == '"':
                    in_quote = False
                    pop_current()
                else:
                    current.append(c)
            else:
                if c == '"':
                    if len(current) > 0:
                        raise ParserException('quotation marks cannot be used within an argument value')
                    in_quote = True
                else:
                    if c == ' ':
                        pop_current()
                    else:
                        current.append(c)
        if in_quote:
            raise ParserException('unterminated quotation marks')
        pop_current()
        return args

    # from the ssh_config manual page:
    #  > ... format ``keyword arguments''.  Configuration options may be
    #  > separated by whitespace or optional whitespace and exactly one `='; the
    #  > latter format is useful to avoid the need to quote whitespace when speci-
    #  > fying configuration options using the ssh, scp, and sftp -o option.
    #  > Arguments may optionally be enclosed in double quotes (") in order to
    #  > represent arguments containing spaces.
    @classmethod
    def parse_config_line(cls, line):
        if '=' in line:
            line_parts = line.strip().split('=', 1)
            return line_parts[0].rstrip(), [line_parts[1].lstrip()]
        else:
            line_parts = line.strip().split(' ', 1)
            other = ''
            if len(line_parts) == 2:
                other = line_parts[1].strip()
            return line_parts[0], SedgeEngine.parse_other_space(other)

    def is_include(self):
        return self._via_include

    def parse(self, fd):
        """very simple parser - but why would we want it to be complex?"""

        def resolve_args(args):
            # FIXME break this out, it's in common with the templating stuff elsewhere
            root = self.sections[0]
            val_dict = dict(('<' + t + '>', u) for (t, u) in root.get_variables().items())
            resolved_args = []
            for arg in args:
                for subst, value in val_dict.items():
                    arg = arg.replace(subst, value)
                resolved_args.append(arg)
            return resolved_args

        def handle_section_defn(keyword, parts):
            if keyword == '@HostAttrs':
                if len(parts) != 1:
                    raise ParserException('usage: @HostAttrs <hostname>')
                if self.sections[0].has_pending_with():
                    raise ParserException('@with not supported with @HostAttrs')
                self.sections.append(HostAttrs(parts[0]))
                return True
            if keyword == 'Host':
                if len(parts) != 1:
                    raise ParserException('usage: Host <hostname>')
                self.sections.append(Host(parts[0], self.sections[0].pop_pending_with()))
                return True

        def handle_vardef(root, keyword, parts):
            if keyword == '@with':
                root.add_pending_with(parts)
                return True

        def handle_set_args(_, parts):
            if len(parts) == 0:
                raise ParserException('usage: @args arg-name ...')
            if not self.is_include():
                return
            if self._args is None or len(self._args) != len(parts):
                raise ParserException('required arguments not passed to include {url} ({parts})'.format(
                    url=self._url,
                    parts=', '.join(parts))
                )
            root = self.sections[0]
            for key, value in zip(parts, self._args):
                root.set_value(key, value)

        def handle_set_value(_, parts):
            if len(parts) != 2:
                raise ParserException('usage: @set <key> <value>')
            root = self.sections[0]
            root.set_value(*resolve_args(parts))

        def handle_add_type(section, parts):
            if len(parts) != 1:
                raise ParserException('usage: @is <HostAttrName>')
            section.add_type(parts[0])

        def handle_via(section, parts):
            if len(parts) != 1:
                raise ParserException('usage: @via <Hostname>')
            section.add_line(
                'ProxyCommand',
                ('ssh {args} nc %h %p 2> /dev/null'.format(args=pipes.quote(resolve_args(parts)[0])), )
            )

        def handle_identity(section, parts):
            if len(parts) != 1:
                raise ParserException('usage: @identity <name>')
            section.add_identity(resolve_args(parts)[0])

        def handle_include(_, parts):
            if len(parts) == 0:
                raise ParserException('usage: @include <https://...|/path/to/file.sedge> [arg ...]')
            url = parts[0]
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.scheme == 'https':
                req = requests.get(url, verify=self._verify_ssl)
                text = req.text
            elif parsed_url.scheme == 'file':
                with open(parsed_url.path) as fd:
                    text = fd.read()
            elif parsed_url.scheme == '':
                path = os.path.expanduser(url)
                with open(path) as fd:
                    text = fd.read()
            else:
                raise SecurityException('error: @includes may only use paths or https:// or file:// URLs')

            subconfig = SedgeEngine(
                self._key_library,
                StringIO(text),
                self._verify_ssl,
                url=url,
                args=resolve_args(parts[1:]),
                parent_keydefs=self.keydefs,
                via_include=True)
            self.includes.append((url, subconfig))

        def handle_keydef(_, parts):
            if len(parts) < 2:
                raise ParserException('usage: @key <name> [fingerprint]...')
            name = parts[0]
            fingerprints = parts[1:]
            self.keydefs[name] = fingerprints

        def handle_keyword(section, keyword, parts):
            handlers = {
                '@set': handle_set_value,
                '@args': handle_set_args,
                '@is': handle_add_type,
                '@via': handle_via,
                '@include': handle_include,
                '@key': handle_keydef,
                '@identity': handle_identity
            }
            if keyword in handlers:
                handlers[keyword](section, parts)
                return True

        for line in (t.strip() for t in fd):
            if line.startswith('#') or line == '':
                continue
            keyword, parts = SedgeEngine.parse_config_line(line)
            if handle_section_defn(keyword, parts):
                continue
            if handle_vardef(self.sections[0], keyword, parts):
                continue
            current_section = self.sections[-1]
            if handle_keyword(current_section, keyword, parts):
                continue
            if keyword.startswith('@'):
                raise ParserException("unknown expansion keyword {}".format(keyword))
            # use other rather than parts to avoid messing up user
            # whitespace; we don't handle quotes in here as we don't
            # need to
            current_section.add_line(keyword, parts)

    def sections_for_cls(self, cls):
        return (t for t in self.sections if isinstance(t, cls))

    def _get_section_by_name(self, name):
        matches = [t for t in self.sections if t.name == name]
        if len(matches) > 1:
            raise ParserException("More than one section with name '{}'".format(name))
        if len(matches) == 0:
            raise ParserException("No such section: {}".format(name))
        return matches[0]

    def host_stanzas(self):
        for host in self.sections_for_cls(Host):
            for tpl in host.host_stanzas(SectionConfigAccess(self)):
                yield tpl

    def output(self, out, stanza_names=None):
        # output global config from root section
        root = self.sections[0]
        if self.is_include():
            if root.has_lines():
                print("Warning: global config in @include '{url}' ignored.".format(url=self._url), file=sys.stderr)
                print("Ignored lines are:", file=sys.stderr)
                warning_fd = StringIO()
                warning_out = ConfigOutput(warning_fd)
                warning_out.write_stanza(root.output_lines())
                print("\n".join([" > " + t for t in warning_fd.getvalue().splitlines()]), file=sys.stderr)
        else:
            out.write_stanza(root.output_lines())

        if stanza_names is None:
            stanza_names = set()

        dupes = set()
        for hostname, stanza in self.host_stanzas():
            if hostname in stanza_names:
                dupes.add(hostname)
            stanza_names.add(hostname)
            out.write_stanza(stanza)
        if dupes:
            print("Warning: duplicated hosts parsing '{url}'".format(url=self._url), file=sys.stderr)
            print("  %s" % (', '.join(sorted(dupes))), file=sys.stderr)

        for url, subconfig in self.includes:
            subconfig.output(out, stanza_names)

        # write out a list of hosts for completion use
        if not self.is_include():
            outf = os.path.expanduser("~/.sedge/hosts")
            pattern_characters = (',', '!', '*', '?')
            try:
                with open(outf, 'w') as fd:
                    for host in sorted(stanza_names):
                        if any(host.find(c) != -1 for c in pattern_characters):
                            continue
                        print(host, file=fd)
            except IOError:
                print("warning: ~/.sedge/hosts could not be written.", file=sys.stderr)
