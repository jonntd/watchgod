import logging
from time import sleep

from pytest_toolbox import mktree

import watchgod.main
from watchgod import AllWatcher, Change, DefaultWatcher, PythonWatcher, watch

tree = {
    'foo': {
        'bar.txt': 'bar',
        'spam.py': 'whatever',
        'spam.pyc': 'splosh',
        'recursive_dir': {
            'a.js': 'boom',
        },
        '.git': {
            'x': 'y',
        }
    }
}


def test_add(tmpdir):
    watcher = AllWatcher(str(tmpdir))
    changes = watcher.check()
    assert changes == set()

    sleep(0.01)
    tmpdir.join('foo.txt').write('foobar')

    changes = watcher.check()
    assert changes == {(Change.added, str(tmpdir.join('foo.txt')))}


def test_modify(tmpdir):
    mktree(tmpdir, tree)

    watcher = AllWatcher(str(tmpdir))
    assert watcher.check() == set()

    sleep(0.01)
    tmpdir.join('foo/bar.txt').write('foobar')

    assert watcher.check() == {(Change.modified, str(tmpdir.join('foo/bar.txt')))}


def test_delete(tmpdir):
    mktree(tmpdir, tree)

    watcher = AllWatcher(str(tmpdir))

    sleep(0.01)
    tmpdir.join('foo/bar.txt').remove()

    assert watcher.check() == {(Change.deleted, str(tmpdir.join('foo/bar.txt')))}


def test_ignore_file(tmpdir):
    mktree(tmpdir, tree)

    watcher = DefaultWatcher(str(tmpdir))

    sleep(0.01)
    tmpdir.join('foo/spam.pyc').write('foobar')

    assert watcher.check() == set()


def test_ignore_dir(tmpdir):
    mktree(tmpdir, tree)

    watcher = DefaultWatcher(str(tmpdir))

    sleep(0.01)
    tmpdir.join('foo/.git/abc').write('xxx')

    assert watcher.check() == set()


def test_python(tmpdir):
    mktree(tmpdir, tree)

    watcher = PythonWatcher(str(tmpdir))

    sleep(0.01)
    tmpdir.join('foo/spam.py').write('xxx')
    tmpdir.join('foo/bar.txt').write('xxx')

    assert watcher.check() == {(Change.modified, str(tmpdir.join('foo/spam.py')))}


def test_watch(mocker):
    class FakeWatcher:
        def __init__(self, path):
            self.results = [
                {'r2'},
                set(),
                {'r1'},
            ]

        def check(self):
            return self.results.pop()

    mocker.spy(watchgod.main, 'sleep')
    iter = watch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=1)
    assert next(iter) == {'r1'}
    assert next(iter) == {'r2'}
    assert watchgod.main.sleep.call_count == 2
    assert watchgod.main.sleep.call_args_list[0][0][0] > 0.001
    assert watchgod.main.sleep.call_args_list[1][0][0] > 0.001


def test_watch_keyboard_error():
    class FakeWatcher:
        def __init__(self, path):
            pass

        def check(self):
            raise KeyboardInterrupt()

    iter = watch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=1)
    assert list(iter) == []


def test_watch_min_sleep(mocker):
    class FakeWatcher:
        def __init__(self, path):
            pass

        def check(self):
            return {'r1'}

    mocker.spy(watchgod.main, 'sleep')
    mocker.spy(watchgod.main.logger, 'debug')
    iter = watch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=10)
    assert next(iter) == {'r1'}
    assert next(iter) == {'r1'}
    assert watchgod.main.sleep.call_count == 1
    assert watchgod.main.sleep.call_args[0][0] == 0.01
    assert watchgod.main.logger.debug.called is False


def test_watch_log(mocker, capsys):
    logging.basicConfig(level=logging.DEBUG)

    class FakeWatcher:
        def __init__(self, path):
            self.files = [1, 2, 3]

        def check(self):
            return {'r1'}

    mocker.spy(watchgod.main.logger, 'debug')
    iter = watch('xxx', watcher_cls=FakeWatcher, debounce=5, min_sleep=10)
    assert next(iter) == {'r1'}

    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'DEBUG:watchgod.main:time=0ms files=3 changes=1\n'
