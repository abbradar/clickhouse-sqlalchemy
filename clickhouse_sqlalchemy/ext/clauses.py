from sqlalchemy import exc
from sqlalchemy.sql import type_api, roles
from sqlalchemy.sql.elements import (
    BindParameter,
    ClauseElement,
    ColumnElement,
    ClauseList
)
from sqlalchemy.sql.util import _offset_or_limit_clause
from sqlalchemy.sql.visitors import InternalTraversal, Visitable


class SampleParam(BindParameter):
    inherit_cache = True


def sample_clause(element):
    """Convert the given value to an "sample" clause.

    This handles incoming element to an expression; if
    an expression is already given, it is passed through.

    """
    if element is None:
        return None
    elif hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    elif isinstance(element, Visitable):
        return element
    else:
        return SampleParam(None, element, unique=True)


class LimitByClause(ClauseElement):
    _traverse_internals = [
        ('by_clauses', InternalTraversal.dp_clauseelement),
        ('offset', InternalTraversal.dp_clauseelement),
        ('limit', InternalTraversal.dp_clauseelement),
    ]

    def __init__(self, by_clauses, limit, offset):
        self.by_clauses = ClauseList(
            *by_clauses, _literal_as_text_role=roles.ByOfRole
        )
        self.offset = _offset_or_limit_clause(offset)
        self.limit = _offset_or_limit_clause(limit)

    def __bool__(self):
        return bool(self.by_clauses.clauses)


class Lambda(ColumnElement):
    """Represent a lambda function, ``Lambda(lambda x: 2 * x)``."""

    __visit_name__ = 'lambda'
    # The SQL comes from calling func, which a cache key cannot capture.
    inherit_cache = False

    def __init__(self, func):
        if not callable(func):
            raise exc.ArgumentError('func must be callable')

        self.type = type_api.NULLTYPE
        self.func = func


class ArrayJoin(ClauseList):
    __visit_name__ = 'array_join'
    inherit_cache = True


class LeftArrayJoin(ClauseList):
    __visit_name__ = 'left_array_join'
    inherit_cache = True
