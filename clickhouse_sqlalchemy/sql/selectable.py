from sqlalchemy.sql.base import _generative
from sqlalchemy.sql.selectable import (
    Select as StandardSelect,
)
from sqlalchemy.sql.visitors import InternalTraversal

from ..ext.clauses import (
    ArrayJoin,
    LeftArrayJoin,
    LimitByClause,
    sample_clause,
)


__all__ = ('Select', 'select')


_clickhouse_traverse_internals = [
    ('_with_cube', InternalTraversal.dp_boolean),
    ('_with_rollup', InternalTraversal.dp_boolean),
    ('_with_totals', InternalTraversal.dp_boolean),
    ('_final_clause', InternalTraversal.dp_boolean),
    ('_sample_clause', InternalTraversal.dp_clauseelement),
    ('_limit_by_clause', InternalTraversal.dp_clauseelement),
    ('_array_join', InternalTraversal.dp_clauseelement),
]


class Select(StandardSelect):
    _traverse_internals = (
        StandardSelect._traverse_internals + _clickhouse_traverse_internals
    )
    _cache_key_traversal = (
        StandardSelect._cache_key_traversal + _clickhouse_traverse_internals
    )

    _with_cube = False
    _with_rollup = False
    _with_totals = False
    _final_clause = None
    _sample_clause = None
    _limit_by_clause = None
    _array_join = None

    @_generative
    def with_cube(self):
        self._with_cube = True
        return self

    @_generative
    def with_rollup(self):
        self._with_rollup = True
        return self

    @_generative
    def with_totals(self):
        self._with_totals = True
        return self

    @_generative
    def final(self):
        self._final_clause = True
        return self

    @_generative
    def sample(self, sample):
        self._sample_clause = sample_clause(sample)
        return self

    @_generative
    def limit_by(self, by_clauses, limit, offset=None):
        self._limit_by_clause = LimitByClause(by_clauses, limit, offset)
        return self

    def _add_array_join(self, columns, left):
        join_type = ArrayJoin if not left else LeftArrayJoin
        self._array_join = join_type(*columns)

    @_generative
    def array_join(self, *columns, **kwargs):
        left = kwargs.get("left", False)
        self._add_array_join(columns, left=left)
        return self

    @_generative
    def left_array_join(self, *columns):
        self._add_array_join(columns, left=True)
        return self

    def join(self, right, onclause=None, isouter=False, full=False, type=None,
             strictness=None, distribution=None):
        flags = tuple({
            'full': full,
            'type': type,
            'strictness': strictness,
            'distribution': distribution
        }.items())
        return super().join(right, onclause=onclause, isouter=isouter,
                            full=flags)


select = Select
