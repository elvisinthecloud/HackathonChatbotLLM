"""Source-owned applicability constraints; quotation is grounding, not entailment.

Semantic predicates require the model's interpretation. Only explicit elapsed
wait reports have a narrow deterministic check; unknown time fails closed.
"""
import re


def validate_metadata(content, descriptors):
    if not isinstance(descriptors, list):
        raise ValueError('Invalid section conditions')
    for d in descriptors:
        if not isinstance(d, dict) or set(d) not in ({'section','condition_quote','kind'}, {'section','condition_quote','kind','minimum_minutes','relation'}):
            raise ValueError('Invalid section condition fields')
        if not all(isinstance(d[k], str) and d[k] for k in ('section','condition_quote','kind')):
            raise ValueError('Invalid section condition text')
        if d['section'] not in re.findall(r'^#{1,6}\s+(.+)$', content, re.M) or d['condition_quote'] not in content:
            raise ValueError('Section condition not grounded in source')
        if d['kind'] == 'elapsed_wait':
            if set(d) != {'section','condition_quote','kind','minimum_minutes','relation'} or type(d['minimum_minutes']) is not int or d['minimum_minutes'] <= 0 or d['relation'] not in ('before','after'):
                raise ValueError('Invalid elapsed wait condition')
            if not re.search(r'\b' + str(d['minimum_minutes']) + r'\s+minutes?\b', content, re.I):
                raise ValueError('Wait threshold not grounded in source')
        elif d['kind'] != 'semantic' or len(d) != 3:
            raise ValueError('Unknown condition kind')


def for_unit(source, section, quote):
    metadata = source.get('metadata', source.get('article_metadata', {}))
    reviewed = metadata.get('section_conditions', source.get('section_conditions', []))
    result = [dict(d) for d in reviewed if d['section'] == section]
    # Unknown sources retain explicit conditional headings and inline predicates.
    # This does not claim to extract every natural-language condition.
    if not result and re.search(r'\b(if|after|before|when|unless|unsure|need|still)\b', section, re.I):
        result.append({'section':section,'condition_quote':section,'kind':'semantic'})
    clean = re.sub(r'^\s*(?:\d+[.)]|[-*+])\s*', '', quote)
    match = re.match(r'(?:If|After|Before|When|Unless)\b[^,\n]*[,]', clean, re.I)
    if match:
        # This is a conditional instruction, not a claim that its prerequisite
        # has already happened. Keep its full wording in the rendered unit.
        result.append({'section':section,'condition_quote':match.group(0).rstrip(','),'kind':'instruction'})
    return result


_DURATION = re.compile(r'\b(?P<n>\d+(?:\.\d+)?|an?|one|sixty)\s*(?P<unit>minutes?|mins?|hours?|hrs?)\b', re.I)


def _elapsed(text):
    """Bind an exact duration directly to an affirmative first-person wait."""
    text = re.sub(r'(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])', ' ', text)
    values = []
    report = re.compile(r"\bI(?:\s+(?:have|already)|'ve|’ve)?\s+(?:already\s+)?(?:waited|have been waiting)\s+(?:for\s+)?", re.I)
    for sentence in re.findall(r'[^.!?;\n]+[.!?;]?', text):
        if sentence.rstrip().endswith('?') or re.search(r'[\"“”]', sentence):
            continue
        for match in report.finditer(sentence):
            # Leading hypotheticals scope over the whole reported action. A
            # later failed-outcome clause does not negate the elapsed wait.
            if re.search(r'\b(?:if|would|could|should|will|might|not|never|maybe|unsure|unknown|perhaps|said|say|says|told|wrote|quote|quoted)\b', sentence[:match.start()], re.I):
                continue
            duration = _DURATION.match(sentence, match.end())
            if duration is None:
                continue
            raw = duration['n'].lower()
            number = {'a':1,'an':1,'one':1,'sixty':60}.get(raw)
            if number is None: number = float(raw)
            values.append(number * (60 if duration['unit'].lower().startswith(('hour','hr')) else 1))
    return values[-1] if values else None


def _explicit_before(text):
    """A narrow affirmative relation report, not a general intent classifier."""
    for sentence in re.findall(r'[^.!?;\n]+[.!?;]?', text):
        if sentence.rstrip().endswith('?') or re.search(r'[\"“”]', sentence) or re.search(r"\b(?:if|not|don.t|would|could|might|maybe|unsure|said|say|says|told|wrote|quote|quoted)\b", sentence, re.I):
            continue
        if re.search(r"\bI\s+(?:need|want)\s+access\s+before\s+the\s+wait\s+ends\b", sentence, re.I):
            return True
    return False


def validate(conditions, claim, current_user, active_quotes=()):
    """Return an error code or None. Caller supplies only non-superseded speech.

    Current explicit reports override historical reports. Temporal basis must
    itself report elapsed time; quoting a convenient unrelated user fragment
    cannot justify a branch. Semantic predicates remain a model responsibility.
    """
    conditions=[condition for condition in conditions if condition['kind']!='instruction']
    if not conditions: return None
    condition_quote, basis = claim.get('condition_quote'), claim.get('user_basis')
    if not condition_quote or not basis: return 'missing_condition_basis'
    if not any(condition_quote in d['condition_quote'] or d['condition_quote'] in condition_quote for d in conditions):
        return 'unidentified_source_condition'
    speech = [current_user, *active_quotes]
    if not isinstance(basis, str) or not any(basis in s for s in speech): return 'invented_applicability'
    basis_contexts = [sentence for s in speech for sentence in re.findall(r'[^.!?;\n]+[.!?;]?', s) if basis in sentence]
    for d in conditions:
        if d['kind'] != 'elapsed_wait': continue
        elapsed = _elapsed(current_user)
        # A current negation/correction cannot be repaired with an old positive.
        if elapsed is None and re.search(r'\b(?:wait|waited|waiting)\b', current_user, re.I) and re.search(r'\b(?:not|never|haven.t|didn.t|actually|correction)\b', current_user, re.I):
            return 'unknown_elapsed_wait'
        if elapsed is None:
            elapsed = next((v for s in reversed(list(active_quotes)) if (v := _elapsed(s)) is not None), None)
        basis_elapsed = _elapsed(basis)
        if d['relation'] == 'before' and _explicit_before(basis) and any(_explicit_before(s) for s in basis_contexts):
            if elapsed is not None and elapsed >= d['minimum_minutes']: return 'contradicted_elapsed_wait'
            continue
        if elapsed is None or basis_elapsed is None or not any(_elapsed(s) == basis_elapsed for s in basis_contexts): return 'unknown_elapsed_wait'
        matches = lambda n: n < d['minimum_minutes'] if d['relation'] == 'before' else n >= d['minimum_minutes']
        if not matches(elapsed) or not matches(basis_elapsed): return 'contradicted_elapsed_wait'
    return None
