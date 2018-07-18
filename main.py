import sys
import io
import uuid
import pytest
import itertools
import more_itertools

MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit('python %s.%s or later required' % MIN_PYTHON)

class ContextMarker():
    def __init__(self, val, out):
        self.val = val
        self.out = out

    def __enter__(self):
        self.out.append(f'start_{self.val}')
        return self

    def __exit__(self, exception, value, traceback):
        self.out.append(f'stop_{self.val}')
        return False

def test_context_marker():
    expected = ['start_z', 'working', 'stop_z']
    buf = []
    with ContextMarker('z', buf) as b:
        buf.append('working')

    assert buf == expected

class ScopedIterator():
    def __init__(self, iterator, dispatch_table):
        self.iter = more_itertools.peekable(iterator)
        self.scope = self.scope_key = None
        self.scope_dispatch = dispatch_table
        self.sentinel = str(uuid.uuid4())

    def __iter__(self):
        return self

    def __next__(self):
        i = self.iter.peek(self.sentinel)
        if i == self.sentinel:
            # end of iteration stream
            if self.scope is not None:
                self.scope.__exit__(None, None, None)
                self.scope = self.scope_key = None
        elif self.scope is None and i in self.scope_dispatch:
            # start of new scope
            self.scope_key = i
            self.scope = self.scope_dispatch[self.scope_key](self.scope_key)
            self.scope.__enter__()
        elif i != self.scope_key and i in self.scope_dispatch:
            # change in scope
            self.scope.__exit__(None, None, None)
            self.scope_key = i
            self.scope = self.scope_dispatch[self.scope_key](self.scope_key)
            self.scope.__enter__()
        elif i != self.scope_key and self.scope_key is not None and i not in self.scope_dispatch:
            # stop scope, but don't start a new one
            self.scope.__exit__(None, None, None)
            self.scope = self.scope_key = None

        return next(self.iter)

from collections import namedtuple
Fixture = namedtuple('Fixture', 'buf iterator expected dispatch_table')

def empty_stream():
    return Fixture(list(), [], [], {})

def typical_stream():
    'typical stream of sorted values, each value with an entry in the dispatch_table.'
    def expected_vals():
        return list(itertools.chain('A' * 3, 'B' * 2))

    def vals_iter():
        for v in expected_vals():
            yield v

    def expected_vals_with_markers():
        return list(
            itertools.chain.from_iterable((('start_A',),
                                           'A' * 3,
                                           ('stop_A', 'start_B'),
                                           'B' * 2,
                                           ('stop_B',))))

    buf = list()
    def a_scope_factory(marker):
        return ContextMarker(marker, buf)
    def b_scope_factory(marker):
        return ContextMarker(marker, buf)

    dispatch_table = { 'A': a_scope_factory,
                       'B': b_scope_factory }
    return Fixture(buf, vals_iter(), expected_vals_with_markers(), dispatch_table)

def partial_coverage():
    'a stream where the dispatch_table does not cover all elements'
    def expected_vals():
        return list(itertools.chain('B' * 1, 'C' * 3, 'D' * 2, 'E' * 1, 'F' * 2))

    def vals_iter():
        for v in expected_vals():
            yield v

    def expected_vals_with_markers():
        return list(
            itertools.chain.from_iterable((('B',
                                            'start_C',),
                                           'C' * 3,
                                           ('stop_C',),
                                           'D' * 2,
                                           ('start_E', 'E', 'stop_E'),
                                           'F' * 2)))

    buf = list()
    def c_scope_factory(marker):
        return ContextMarker(marker, buf)
    def e_scope_factory(marker):
        return ContextMarker(marker, buf)

    dispatch_table = { 'C': c_scope_factory,
                       'E': e_scope_factory }
    return Fixture(buf, vals_iter(), expected_vals_with_markers(), dispatch_table)

class _test_():
    'simple class to test out dispatch'
    def __init__(self, val):
        self._val = val

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, new_val):
        self._val = new_val

    def __str__(self):
        return str(self._val)

def dispatch_by_class_with_str():
    'a stream that uses objects defining __str__ as the key to dispatch on.'

    def expected_vals():
        return list((_test_(42), _test_(64)))

    def vals_iter():
        for v in expected_vals():
            # use the printed representation of the class instance for scoping.
            yield str(v)

    def expected_vals_with_markers():
        return list(('start_42', '42', 'stop_42', 'start_64', '64', 'stop_64'))

    buf = list()
    def scope_factory_42(marker):
        return ContextMarker(marker, buf)
    def scope_factory_64(marker):
        return ContextMarker(marker, buf)

    dispatch_table = { '42': scope_factory_42,
                       '64': scope_factory_64 }
    return Fixture(buf, vals_iter(), expected_vals_with_markers(), dispatch_table)


@pytest.fixture
def fixtures():
    return list((
        empty_stream(),
        typical_stream(),
        dispatch_by_class_with_str(),
        partial_coverage()
    ))

def test_by_fixtures(fixtures):
    for fix in fixtures:
        for i in ScopedIterator(fix.iterator, fix.dispatch_table):
            fix.buf.append(i)

        assert fix.buf == fix.expected
