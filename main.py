import io
import pytest
import more_itertools


def vals():
    for a in (['CA'] * 3):
        yield a
    for b in (['FL'] * 2):
        yield b

def expected_vals_with_markers():
    expected = list()
    expected.append(('start_CA'))
    for c in (['CA'] * 3):
        expected.append(c)
    expected.append(('stop_CA'))
    expected.append(('start_FL'))
    for c in (['FL'] * 2):
        expected.append(c)
    expected.append(('stop_FL'))
    return expected

def expected_vals():
    expected = list()
    for c in (['CA'] * 3):
        expected.append(c)
    for c in (['FL'] * 2):
        expected.append(c)
    return expected

def test_fixtures():
    assert list(vals()) == expected_vals()

class context_marker():
    def __init__(self, val, out):
        self.val = val
        self.out = out

    def __enter__(self):
        print(f'start_{self.val}', file=self.out)
        return self

    def __exit__(self, execption, value, traceback):
        print(f'stop_{self.val}', file=self.out)
        return False

def test_context_marker():
    expected = ['start_z', 'working', 'stop_z']
    with io.StringIO() as buf:
        with context_marker('z', buf) as b:
            print('working', file=buf)

        buf.seek(0)
        s = buf.read().rstrip()
        assert s.split('\n') == expected

class scoped_iterator():
    def __init__(self, iterator, dispatch_table):
        self.iter = more_itertools.peekable(iterator)
        self.scope = None
        self.scope_dispatch = dispatch_table
        self.sentinel = '__sentinel__'

    def __iter__(self):
        return self

    def __next__(self):
        i = self.iter.peek(self.sentinel)
        if i == self.sentinel:
            # end of iteration stream
            if self.scope is not None:
                self.scope.__exit__(None, None, None)
                self.scope = self.scope_key = None
        elif self.scope is None:
            # start of new scope
            if i in self.scope_dispatch:
                self.scope_key = i
                self.scope = self.scope_dispatch[self.scope_key](self.scope_key)
                self.scope.__enter__()
        elif i != self.scope_key and i in self.scope_dispatch:
            # change in scope
            self.scope.__exit__(None, None, None)
            self.scope_key = i
            self.scope = self.scope_dispatch[self.scope_key](self.scope_key)
            self.scope.__enter__()

        return next(self.iter)

def test_normal_marker():
    with io.StringIO() as buf:
        def ca_scope_factory(marker):
            return context_marker(marker, buf)
        def fl_scope_factory(marker):
            return context_marker(marker, buf)

        dispatch_table = { 'CA': ca_scope_factory,
                           'FL': fl_scope_factory }

        it = scoped_iterator(vals(), dispatch_table)
        for i in it:
            print(i, file=buf)

        buf.seek(0)
        s = buf.read().rstrip()
        assert s.split('\n') == expected_vals_with_markers()
