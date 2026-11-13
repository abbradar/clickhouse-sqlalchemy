import warnings

from sqlalchemy import Column, func, text
from sqlalchemy.engine.interfaces import CacheStats

from clickhouse_sqlalchemy import types, engines, select, Table
from clickhouse_sqlalchemy.ext.clauses import Lambda
from tests.testcase import CompilationTestCase, NativeSessionTestCase


class CacheKeyTestCase(CompilationTestCase):
    def setUp(self):
        super().setUp()
        self.table = Table(
            't1', self.metadata(),
            Column('x', types.Int32, primary_key=True),
            Column('y', types.Array(types.Int32)),
            engines.Memory()
        )

    def _key(self, query):
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            key = query._generate_cache_key()
        return None if key is None else key.key

    def test_clauses_change_the_key(self):
        t = self.table
        query = select(t.c.x).group_by(t.c.x)
        keys = [
            self._key(query),
            self._key(query.final()),
            self._key(query.sample(0.1)),
            self._key(query.with_cube()),
            self._key(query.with_rollup()),
            self._key(query.with_totals()),
            self._key(query.limit_by([t.c.x], limit=1)),
            self._key(query.limit_by([t.c.y], limit=1)),
            self._key(query.array_join(t.c.y)),
            self._key(query.left_array_join(t.c.y)),
        ]
        self.assertNotIn(None, keys)
        self.assertEqual(len(set(keys)), len(keys))

    def test_bound_values_share_the_key(self):
        t = self.table
        self.assertEqual(
            self._key(select(t.c.x).sample(0.1)),
            self._key(select(t.c.x).sample(0.2))
        )
        self.assertEqual(
            self._key(select(t.c.x).limit_by([t.c.x], limit=1)),
            self._key(select(t.c.x).limit_by([t.c.x], limit=2))
        )

    def test_query_clauses_change_the_key(self):
        t = self.table
        query = self.session.query(t.c.x).group_by(t.c.x)
        keys = [
            self._key(query._statement_20()),
            self._key(query.final()._statement_20()),
            self._key(query.sample(0.1)._statement_20()),
            self._key(query.with_totals()._statement_20()),
            self._key(query.limit_by([t.c.x], limit=1)._statement_20()),
        ]
        self.assertNotIn(None, keys)
        self.assertEqual(len(set(keys)), len(keys))

    def test_lambda_is_not_cached(self):
        query = select(
            func.arrayFilter(Lambda(lambda x: x > 1), self.table.c.y)
        )
        self.assertIsNone(self._key(query))


class CachedExecutionTestCase(NativeSessionTestCase):
    def test_final_is_not_shared_through_the_cache(self):
        table = Table(
            't_cached_final', self.metadata(),
            Column('x', types.Int32, primary_key=True),
            engines.ReplacingMergeTree(order_by=('x', ))
        )

        with self.create_table(table):
            self.session.execute(text('SYSTEM STOP MERGES t_cached_final'))
            self.session.execute(table.insert(), [{'x': 1}])
            self.session.execute(table.insert(), [{'x': 1}])

            query = select(func.count()).select_from(table)
            results = [
                self.session.execute(q)
                for q in (query, query, query.final(), query.final())
            ]

            self.assertEqual([rv.scalar() for rv in results], [2, 2, 1, 1])
            self.assertEqual(
                [rv.context.cache_hit for rv in results[1::2]],
                [CacheStats.CACHE_HIT, CacheStats.CACHE_HIT]
            )
