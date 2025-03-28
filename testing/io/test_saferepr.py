from _pytest._io.saferepr import DEFAULT_REPR_MAX_SIZE
from _pytest._io.saferepr import saferepr
from _pytest._io.saferepr import saferepr_unlimited
import pytest


def test_simple_repr():
    assert saferepr(1) == "1"
    assert saferepr(None) == "None"


def test_maxsize():
    s = saferepr("x" * 50, maxsize=25)
    assert len(s) == 25
    expected = repr("x" * 10 + "..." + "x" * 10)
    assert s == expected


def test_no_maxsize():
    text = "x" * DEFAULT_REPR_MAX_SIZE * 10
    s = saferepr(text, maxsize=None)
    expected = repr(text)
    assert s == expected


def test_maxsize_error_on_instance():
    class A:
        def __repr__(self):
            raise ValueError("...")

    s = saferepr(("*" * 50, A()), maxsize=25)
    assert len(s) == 25
    assert s[0] == "(" and s[-1] == ")"


def test_exceptions() -> None:
    class BrokenRepr:
        def __init__(self, ex):
            self.ex = ex

        def __repr__(self):
            raise self.ex

    class BrokenReprException(Exception):
        __str__ = None  # type: ignore[assignment]
        __repr__ = None  # type: ignore[assignment]

    assert "Exception" in saferepr(BrokenRepr(Exception("broken")))
    s = saferepr(BrokenReprException("really broken"))
    assert "TypeError" in s
    assert "TypeError" in saferepr(BrokenRepr("string"))

    none = None
    try:
        none()  # type: ignore[misc]
    except BaseException as exc:
        exp_exc = repr(exc)
    obj = BrokenRepr(BrokenReprException("omg even worse"))
    s2 = saferepr(obj)
    assert s2 == (
        f"<[unpresentable exception ({exp_exc!s}) raised in repr()] BrokenRepr object at 0x{id(obj):x}>"
    )


def test_baseexception():
    """Test saferepr() with BaseExceptions, which includes pytest outcomes."""

    class RaisingOnStrRepr(BaseException):
        def __init__(self, exc_types):
            self.exc_types = exc_types

        def raise_exc(self, *args):
            try:
                self.exc_type = self.exc_types.pop(0)
            except IndexError:
                pass
            if hasattr(self.exc_type, "__call__"):
                raise self.exc_type(*args)
            raise self.exc_type

        def __str__(self):
            self.raise_exc("__str__")

        def __repr__(self):
            self.raise_exc("__repr__")

    class BrokenObj:
        def __init__(self, exc):
            self.exc = exc

        def __repr__(self):
            raise self.exc

        __str__ = __repr__

    baseexc_str = BaseException("__str__")
    obj = BrokenObj(RaisingOnStrRepr([BaseException]))
    assert saferepr(obj) == (
        f"<[unpresentable exception ({baseexc_str!r}) "
        f"raised in repr()] BrokenObj object at 0x{id(obj):x}>"
    )
    obj = BrokenObj(RaisingOnStrRepr([RaisingOnStrRepr([BaseException])]))
    assert saferepr(obj) == (
        f"<[{baseexc_str!r} raised in repr()] BrokenObj object at 0x{id(obj):x}>"
    )

    with pytest.raises(KeyboardInterrupt):
        saferepr(BrokenObj(KeyboardInterrupt()))

    with pytest.raises(SystemExit):
        saferepr(BrokenObj(SystemExit()))

    with pytest.raises(KeyboardInterrupt):
        saferepr(BrokenObj(RaisingOnStrRepr([KeyboardInterrupt])))

    with pytest.raises(SystemExit):
        saferepr(BrokenObj(RaisingOnStrRepr([SystemExit])))

    with pytest.raises(KeyboardInterrupt):
        print(saferepr(BrokenObj(RaisingOnStrRepr([BaseException, KeyboardInterrupt]))))

    with pytest.raises(SystemExit):
        saferepr(BrokenObj(RaisingOnStrRepr([BaseException, SystemExit])))


def test_buggy_builtin_repr():
    # Simulate a case where a repr for a builtin raises.
    # reprlib dispatches by type name, so use "int".

    class int:
        def __repr__(self):
            raise ValueError("Buggy repr!")

    assert "Buggy" in saferepr(int())


def test_big_repr():
    from _pytest._io.saferepr import SafeRepr

    assert len(saferepr(range(1000))) <= len("[" + SafeRepr(0).maxlist * "1000" + "]")


def test_repr_on_newstyle() -> None:
    class Function:
        def __repr__(self):
            return "<%s>" % (self.name)  # type: ignore[attr-defined]

    assert saferepr(Function())


def test_unicode():
    val = "£€"
    reprval = "'£€'"
    assert saferepr(val) == reprval


def test_broken_getattribute():
    """saferepr() can create proper representations of classes with
    broken __getattribute__ (#7145)
    """

    class SomeClass:
        def __getattribute__(self, attr):
            raise RuntimeError

        def __repr__(self):
            raise RuntimeError

    assert saferepr(SomeClass()).startswith(
        "<[RuntimeError() raised in repr()] SomeClass object at 0x"
    )


def test_saferepr_unlimited():
    dict5 = {f"v{i}": i for i in range(5)}
    assert saferepr_unlimited(dict5) == "{'v0': 0, 'v1': 1, 'v2': 2, 'v3': 3, 'v4': 4}"

    dict_long = {f"v{i}": i for i in range(1_000)}
    r = saferepr_unlimited(dict_long)
    assert "..." not in r
    assert "\n" not in r


def test_saferepr_unlimited_exc():
    class A:
        def __repr__(self):
            raise ValueError(42)

    assert saferepr_unlimited(A()).startswith(
        "<[ValueError(42) raised in repr()] A object at 0x"
    )
