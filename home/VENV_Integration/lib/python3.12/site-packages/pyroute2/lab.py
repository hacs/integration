import inspect

try:
    from unittest import mock
except ImportError:
    mock = None

registry = []
use_mock = False


class LAB_API:
    def __init__(self, *argv, **kwarg):
        super().__init__(*argv, **kwarg)
        if use_mock:
            if mock is None:
                # postpone ImportError
                #
                # unittest may not be available on embedded platforms,
                # but it is still used by IPRoute class; it is safe
                # to leave it in the minimal for now, just raise an
                # exception when being used
                #
                # Bug-Url: https://github.com/svinota/pyroute2/pull/1096
                raise ImportError('unittest.mock not available')
            registry.append(self)
            for name, method in inspect.getmembers(
                self, predicate=inspect.ismethod
            ):
                setattr(self, name, mock.MagicMock(name=name, wraps=method))
