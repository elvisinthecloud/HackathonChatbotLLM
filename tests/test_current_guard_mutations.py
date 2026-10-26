"""Focused mutation probes: current acceptance must fail if its target guard fails.

These run the same acceptance assertions against deliberately weakened local
functions. They establish test sensitivity, not live-model conversation quality.
"""
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import support  # Initializes the backend under isolated offline test settings.
import article_retrieval
import flexible_support as f
import test_architecture_acceptance as acceptance


@contextmanager
def mutation_transcripts(guard):
    start = len(acceptance.CONVERSATION_RUNS)
    try:
        yield
    finally:
        for transcript in acceptance.CONVERSATION_RUNS[start:]:
            transcript.update(execution_kind='offline_guard_mutation',
                              disabled_guard=guard, expected_outcome='acceptance_assertion_failed')


class CurrentGuardMutationTests(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_case_detects_disabled_decision_validation(self):
        case = acceptance.DialogueAcceptanceTests(
            'test_unknown_or_conflicting_course_scope_cannot_render_specific_steps')
        with mutation_transcripts('decision_validation'), patch.object(f, 'validate_decision', return_value=None), self.assertRaises(AssertionError):
            await case.test_unknown_or_conflicting_course_scope_cannot_render_specific_steps()
        # The mutated run reached the decision and leaked the selected procedure;
        # this would have been hidden by the old invalid interpretation fixture.
        transcript = acceptance.CONVERSATION_RUNS[-1]
        self.assertEqual(transcript['validation_outcomes'], acceptance.ACCEPTED_STAGES)
        self.assertEqual(transcript['source_ids'], ['MCELE-CSC-001'])

    async def test_unknown_method_case_detects_disabled_applicability_check(self):
        case = acceptance.DialogueAcceptanceTests(
            'test_unknown_method_cannot_render_condition_specific_procedure')
        with mutation_transcripts('source_applicability'), patch.object(article_retrieval, 'applicability_status',
                          return_value={'applicable': True, 'missing': [], 'conflicts': []}), \
             self.assertRaises(AssertionError):
            await case.test_unknown_method_cannot_render_condition_specific_procedure()
        # The separate renderer method guard may still prevent advice. The test
        # specifically detects that decision validation stopped rejecting it.
        self.assertEqual(acceptance.CONVERSATION_RUNS[-1]['validation_outcomes'],
                         acceptance.ACCEPTED_STAGES)

    async def test_retraction_case_detects_lost_supersession(self):
        case = acceptance.DialogueAcceptanceTests(
            'test_correction_retracts_completion_once_and_retains_unrelated_goal')
        reconcile = f.dialogue.reconcile
        def drop_supersession(memory, value, current):
            value = {**value, 'revisions': [{**revision, 'supersedes': []}
                                          for revision in value['revisions']]}
            return reconcile(memory, value, current)
        with mutation_transcripts('fact_supersession'), patch.object(f.dialogue, 'reconcile', side_effect=drop_supersession), \
             self.assertRaises(AssertionError):
            await case.test_correction_retracts_completion_once_and_retains_unrelated_goal()
        transcript = acceptance.CONVERSATION_RUNS[-1]
        self.assertEqual(transcript['validation_outcomes'], acceptance.ACCEPTED_STAGES)
        self.assertEqual(transcript['context']['conversation']['completed_quotes'],
                         ['I completed the password reset.'])

    def test_candidate_hash_case_detects_disabled_release_verification(self):
        case = acceptance.CorpusAcceptanceTests(
            'test_stale_candidate_hash_or_release_cannot_hydrate')
        case.setUp()
        with patch.object(article_retrieval, 'verify_candidate', return_value=True), \
             self.assertRaises(AssertionError):
            case.test_stale_candidate_hash_or_release_cannot_hydrate()

    def test_prompt_budget_case_detects_removed_input_bound(self):
        case = acceptance.PromptBudgetAcceptanceTests(
            'test_complete_messages_and_schema_fit_context_with_output_reserve')
        with patch.object(f, 'fit_payload', side_effect=lambda stage, prompt, payload, schema, num_ctx: payload), \
             self.assertRaises(AssertionError):
            case.test_complete_messages_and_schema_fit_context_with_output_reserve()
