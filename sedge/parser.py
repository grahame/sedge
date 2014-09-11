import pipes
from itertools import product


class ParserException(Exception):
    pass


class Section:
    def __init__(self, name, with_exprs):
        self.name = name
        self.with_exprs = with_exprs
        self.lines = []
        self.types = []
        self.expansions = []

    def add_line(self, keyword, parts):
        self.lines.append((keyword, parts))

    def add_type(self, name):
        self.types.append(name)

    def add_expansion(self, parts):
        self.expansions.append(parts)

    def get_lines(self, section_lookup_fn, visited_set):
        """
        get the lines for this section
        visited_set is used to avoid visiting same section
        twice, if we've got a diamond in the @is setup
        """
        if self in visited_set:
            return []
        lines = self.lines.copy()
        visited_set.add(self)
        for section_name in self.types:
            section = section_lookup_fn(section_name)
            lines += section.get_lines(section_lookup_fn, visited_set)
        return lines

    def __repr__(self):
        s = "%s:%s" % (type(self).__name__, self.name)
        if self.with_exprs:
            s += '[' + ','.join(' '.join(t) for t in self.with_exprs) + ']'
        return '<%s>' % s


class Root(Section):
    def __init__(self):
        super(Root, self).__init__('Root', [])
        self.pending_with = []

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

    def output_lines(self, fd):
        for keyword, parts in sorted(self.lines):
            fd.write('%s %s\n' % (keyword, ' '.join(parts)))
        fd.write('\n')


class HostAttrs(Section):
    def __init__(self, name):
        super(HostAttrs, self).__init__(name, [])


class Host(Section):
    @classmethod
    def expand_with(cls, defn):
        if len(defn) == 0:
            return []
        fmt_error = 'range should be format {A..B} or {A..B/C}'
        first = defn[0]
        if first.startswith('{') and first.endswith('}'):
            try:
                range_defn = first[1:-1]
                incr = 1
                if '/' in range_defn:
                    range_defn, incr = '/'.split(range_defn)
                    incr = int(incr)
                range_parts = range_defn.split('..')
                if len(range_parts) != 2:
                    raise ParserException(fmt_error)
                from_val, to_val = (int(t) for t in range_parts)
                to_val += 1  # inclusive end
            except ValueError:
                raise ParserException(
                    'expected an integer in range definition.')
            return list(range(from_val, to_val, incr))
        # if not a range, return as literal
        return defn

    def resolve_defn(self, section_lookup_fn):
        visited = set()
        lines = ['Host %s' % (self.name)]
        for keyword, parts in self.get_lines(section_lookup_fn, visited):
            line = '    %s %s' % (keyword, ' '.join(parts))
            lines.append(line)
        return '\n'.join(lines)

    def apply_substitutions(self, text, val_dict):
        for name, value in val_dict.items():
            defn = '<%s>' % (name)
            text = text.replace(defn, str(value))
        return text

    def get_hostdefs(self, section_lookup_fn):
        """
        returns a list of host definitions
        """
        hostdefs = []
        names = []
        vals = []
        for with_defn in self.with_exprs:
            names.append(with_defn[0])
            vals.append(Host.expand_with(with_defn[1:]))
        defn_text = self.resolve_defn(section_lookup_fn)
        for val_tpl in product(*vals):
            val_dict = dict(zip(names, val_tpl))
            hostdefs.append(
                self.apply_substitutions(defn_text, val_dict))
        return hostdefs


class SedgeConfig:
    """
    base parser for a sedge configuration file.
    handles all directives and expansions
    """
    def __init__(self, fd):
        self.sections = [Root()]
        self.parse(fd)

    def parse(self, fd):
        "very simple parser - but why would we want it to be complex?"

        def handle_section_defn(keyword, parts):
            if keyword == '@HostAttrs':
                if len(parts) != 1:
                    raise ParserException(
                        'usage: @HostAttrs <hostname>')
                if self.sections[0].has_pending_with():
                    raise ParserException(
                        '@with not supported with @HostAttrs')
                self.sections.append(HostAttrs(parts[0]))
                return True
            if keyword == 'Host':
                if len(parts) != 1:
                    raise ParserException('usage: Host <hostname>')
                self.sections.append(
                    Host(parts[0], self.sections[0].pop_pending_with()))
                return True

        def handle_vardef(root, keyword, parts):
            if keyword == '@with':
                root.add_pending_with(parts)
                return True

        def handle_expansion(section, keyword, parts):
            if keyword == '@is':
                if len(parts) != 1:
                    raise ParserException('usage: @is <HostAttrName>')
                section.add_type(parts[0])
                return True
            if keyword == '@via':
                if len(parts) != 1:
                    raise ParserException('usage: @is <Hostname>')
                section.add_line(
                    'ProxyCommand',
                    ('ssh %s nc %%h %%p 2> /dev/null' %
                        (pipes.quote(parts[0])),))
                return True

        for line in (t.strip() for t in fd):
            if line.startswith('#') or line == '':
                continue
            parts = [t.strip() for t in line.split()]
            keyword, parts = parts[0], parts[1:]
            if handle_section_defn(keyword, parts):
                continue
            if handle_vardef(self.sections[0], keyword, parts):
                continue
            current_section = self.sections[-1]
            if handle_expansion(current_section, keyword, parts):
                continue
            if keyword.startswith('@'):
                raise ParserException(
                    "unknown expansion keyword '%s'" % (keyword))
            current_section.add_line(keyword, parts)

    def sections_for_cls(self, cls):
        return (t for t in self.sections if isinstance(t, cls))

    def _get_section_by_name(self, name):
        matches = [t for t in self.sections if t.name == name]
        if len(matches) > 1:
            raise ParserException(
                "More than one section with name '%s'" % (name))
        if len(matches) == 0:
            raise ParserException("No such section: %s" % (name))
        return matches[0]

    def output(self, fd):
        # output global config from root section
        root = self.sections[0]
        root.output_lines(fd)
        for host in self.sections_for_cls(Host):
            for hostdef in host.get_hostdefs(self._get_section_by_name):
                fd.write(hostdef)
                fd.write('\n\n')
