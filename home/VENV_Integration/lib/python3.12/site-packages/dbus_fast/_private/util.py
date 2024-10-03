import ast
import inspect
from typing import Any, List, Tuple, Union

from ..signature import SignatureTree, Variant, get_signature_tree


def signature_contains_type(
    signature: Union[str, SignatureTree], body: List[Any], token: str
) -> bool:
    """For a given signature and body, check to see if it contains any members
    with the given token"""
    if type(signature) is str:
        signature = get_signature_tree(signature)

    queue = []
    contains_variants = False
    for st in signature.types:
        queue.append(st)

    while True:
        if not queue:
            break
        st = queue.pop()
        if st.token == token:
            return True
        elif st.token == "v":
            contains_variants = True
        queue.extend(st.children)

    if not contains_variants:
        return False

    for member in body:
        queue.append(member)

    while True:
        if not queue:
            return False
        member = queue.pop()
        if type(member) is Variant and signature_contains_type(
            member.signature, [member.value], token
        ):
            return True
        elif type(member) is list:
            queue.extend(member)
        elif type(member) is dict:
            queue.extend(member.values())


def replace_fds_with_idx(
    signature: Union[str, SignatureTree], body: List[Any]
) -> Tuple[List[Any], List[int]]:
    """Take the high level body format and convert it into the low level body
    format. Type 'h' refers directly to the fd in the body. Replace that with
    an index and return the corresponding list of unix fds that can be set on
    the Message"""
    if type(signature) is str:
        signature = get_signature_tree(signature)

    if not signature_contains_type(signature, body, "h"):
        return body, []

    unix_fds = []

    def _replace(fd):
        try:
            return unix_fds.index(fd)
        except ValueError:
            unix_fds.append(fd)
            return len(unix_fds) - 1

    _replace_fds(body, signature.types, _replace)

    return body, unix_fds


def replace_idx_with_fds(
    signature: Union[str, SignatureTree], body: List[Any], unix_fds: List[int]
) -> List[Any]:
    """Take the low level body format and return the high level body format.
    Type 'h' refers to an index in the unix_fds array. Replace those with the
    actual file descriptor or `None` if one does not exist."""
    if type(signature) is str:
        signature = get_signature_tree(signature)

    if not signature_contains_type(signature, body, "h"):
        return body

    def _replace(idx):
        try:
            return unix_fds[idx]
        except IndexError:
            return None

    _replace_fds(body, signature.types, _replace)

    return body


def parse_annotation(annotation: str) -> str:
    """
    Because of PEP 563, if `from __future__ import annotations` is used in code
    or on Python version >=3.10 where this is the default, return annotations
    from the `inspect` module will return annotations as "forward definitions".
    In this case, we must eval the result which we do only when given a string
    constant.
    """

    def raise_value_error():
        raise ValueError(
            f"service annotations must be a string constant (got {annotation})"
        )

    if not annotation or annotation is inspect.Signature.empty:
        return ""
    if type(annotation) is not str:
        raise_value_error()
    try:
        body = ast.parse(annotation).body
        if len(body) == 1 and type(body[0].value) is ast.Constant:
            if type(body[0].value.value) is not str:
                raise_value_error()
            return body[0].value.value
    except SyntaxError:
        pass

    return annotation


def _replace_fds(body_obj: List[Any], children, replace_fn):
    """Replace any type 'h' with the value returned by replace_fn() given the
    value of the fd field. This is used by the high level interfaces which
    allow type 'h' to be the fd directly instead of an index in an external
    array such as in the spec."""
    for index, st in enumerate(children):
        if not any(sig in st.signature for sig in "hv"):
            continue
        if st.signature == "h":
            body_obj[index] = replace_fn(body_obj[index])
        elif st.token == "a":
            if st.children[0].token == "{":
                _replace_fds(body_obj[index], st.children, replace_fn)
            else:
                for i, child in enumerate(body_obj[index]):
                    if st.signature == "ah":
                        body_obj[index][i] = replace_fn(child)
                    else:
                        _replace_fds([child], st.children, replace_fn)
        elif st.token in "(":
            _replace_fds(body_obj[index], st.children, replace_fn)
        elif st.token in "{":
            for key, value in list(body_obj.items()):
                body_obj.pop(key)
                if st.children[0].signature == "h":
                    key = replace_fn(key)
                if st.children[1].signature == "h":
                    value = replace_fn(value)
                else:
                    _replace_fds([value], [st.children[1]], replace_fn)
                body_obj[key] = value

        elif st.signature == "v":
            if body_obj[index].signature == "h":
                body_obj[index].value = replace_fn(body_obj[index].value)
            else:
                _replace_fds(
                    [body_obj[index].value], [body_obj[index].type], replace_fn
                )

        elif st.children:
            _replace_fds(body_obj[index], st.children, replace_fn)
