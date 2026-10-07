"""Run an explicit maintained list of offline server guards, never live acceptance."""
import argparse
import json
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tests'),str(ROOT/'scripts')]

MAINTAINED_MODULES=(
    'test_compact_interpretation',
    'test_compact_reply',
    'test_compact_relevance',
    'test_article_registry',
    'test_architecture_operations',
    'test_session_contracts',
    'test_evidence_conditions',
    'test_dialogue_state_revision',
    'test_sessions',
    'test_private_config',
    'test_release_packaging',
    'test_interpretation_context_contract',
    'test_context_gap_fixes',
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'output/test-suite-refresh/results.json')
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromNames(MAINTAINED_MODULES)
    def ids(tests):
        for case in tests:
            if isinstance(case,unittest.TestSuite):yield from ids(case)
            else:yield case.id()
    test_ids=list(ids(suite))
    started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    report={
        'status':'passed' if result.wasSuccessful() else 'failed',
        'execution_kind':'offline_maintained_server_guards',
        'modules':list(MAINTAINED_MODULES),
        'excluded_modules':sorted(path.stem for path in (ROOT/'tests').glob('test_*.py')
                                  if path.stem not in MAINTAINED_MODULES),
        'exclusion_reason':'Legacy scripted conversation fixtures and mixed helper modules are outside this maintained runner pending a scoped refresh; files are preserved.',
        'tests_run':result.testsRun,'failures':[{'test':t.id(),'details':e} for t,e in result.failures],
        'errors':[{'test':t.id(),'details':e} for t,e in result.errors],
        'skipped':[{'test':t.id(),'reason':reason} for t,reason in result.skipped],
        'duration_seconds':round(time.monotonic()-started,3),'test_ids':test_ids,
        'live_model_conversations':0,
        'live_acceptance_turns':0,
        'limits':['These local guards use fixtures and service doubles; they do not evaluate live model choices.',
                  'Passing guards do not establish conversation usefulness, semantic recall, live retrieval quality or latency.',
                  'Broad unittest discovery includes unmaintained legacy fixtures and is not the maintained current-path check.',
                  'Frontend checks and disposable PostgreSQL contracts run separately.'],
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print('Results: '+str(args.report))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
