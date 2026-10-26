"""Server-owned progress and extractive guidance; no service calls or stored source text."""
from copy import deepcopy
import json
import re


def normalized(text):
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def short_reply(text):
    return normalized(text) in {
        'yes', 'no', 'done', 'next', 'ready', 'i am ready', 'im ready',
        'i did that', 'already done', 'completed', 'not yet', 'okay', 'ok',
    }


def changed_error(text):
    return bool(re.search(
        r"\b(?:different|new|changed)\s+(?:error|message)|\b(?:error|message)\s+(?:has\s+)?changed\b"
        r"|\b(?:now|instead)\s+(?:it\s+)?(?:says|shows|displays)\b"
        r"|\bno longer\b.{0,70}\b(?:error|refused to connect)\b", text, re.I))


def new_issue(text):
    return bool(re.search(r"\b(?:new|different|another|separate)\s+(?:issue|problem|question)\b"
                          r"|\b(?:start over|change (?:the )?topic)\b", text, re.I))


def fresh_state(profile_id):
    return {'schema': 1, 'profile_id': profile_id, 'article_id': None,
            'step_index': 0, 'completed_steps': [], 'pending_question': None,
            'known_facts': {}, 'status': 'intake'}


def state_from(context, profile_id):
    state = context.get('troubleshooting', {})
    if (not isinstance(state, dict) or state.get('schema') != 1 or state.get('profile_id') != profile_id
            or not isinstance(state.get('known_facts'), dict) or not isinstance(state.get('completed_steps'), list)
            or type(state.get('step_index')) is not int or not 0 <= state['step_index'] <= 64
            or any(type(index) is not int or not 0 <= index < 64 for index in state['completed_steps'])):
        return fresh_state(profile_id)
    return deepcopy(state)


def source_units(chunks):
    """Preserve numbered steps, bullet facts and paragraphs with their citation indexes."""
    units = []
    seen = set()
    for citation, chunk in enumerate(chunks, 1):
        content = (chunk.get('content') or '').strip()
        section = None
        for block in re.split(r'\n\s*\n', content):
            block = block.strip()
            if block.startswith('#'):
                section = block.lstrip('#').strip()
                continue
            if not block:
                continue
            parts = re.split(r'(?m)^\s*(\d{1,2})\.\s+', block)
            records = []
            if len(parts) > 1:
                if parts[0].strip():
                    records.append(('note', None, parts[0].strip()))
                for index in range(1, len(parts), 2):
                    records.append(('step', int(parts[index]), parts[index+1].strip()))
            elif re.match(r'^[-*]\s+', block):
                records = [('note', None, line.strip()) for line in block.splitlines() if line.strip()]
            else:
                records = [('note', None, block)]
            for kind, number, text in records:
                key = (section, kind, number, text)
                if key in seen or not text:
                    continue
                seen.add(key)
                units.append({'id': f'u{len(units)}', 'kind': kind, 'number': number,
                              'text': text, 'citation': citation, 'section': section})
    return units


def steps_in(units):
    steps = [unit for unit in units if unit['kind'] == 'step']
    # Never present a partial retrieved procedure as its first step.
    if [unit['number'] for unit in steps] != list(range(1, len(steps)+1)):
        return []
    return steps


def render_unit(unit):
    prefix = f"{unit['number']}. " if unit['kind'] == 'step' else ''
    return f"{prefix}{unit['text']} [{unit['citation']}]"


def suggestions(state, answer):
    """Offer only replies that answer the question visible in this turn."""
    if not isinstance(answer, str):
        return []
    kind = state.get('pending_question')
    completion_prompts = (
        "Tell me when you've completed this step, or what is stopping you.",
        "Tell me when you've completed the current step, or what is stopping you.",
    )
    changed_error_reply = ['The error changed'] if (state.get('known_facts') or {}).get('reported_error') else []
    if kind == 'step_complete' and answer.endswith(completion_prompts):
        return ['Done', "I'm stuck"] + changed_error_reply
    binary_prompts = {
        'account_exists': ('Do you already have an MCeLE account?',),
        'outcome': ('Did that resolve the issue?',),
        'offer_steps': ('Would you like help finding a different course that awards RRC?',),
        'explanation': ('Would you like to return to the current step?', 'Would you like to return to checking the result?'),
        'csc_mcele_visible': ('Does CSC appear under MCeLE My Courses?',),
        'csc_moodle_visible': ('Do you now see CSC in Moodle My Courses with All selected?',),
    }
    if kind in binary_prompts and answer.endswith(binary_prompts[kind]):
        return ['Yes', 'No'] + (changed_error_reply if kind == 'outcome' else [])
    # Free-text clarifications keep their task/system choices only when that
    # exact server prompt is being shown, never after a greeting or source fact.
    if answer != state.get('question_text'):
        return []
    if kind == 'system' and 'MCeLE or Moodle?' in answer:
        return ['MCeLE', 'Moodle']
    if kind == 'task' and answer.startswith('What are you trying to do with this course:'):
        return ['Launch course content', 'Enroll in a course', 'Copy a Moodle course']
    return []


def ask(state, kind, text):
    state['pending_question'] = kind
    state['status'] = 'intake' if kind in {'error', 'system', 'task', 'conflict'} else 'guiding'
    return text


def step_answer(state, steps):
    unit = steps[state['step_index']]
    state.update(pending_question='step_complete', status='guiding')
    return render_unit(unit) + "\n\nTell me when you've completed this step, or what is stopping you."


def outcome_question(state):
    state.update(pending_question='outcome', status='checking')
    return 'Did that resolve the issue?'


def failed(text):
    return bool(re.search(r"\b(?:still|same)\b.{0,35}\b(?:error|problem|fail|fails|failing|stuck|not|cannot|can.t)\b"
        r"|\b(?:didn.t|did not|doesn.t|does not) work\b|\b(?:i.m|i am) stuck\b"
        r"|\b(?:still no|same problem|it still fails|not working|keeps loading|never submits|times out|can.t do (?:it|that))\b", text, re.I))


def succeeded(text):
    if failed(text) or re.search(r"\b(?:not|never|don.t|didn.t|doesn.t|hasn.t|haven.t)\b", text, re.I):
        return False
    return bool(re.search(r"\b(?:it works now|it worked|that worked|it(?:.s| is) fixed|problem (?:is )?fixed|issue (?:is )?resolved"
                          r"|course (?:opens|opened) now|successfully opened|all fixed)\b", text, re.I))


def completed_from_report(text, article_id, steps):
    """Accept explicit user completion, never infer it from an assistant answer."""
    # Negation belongs to its own action, not to unrelated completed actions:
    # "I cleared the data, but have not restarted" confirms only the former.
    clauses = re.split(r'[,;.]|\b(?:but|however|and)\b', text, flags=re.I)
    text = ' '.join(clause for clause in clauses if not re.search(
        r"\b(?:not|haven.t|have not|didn.t|did not|can.t|cannot|unable|never)\b", clause, re.I))
    if not re.search(r"\b(?:already|have|ve|did|done|completed|cleared|restarted|retried)\b", text, re.I):
        return []
    indexes = set()
    for match in re.finditer(r'\bstep(?:s)?\s+(\d{1,2})(?:\s*(?:through|to|-)\s*(\d{1,2}))?', text, re.I):
        start, end = int(match[1]), int(match[2] or match[1])
        if 1 <= start <= end <= len(steps):
            indexes.update(range(start-1, end))
    if re.search(r'\b(?:all (?:the )?steps|whole procedure|every (?:prescribed )?(?:troubleshooting )?step)\b', text, re.I):
        indexes.update(range(len(steps)))
    if article_id == 'MCELE-LAUNCH-001':
        # The curated launch procedure is linear. Completing a later UI action
        # confirms its preceding navigation, but never a subsequent restart/retry.
        if re.search(r'\b(?:clear|delet)\w*\b.{0,45}\bbrowsing data\b', text, re.I) or (
                re.search(r'\bclear\w*\b', text, re.I) and re.search(r'\bcookies\b', text, re.I)
                and re.search(r'\bcache\w*\b', text, re.I)):
            indexes.update(range(min(6, len(steps))))
        if re.search(r'\brestart\w*\b', text, re.I):
            indexes.add(6)
        if re.search(r'\b(?:retried|retry|tried (?:again|launching)|tried (?:the )?course again)\b', text, re.I):
            indexes.add(7)
    return sorted(index for index in indexes if index < len(steps))


def advance_completed(state, steps, indexes):
    completed = set(state.get('completed_steps', [])) | set(indexes)
    state['completed_steps'] = sorted(completed)
    index = 0
    while index in completed and index < len(steps):
        index += 1
    state['step_index'] = index


def choose_model_unit(answer, units):
    """Only an ID is accepted from the model; all returned facts come from that unit."""
    try:
        choice = json.loads(answer)
    except (ValueError, TypeError):
        return None
    if not isinstance(choice, dict) or set(choice) != {'unit_id'}:
        return None
    return next((unit for unit in units if unit['id'] == choice['unit_id']), None)


def relevant_unit(question, units, context):
    """A conservative local fallback for named fields, course codes and links."""
    tokens = set(normalized(question).split()) - {
        'the', 'a', 'an', 'i', 'me', 'my', 'is', 'are', 'in', 'on', 'to', 'of',
        'for', 'and', 'or', 'it', 'that', 'this', 'do', 'how', 'what', 'where',
        'can', 'you', 'course', 'please', 'with', 'have', 'about',
    }
    course = context.get('course_id')
    if course and (course.casefold() in question.casefold() or re.search(r'eligib|requirement|prerequisite|rank|select', question, re.I)):
        course_tokens = {course.casefold(), ('epme'+course).casefold()}
        course_units = [unit for unit in units if course_tokens & set(normalized(unit['text']).split())]
        if course_units:
            return course_units[0]
    ranked = [(len(tokens & set(normalized(unit['text']).split())), unit) for unit in units]
    reference_query = bool(tokens & {'tutorial', 'training', 'link', 'policy', 'video'})
    if re.search(r'\bwhere\b', question, re.I) and not reference_query:
        ranked = [pair for pair in ranked if pair[1]['kind'] == 'step']
    best = max(ranked, key=lambda pair: pair[0], default=(0, None))
    threshold = 1 if reference_query or 'prerequisite' in tokens else 2
    return best[1] if best[0] >= threshold else None


def guide_reply(question, chunks, state, context, selected_unit=None):
    """Return (answer, clarification). Persist only IDs/progress and user facts."""
    from access_support import NEW_ARTICLES, guided_access_reply
    if chunks[0]['source_path'] in NEW_ARTICLES:
        return guided_access_reply(question, chunks, state, context)
    units = source_units(chunks)
    steps = steps_in(units)
    article_id = chunks[0]['source_path']
    if state.get('article_id') != article_id:
        state.update(article_id=article_id, step_index=0, completed_steps=[], pending_question=None, status='intake')
    if not context.get("_interpretation") and succeeded(question):
        state.update(status='resolved', pending_question=None)
        return "Glad it's working. What else would you like help with?", False
    reply = normalized(question)
    pending = state.get('pending_question')
    if article_id == 'MCELE-EPME-001' and not context.get('course_id'):
        if re.search(r'\b(?:all|compare|comparison|overview|list|every)\b', question, re.I):
            answer = '\n\n'.join(render_unit(unit) for unit in units)
            return answer + '\n\n' + ask(state, 'course', 'Which EPME course would you like to discuss?'), True
        return ask(state, 'course', 'Which EPME course are you asking about?'), True
    if article_id == 'MCELE-ECDEP-001' and not context.get('course_id'):
        return ask(state, 'course', 'Which seminar is this enrollment request for: 5500 or 6800?'), True
    from intent_interpreter import interpreted_guidance
    if article_id != 'MCELE-CSC-001':
        interpreted = interpreted_guidance(chunks, context, state, units)
        if interpreted is not None:
            return interpreted
    if pending == 'explanation':
        if reply in {'yes', 'continue', 'next', 'done', 'continue current step'} and steps:
            resume = state.pop('resume_pending_question', None)
            if resume == 'outcome' or state['step_index'] >= len(steps):
                return outcome_question(state), True
            if resume == 'step_problem':
                return ask(state, resume, 'What happened when you tried this step? You can describe it or attach a screenshot.'), True
            if resume == 'csc_mcele_visible':
                ask(state, resume, 'Does CSC appear under MCeLE My Courses?')
                return render_unit(steps[0]) + '\n\nDoes CSC appear under MCeLE My Courses?', True
            if resume == 'csc_moodle_visible':
                return ask(state, resume, 'Do you now see CSC in Moodle My Courses with All selected?'), True
            return step_answer(state, steps), False
        if reply == 'no':
            state['pending_question'] = 'explanation_detail'
            return 'What other detail would you like to clarify?', True
    if pending == 'offer_steps':
        if reply == 'yes' and steps:
            return step_answer(state, steps), False
        if reply == 'no':
            state.update(pending_question=None, status='information')
            return 'Okay. What else would you like help with?', False
    if article_id == 'MCELE-CSC-001':
        facts = state['known_facts']
        if re.search(r'\b(?:missing|not|doesn.t|does not|cannot find|can.t find)\b.{0,65}\bMoodle\b', question, re.I):
            facts['csc_moodle_visible'] = False
        if re.search(r'\b(?:appears|listed|see)\b.{0,40}\bMCeLE\b', question, re.I):
            facts['csc_mcele_visible'] = True
        if re.search(r'\b(?:missing|not|doesn.t|does not)\b.{0,55}\bMCeLE\b', question, re.I):
            facts['csc_mcele_visible'] = False
        if pending in {'csc_mcele_visible', 'csc_moodle_visible'} and reply in {'yes', 'no'}:
            facts[pending] = reply == 'yes'
            if reply == 'yes':
                completed = [0] if pending == 'csc_mcele_visible' else [0, 1, 2]
                advance_completed(state, steps, completed)
        if facts.get('csc_mcele_visible') is False:
            unit = next(unit for unit in units if 'Help Desk first' in unit['text'])
            state.update(pending_question=None, status='handoff')
            return render_unit(unit), False
        if facts.get('csc_mcele_visible') is True and facts.get('csc_moodle_visible') is False:
            # The source requires confirming the All filter before Region-first.
            if not facts.get('csc_all_filter_checked'):
                state['step_index'] = 2
            else:
                unit = next(unit for unit in units if 'Region first' in unit['text'])
                state.update(pending_question=None, status='handoff')
                return render_unit(unit), False
    if pending == 'outcome':
        if selected_unit and not short_reply(question):
            state.update(pending_question='explanation', resume_pending_question='outcome')
            return render_unit(selected_unit) + '\n\nWould you like to return to checking the result?', True
        if reply in {'yes', 'yes it did', 'resolved', 'fixed'}:
            state.update(status='resolved', pending_question=None)
            return "Glad that resolved it. What else would you like help with?", False
        if reply in {'no', 'no it did not', 'nope'} or failed(question):
            state.update(status='exhausted', pending_question=None)
            escalations = [unit for unit in units if re.search(r'contact.{0,45}help\s*desk', unit['text'], re.I)]
            if escalations:
                return render_unit(escalations[-1]), False
            return 'The approved article has no further troubleshooting steps for this result. Please contact the Helpdesk for further assistance.', False
        return outcome_question(state), True
    if article_id == 'MCELE-RRC-001' and pending is None and not re.search(r'\b(?:catalog|find|other courses?|Item Has|filter|Full Details)\b', question, re.I):
        state['pending_question'] = 'offer_steps'
        return render_unit(units[0]) + '\n\nWould you like help finding a different course that awards RRC?', True
    if steps:
        reported = completed_from_report(question, article_id, steps)
        if pending == 'step_complete' and reply in {'yes', 'done', 'next', 'completed', 'i did that', 'already done', 'ready', 'i am ready', 'im ready'}:
            reported.append(state['step_index'])
        if pending == 'step_problem' and reply in {'done', 'completed', 'i did that'}:
            reported.append(state['step_index'])
        if reported:
            state['known_facts']['reported_completed_steps'] = sorted(set(state['completed_steps']) | set(reported))
            if article_id == 'MCELE-LAUNCH-001':
                for index, fact in ((5, 'cleared_browsing_data'), (6, 'restarted'), (7, 'retried')):
                    if index in reported:
                        state['known_facts'][fact] = True
            advance_completed(state, steps, reported)
            if state['step_index'] >= len(steps):
                if failed(question):
                    state['pending_question'] = 'outcome'
                    return guide_reply('No', chunks, state, context)
                return outcome_question(state), True
            if article_id == 'MCELE-CSC-001' and 2 in reported:
                state['known_facts']['csc_all_filter_checked'] = True
                return ask(state, 'csc_moodle_visible', 'Do you now see CSC in Moodle My Courses with All selected?'), True
            return step_answer(state, steps), False
        if pending in {'step_complete', 'step_problem'} and (reply in {'yes', 'no', 'not yet'} or failed(question)):
            return ask(state, 'step_problem', 'What happened when you tried this step? You can describe it or attach a screenshot.'), True
        if selected_unit:
            # Explaining a label/link does not silently complete or jump a step.
            state['resume_pending_question'] = pending
            state['pending_question'] = 'explanation'
            return render_unit(selected_unit) + '\n\nWould you like to return to the current step?', True
        if state['step_index'] >= len(steps):
            return outcome_question(state), True
        answer = step_answer(state, steps)
        if article_id == 'MCELE-CSC-001' and state['step_index'] == 0:
            state['pending_question'] = 'csc_mcele_visible'
            answer = render_unit(steps[0]) + '\n\nDoes CSC appear under MCeLE My Courses?'
        if pending is None:
            # Include a permission prerequisite without dumping the procedure.
            prerequisites = [unit for unit in units if unit['kind'] == 'note'
                             and re.search(r'\b(?:role|requires?|need)\b', unit['text'], re.I)]
            if prerequisites and article_id in {'MOODLE-COPY-001', 'MCELE-ENROLLMENT-REPORT-001'}:
                answer = render_unit(prerequisites[0]) + '\n\n' + answer
        return answer, False
    state.update(status='information', pending_question=None)
    if article_id == 'MOODLE-COPY-002':
        return '\n\n'.join(render_unit(unit) for unit in units), False
    unit = selected_unit or relevant_unit(question, units, context)
    if unit:
        return render_unit(unit), False
    return 'I do not have enough information in the approved article to answer that. What detail would you like to clarify?', True
