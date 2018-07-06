import io
import pytest


def vals():
    for a in (['a'] * 3):
        yield a
    for b in (['b'] * 2):
        yield b

def expected_vals():
    expected = list()
    expected.append(('start_a'))
    for c in (['a'] * 3):
        expected.append(c)
    expected.append(('stop_a'))
    expected.append(('start_b'))
    for c in (['b'] * 2):
        expected.append(c)
    expected.append(('stop_b'))
    return expected

def test_scoped_iteration():
    assert list(vals()) == expected_vals()

class context_marker():
    def __init__(self, val, out):
        self.val = val
        self.out = out

    def __enter__(self):
        print(f"start_{self.val}", file=self.out)
        return self

    def __exit__(self, execption, value, traceback):
        print(f"stop_{self.val}", file=self.out)
        return False

def test_context_marker():
    expected = ['start_z', 'working', 'stop_z']
    with io.StringIO() as buf:
        with context_marker('z', buf) as b:
            print('working', file=buf)

        
        buf.seek(0)
        s = buf.read().rstrip()
        assert s.split('\n') == expected
