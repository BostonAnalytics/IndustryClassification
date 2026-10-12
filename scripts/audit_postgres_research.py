"""Read-only local PostgreSQL metadata/coverage audit; credentials never exported."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import dotenv_values
import psycopg2

OUT = Path(__file__).resolve().parents[1] / 'docs/research'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True, type=Path)
    parser.add_argument('--mode', choices=['schema', 'coverage', 'text-sample'], default='schema')
    args = parser.parse_args()
    env = dotenv_values(args.env_file)
    prefix = next((p for p in ['LOCAL_DB_', 'DB_']
                   if str(env.get(p + 'HOST', '')).strip().lower() in {'localhost', '127.0.0.1', '::1'}), None)
    if not prefix:
        raise SystemExit('No explicitly loopback PostgreSQL configuration found')
    config = {k: env.get(prefix + v) for k, v in
              [('host', 'HOST'), ('port', 'PORT'), ('dbname', 'NAME'), ('user', 'USER'), ('password', 'PASSWORD')]}
    conn = psycopg2.connect(**config, connect_timeout=10,
                           application_name='industry_research_read_only',
                           options='-c default_transaction_read_only=on -c statement_timeout=600000 -c lock_timeout=3000 -c timezone=UTC')
    conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
    result = {'audit_started_utc': datetime.now(timezone.utc).isoformat(),
              'target': 'loopback PostgreSQL', 'mode': args.mode}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_setting('transaction_read_only'), current_setting('transaction_isolation'), transaction_timestamp()")
            result['transaction'] = list(cur.fetchone())
            assert result['transaction'][0] == 'on'
            if args.mode == 'schema':
                cur.execute("SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('met_career_match_jobposting', 'met_career_match_rawjobsourcerecord', 'met_career_match_jobpostingrefinement', 'met_career_match_jobskillprofile', 'met_career_match_jobpostingskill', 'met_career_match_naicsreference') ORDER BY table_schema, table_name, ordinal_position")
                result['columns'] = [list(r) for r in cur.fetchall()]
                cur.execute("SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables WHERE relname ILIKE '%job%' OR relname ILIKE '%posting%' ORDER BY n_live_tup DESC LIMIT 25")
                result['table_estimates'] = [list(r) for r in cur.fetchall()]
                cur.execute("SELECT indexname,indexdef FROM pg_indexes WHERE tablename='met_career_match_jobposting'")
                result['indexes'] = [list(r) for r in cur.fetchall()]
            elif args.mode == 'text-sample':
                cur.execute("""SELECT EXTRACT(YEAR FROM posted_at AT TIME ZONE 'UTC')::integer AS year,
                    COUNT(*) AS sampled_records,
                    COUNT(*) FILTER (WHERE LOWER(BTRIM(COALESCE(description,''))) NOT IN ('','unknown','none','null','nan','unclassified')) AS text_nonplaceholder,
                    COUNT(*) FILTER (WHERE LENGTH(BTRIM(description)) >= 200) AS text_200_chars,
                    COUNT(*) FILTER (WHERE naics_code ~ '^[0-9]{4,6}$') AS naics_4_to_6_digits,
                    COUNT(*) FILTER (WHERE countryiso='US') AS country_us
                    FROM public.met_career_match_jobposting TABLESAMPLE SYSTEM (0.2) REPEATABLE (2026)
                    WHERE posted_at >= '2024-01-01 00:00:00+00'::timestamptz AND posted_at < '2027-01-01 00:00:00+00'::timestamptz
                    GROUP BY 1 ORDER BY 1""")
                result['sample'] = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
                assert all(r['year'] in (2024, 2025, 2026) for r in result['sample'])
                result['interpretation'] = 'Physical-block 0.2 percent SYSTEM sample; descriptive feasibility only. Not exact coverage, not an independent annotation benchmark; clustering may bias these proportions. Separate read-only transaction from full coverage audit.'
            else:
                sql = """SELECT date_trunc('month', posted_at AT TIME ZONE 'UTC')::text AS month,
                    source, countryiso, COUNT(*) AS records,
                    COUNT(*) FILTER (WHERE is_duplicate) AS duplicate_flagged,
                    COUNT(*) FILTER (WHERE is_cold_storage) AS cold_storage,
                    COUNT(*) FILTER (WHERE naics_reference_id IS NOT NULL) AS naics_linked,
                    COUNT(*) FILTER (WHERE soc_reference_id IS NOT NULL) AS soc_linked
                    FROM public.met_career_match_jobposting
                    GROUP BY 1,2,3 ORDER BY 1,2,3"""
                cur.execute('EXPLAIN (FORMAT JSON) ' + sql)
                result['plan'] = cur.fetchone()[0]
                print('Read-only coverage plan obtained; scanning date/source/country metadata', flush=True)
                cur.execute(sql)
                result['coverage'] = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
                cur.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE posted_at IS NULL) AS undated, COUNT(*) FILTER (WHERE posted_at > transaction_timestamp()) AS future_dated, MIN(posted_at)::text, MAX(posted_at)::text, COUNT(*) FILTER (WHERE posted_at < '1900-01-01'::timestamptz) AS before_1900 FROM public.met_career_match_jobposting")
                result['reconciliation'] = list(cur.fetchone())
                assert sum(r['records'] for r in result['coverage']) == result['reconciliation'][0]
            result['audit_finished_utc'] = datetime.now(timezone.utc).isoformat()
        conn.rollback()
    finally:
        conn.close()
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / f'postgres-{args.mode}.json'
    destination.write_text(json.dumps(result, indent=2, default=str) + '\n', encoding='utf-8')
    print('POSTGRES READ-ONLY AUDIT VERIFIED', destination)


if __name__ == '__main__':
    main()
