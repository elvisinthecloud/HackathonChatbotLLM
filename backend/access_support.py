"""Reviewed login and learner access routing; no services or role inference."""
import re

ACCESS_BASELINE_ARTICLES = (
    'MCELE-LOGIN-001', 'MCELE-CAC-001', 'MCELE-RECOVERY-001',
    'MCELE-LAUNCH-002', 'MOODLE-ACCESS-001', 'MOODLE-APP-001',
)
from account_course_support import REVIEWED_ARTICLES, resolve_reviewed_context, guide_reviewed_reply

NEW_ARTICLES = ACCESS_BASELINE_ARTICLES + REVIEWED_ARTICLES
ALL_ROLES = ('Student', 'Adjunct Faculty', 'Academics Officer', 'Training Manager', 'Regional Director')


def has(pattern, text):
    return bool(re.search(pattern, text, re.I))


def access_method(text):
    # Use the same explicit, non-negated evidence boundary as interpretation.
    from intent_interpreter import method_choices
    choices = method_choices(text)
    return 'browser' if 'browser' in choices else 'app' if 'app' in choices else None


def problem_branch(text, topic):
    if topic == 'credential-recovery':
        if has(r'\b(?:email|pin)\b', text) and has(r'\b(?:no|not|missing|never|didn.t|haven.t|doesn.t|hasn.t|waiting|arriv\w*)\b', text):
            return 'Recovery email missing'
        if has(r'\busername\b', text) and not has(r'\bpassword\b', text):
            return 'Forgot username'
        if has(r'\bpassword\b', text) and not has(r'\busername\b', text):
            return 'Reset password'
    if topic == 'cac-login':
        for pattern, branch in (
            (r'\b(?:loop\w*|back to (?:the )?login|back to (?:the )?(?:start|starting) page)\b', 'Login loop'),
            (r'\b(?:access denied|denied|deers)\b', 'Access denied'),
            (r'\b(?:no|not|missing|never|doesn.t)\b.{0,45}\b(?:prompt|certificate selection)\b', 'No CAC prompt'),
            (r'\b(?:new|replaced|replacement)\b.{0,25}\bCAC\b', 'CAC login fails after receiving a new CAC'),
            (r'\b(?:personal|home)\b.{0,30}\b(?:device|computer|laptop)\b', 'CAC login fails on a personal device'),
            (r'\b(?:deactivated|disabled|inactive|reactivat\w*)\b', 'Account is deactivated or disabled'),
        ):
            if has(pattern, text):
                return branch
    if topic == 'launch':
        for pattern, branch in (
            (r'\b(?:pop.?up|nothing (?:opens|happens)|no window)\b', 'Pop-up blocked'),
            (r'\b(?:active session|another session (?:is )?running)\b', 'Active session'),
            (r'\b(?:blank|white|empty)\s+(?:page|screen|window)\b', 'Blank page'),
            (r'\bskillsoft\b', 'Skillsoft connection'),
            (r'\blaunch menu\b', 'Launch menu course'),
        ):
            if has(pattern, text):
                return branch
    return None


def resolve_support_context(selected, previous, previous_selected, question, image_text,
                            courses, chosen, mentions):
    """Return None for existing reviewed workflows, otherwise resolved context/prompt/change."""
    reviewed = resolve_reviewed_context(selected, previous, previous_selected, question, image_text, courses, chosen, mentions)
    if reviewed is not None:
        return reviewed
    text = question + '\n' + image_text
    prior_topic = previous.get('topic')
    prior_new = previous.get('support_article_id') in NEW_ARTICLES or previous.get('support_flow')
    pending = previous.get('troubleshooting', {}).get('pending_question')
    copy_task = has(r'\b(?:copy|copying|clone|cloning|Quality Assurance|Content Management|MClearn)\b', text)
    created_problem = has(r'\b(?:course|activity|activities|material|quiz|lesson)\b', text) and has(r'\b(?:created|built|authored|designed)\b', text) and has(r'\b(?:not working|won.t|doesn.t|broken|problem|issue|fail\w*)\b', text)
    if copy_task:
        return None
    if previous.get('troubleshooting', {}).get('article_id') == 'MCELE-CSC-001' and not access_method(question) and not has(r'\b(?:log\s*in|login|sign\s*in)\b', question):
        return None
    moodle = has(r'\b(?:moodle|instructor[- ]led)\b', text)
    created_problem = created_problem or previous.get('topic') == 'course-problem'
    if created_problem and not moodle and courses.get(chosen, {}).get('content_area') != 'Moodle' and previous.get('system_area') != 'Moodle':
        return None
    method = access_method(question)
    invalid_credentials = has(r'\binvalid credentials\b', text)
    disabled_account = has(r'\baccount\b', text) and has(r'\b(?:disabled|deactivated|reactivat\w*)\b', text)
    recovery = invalid_credentials or has(r'\b(?:forgot|forgotten|recover\w*|reset)\b.{0,55}\b(?:username|password|credentials)\b|\b(?:username|password)\b.{0,30}\b(?:forgot|reset|recover\w*)\b', text)
    missing_email = has(r'\b(?:recovery|reset|pin)\b', text) and has(r'\b(?:email|arriv\w*|receiv\w*)\b', text) and has(r'\b(?:not|no|missing|never|didn.t|haven.t|doesn.t|hasn.t)\b', text)
    generic_login = has(r'\b(?:log\s*(?:in|on)|login|sign\s*(?:in|on))\b', text) and has(r'\b(?:how|cannot|can.t|unable|won.t|not|fails?|failing|problem|help|loop\w*)\b', text)
    cac = has(r'\bCAC\b', text)
    learner = has(r'\b(?:launch\w*|access|open|opening|course tile|course material|course activity|activities|dashboard|my courses)\b', text)
    enrolled = has(r'\b(?:my enrolled course|course (?:I am|I.m) enrolled in|enrolled|taking|as a student)\b', text) and not has(r'\b(?:not|never)\s+enrolled\b', text)
    # Keep explicitly reviewed enrollment/credit and CSC-specific workflows intact.
    enrollment = has(r'\b(?:enroll\w*|eligib\w*|prerequisit\w*|recommend|deny|ECDEP|RRC|retirement|Enrollment Report)\b', text) and not enrolled
    if enrollment and not generic_login and not recovery and not created_problem:
        return None
    if (chosen == 'CSC' or mentions == ['CSC']) and has(r'\b(?:CSC|missing|not (?:appear|show)|cannot find|can.t find)\b', text) and not method and not generic_login:
        return None

    if (not prior_new and previous.get('activity') == 'course-content' and previous.get('system_area') == 'MCeLE'
            and not moodle and not generic_login and not recovery and not missing_email and not created_problem
            and not problem_branch(text, 'launch') and selected == previous_selected):
        return None
    topic = None
    if recovery or missing_email or (prior_topic == 'credential-recovery' and prior_new and not moodle and not learner and not generic_login):
        topic = 'credential-recovery'
    elif moodle or (method and prior_topic in {'moodle-access', 'moodle-app'}) or created_problem:
        topic = 'moodle-access'
    elif pending == 'login_method' and cac:
        topic = 'login'
    elif disabled_account:
        topic = 'login'
    elif generic_login and not (prior_topic in {'moodle-access', 'moodle-app'} and not has(r'\bMCeLE\b', question)):
        topic = 'cac-login' if cac and has(r'\b(?:cannot|can.t|unable|won.t|not|fails?|failing|problem|loop\w*)\b', text) else 'login'
    elif cac and (pending == 'login_method' or generic_login or problem_branch(text, 'cac-login') or has(r'\b(?:loop|denied|prompt|new|disabled|personal|fails?|problem|help|not working|isn.t working|doesn.t work)\b', text)):
        topic = 'cac-login'
    elif learner or (problem_branch(text, 'launch') and (chosen or mentions or has(r'\bcourse\b', text))):
        topic = 'launch'
    elif prior_new:
        topic = prior_topic
    if not topic:
        return None

    selection_changed = selected != previous_selected
    course_id = chosen or (mentions[0] if len(mentions) == 1 and not selected else None)
    if not course_id and not selection_changed and not (topic in {'login', 'cac-login', 'credential-recovery'}):
        course_id = previous.get('course_id')
    course = courses.get(course_id, {})
    course_query = selected or (previous.get('course_query') if not selection_changed else None)
    if pending == 'course' and prior_topic == 'launch' and not course_id and not method and not moodle and not has(r'\b(?:MCeLE|self[- ]paced)\b', text):
        if question.strip().casefold() not in {'yes', 'no', 'done'}:
            course_query = question.strip()[:160]
    course_changed = selection_changed or course_id != previous.get('course_id') or course_query != previous.get('course_query')
    platform = course.get('content_area')
    context = {'course_id': course_id, 'course_title': course.get('title') or course_query,
               'course_query': course_query, 'course_known': bool(course),
               'delivery_area': platform, 'enrollment_area': course.get('enrollment_area'),
               'discovery_portal': course.get('discovery_portal'), 'topic': topic,
               'activity': 'account-access' if topic in {'login', 'cac-login', 'credential-recovery'} else 'course-content',
               'support_flow': True}
    prompt = None
    branch = 'Reset password' if invalid_credentials else ('Disabled account' if disabled_account else problem_branch(text, topic))
    if not branch and prior_new and prior_topic == topic and not course_changed:
        branch = previous.get('support_branch')
    if topic in {'login', 'cac-login', 'credential-recovery'}:
        context['system_area'] = 'MCeLE'
        if topic == 'login':
            if has(r'\b(?:username|password|credentials)\b', text):
                branch = 'Username/password login'
            elif cac:
                branch = 'CAC login'
            if branch is None:
                prompt = 'Are you signing in with a CAC or with your MCeLE username and password?'
            context['support_article_id'] = 'MCELE-LOGIN-001'
        elif topic == 'cac-login':
            context['support_article_id'] = 'MCELE-CAC-001'
            if branch is None:
                prompt = 'What happens when you try CAC login: a login loop, access denied, no CAC prompt, or something else?'
        else:
            context['support_article_id'] = 'MCELE-RECOVERY-001'
            if branch is None:
                prompt = 'Are you recovering your username or resetting your password?'
    else:
        prior_method = previous.get('moodle_access_method') if not course_changed and prior_topic in {'moodle-access', 'moodle-app'} else None
        direct_moodle = moodle or (method is not None and prior_topic in {'moodle-access', 'moodle-app'}) or created_problem
        if not direct_moodle and topic == 'launch' and platform == 'Moodle':
            direct_moodle = True
        if not direct_moodle and topic == 'launch' and not platform:
            if not course_id and not course_query:
                prompt = 'Which course are you trying to open? You can give its name or course code.'
            elif has(r'\b(?:moodle|instructor[- ]led)\b', text):
                direct_moodle = True
            elif has(r'\b(?:MCeLE|self[- ]paced)\b', text):
                platform = 'MCeLE'
            elif previous.get('system_area') == 'MCeLE' and not course_changed:
                platform = 'MCeLE'
            else:
                prompt = 'Is this a self-paced course in MCeLE, or an Instructor-Led Course in Moodle?'
        if direct_moodle or prior_topic in {'moodle-access', 'moodle-app'} and not course_changed and topic != 'launch':
            if platform == 'MCeLE' and (moodle or method) and learner and prior_topic not in {'moodle-access', 'moodle-app'} and not has(r'\b(?:log\s*in|login|sign\s*in|get to|where|access (?:the )?moodle)\b', text):
                prompt = 'The selected course is mapped to MCeLE content, but you mentioned Moodle. Which course are you trying to open? Please update or clear the course field if needed.'
            phone_only = has(r'\b(?:phone|mobile|iphone|android|ipad|tablet)\b', text) and method is None and prior_method is None
            method = method or prior_method or (None if phone_only else 'browser')
            if phone_only and not prompt:
                prompt = 'Are you using the Moodle app or MCeLE in a web browser?'
            context.update(topic='moodle-app' if method == 'app' else 'moodle-access', system_area='Moodle', moodle_access_method=method,
                           support_article_id='MOODLE-APP-001' if method == 'app' else 'MOODLE-ACCESS-001')
            stage = previous.get('failure_stage') if prior_topic == context['topic'] and not course_changed else None
            if created_problem:
                stage = 'course-management'
                context['activity'] = 'course-management'
            elif method == 'app' and has(r'\b(?:locked[- ]?out|lockout)\b', text):
                stage = 'locked-out'
            elif has(r'\b(?:missing|cannot find|can.t find|not (?:showing|visible)|doesn.t (?:appear|show))\b', text) and has(r'\b(?:course|tile)\b', text):
                stage = 'missing-course'
            elif has(r'\b(?:activity|activities|material|quiz|lesson)\b', text) and has(r'\b(?:not|won.t|doesn.t|broken|problem|issue|fail\w*|unable|can.t|cannot)\b', text):
                stage = 'activity'
            elif has(r'\b(?:launch|redirect|route|handoff)\w*\b', text) and has(r'\bMCeLE\b', text):
                stage = 'handoff'
            if has(r'\b(?:inside|already in|from the dashboard|I am in Moodle|I.m in Moodle|on the Moodle dashboard)\b', text):
                entry = 'Moodle'
            elif has(r'\bMCeLE\b', text) or stage == 'handoff':
                entry = 'MCeLE'
            else:
                entry = previous.get('entry_point') if not course_changed else None
            context.update(failure_stage=stage, entry_point=entry)
            branch = 'App access' if method == 'app' else ('MCeLE-to-Moodle handoff' if stage == 'handoff' else 'Browser access')
            if method == 'app' and (has(r'\bQR(?:[- ]code)?\b', text) or (previous.get('support_branch') == 'QR code enrollment' and not course_changed and prior_method == method)):
                branch = 'QR code enrollment'
            if method == 'app' and stage == 'locked-out':
                branch = 'Locked out'
            if stage in {'missing-course', 'activity', 'course-management'}:
                branch = 'Moodle support'
        else:
            context.update(system_area=platform, support_article_id='MCELE-LAUNCH-002')
            if branch is None and not prompt and previous.get('troubleshooting', {}).get('article_id') != 'MCELE-LAUNCH-001':
                prompt = 'What happens when you try to open the course? You can type the exact error or attach a screenshot.'
    context['support_branch'] = branch
    if len(mentions) > 1 or bool(chosen and mentions and mentions != [chosen]):
        prompt = 'The selected course and the course in your message differ. Which course do you need help with? Please update or clear the course field.'
    if prompt:
        context['unresolved'] = True
    changed = course_changed or any(context.get(key) != previous.get(key) for key in (
        'activity', 'system_area', 'topic', 'support_article_id', 'moodle_access_method', 'support_branch'))
    return context, prompt, changed


def reported_access_steps(question, branch, steps):
    """Recognize a few reviewed completion reports, with negation scoped by clause."""
    clauses = re.split(r'[,;.]|\b(?:but|however|and)\b', question, flags=re.I)
    report = ' '.join(clause for clause in clauses if not has(
        r"\b(?:not|never|haven.t|have not|didn.t|did not|can.t|cannot|unable)\b", clause))
    done = set()
    if branch == 'Browser access' and has(r'\b(?:I am|I.m|already|inside)\s+(?:already\s+)?(?:in\s+)?Moodle\b', report):
        done.update(range(min(2, len(steps))))
    for index, unit in enumerate(steps):
        text = unit['text']
        if index == 0 and branch in {'Browser access', 'App access'} and has(r'\b(?:already|have|ve)\b.{0,35}\b(?:logged|signed)\s+in\b', report) and has(r'\bMCeLE\b', report):
            done.add(index)
        if has(r'\bclear\b', text) and has(r'\b(?:cleared|deleted)\b.{0,35}\b(?:cache|cookies)\b', report):
            if not has(r'\bcookies\b', text) or has(r'\bcookies\b', report):
                done.add(index)
        if has(r'\brestart\b', text) and has(r'\brestarted\b', report):
            done.add(index)
        if branch == 'Recovery email missing':
            if has(r'Wait up to 30 minutes', text) and has(r'\bwaited\b.{0,20}\b(?:30|thirty)\s+(?:minutes|mins)\b', report):
                done.add(index)
            if has(r'\b(?:spam|junk)\b', text) and has(r'\bchecked\b.{0,30}\b(?:spam|junk)\b', report):
                done.add(index)
    return sorted(done)


def guided_access_reply(question, chunks, state, context):
    """Use only the active approved section, then delegate linear progress to the guide."""
    if chunks[0]['source_path'] in REVIEWED_ARTICLES:
        return guide_reviewed_reply(question, chunks, state, context)
    from troubleshooting import source_units, steps_in, render_unit, step_answer, outcome_question, ask, normalized, short_reply, failed, succeeded, advance_completed, completed_from_report
    units = source_units(chunks)
    article_id = chunks[0]['source_path']
    branch = context.get('support_branch')
    active = [unit for unit in units if unit.get('section') == branch]
    if not active:
        return ask(state, 'detail', 'What happens at the step you are trying to complete?'), True
    if state.get('article_id') != article_id or state.get('active_branch') != branch:
        state.update(article_id=article_id, active_branch=branch, step_index=0, completed_steps=[], pending_question=None, status='intake')
    if context.get('moodle_access_method'):
        state['known_facts']['moodle_access_method'] = context['moodle_access_method']
    if context.get('failure_stage'):
        state['known_facts']['failure_stage'] = context['failure_stage']
    if not context.get("_interpretation") and succeeded(question):
        state.update(status='resolved', pending_question=None)
        return "Glad it's working. What else would you like help with?", False
    if branch == 'Moodle support':
        unit = next((unit for unit in active if 'option 3' in unit['text']), active[0])
        state.update(status='handoff', pending_question=None)
        return render_unit(unit), False
    steps = steps_in(active)
    if not steps:
        state.update(status='information', pending_question=None)
        return render_unit(active[0]), False
    from intent_interpreter import interpreted_guidance
    interpreted = interpreted_guidance(chunks, context, state, active)
    if interpreted is not None:
        return interpreted
    pending = state.get('pending_question')
    reply = normalized(question)
    if pending == 'explanation':
        if reply == 'yes':
            state['pending_question'] = state.pop('resume_pending_question', 'step_complete')
            if state['step_index'] >= len(steps):
                return outcome_question(state), True
            return step_answer(state, steps), False
        if reply == 'no':
            return ask(state, 'explanation_detail', 'What other detail would you like to clarify?'), True
    if pending == 'outcome':
        if reply in {'yes', 'yes it did', 'fixed', 'resolved'}:
            state.update(status='resolved', pending_question=None)
            return "Glad that resolved it. What else would you like help with?", False
        if reply in {'no', 'nope', 'no it did not'} or failed(question):
            escalation = next((unit for unit in units if unit.get('section') == 'Moodle support' and 'option 3' in unit['text']), None)
            escalation = escalation or next((unit for unit in reversed(active) if re.search(r'contact.{0,60}help\s*desk', unit['text'], re.I)), None)
            if escalation:
                state.update(status='handoff', pending_question=None)
                return render_unit(escalation), False
            return ask(state, 'step_problem', 'What happened after the last step? You can describe it or attach a screenshot.'), True
        return outcome_question(state), True
    reported = completed_from_report(question, article_id, steps) + reported_access_steps(question, branch, steps)
    if pending == 'step_complete' and reply in {'yes', 'yes i did'}:
        reported.append(state['step_index'])
    if pending in {'step_complete', 'step_problem'} and reply in {'done', 'next', 'completed', 'i did that', 'already done'}:
        reported.append(state['step_index'])
    if reported:
        advance_completed(state, steps, reported)
        state['known_facts']['reported_completed_steps'] = list(state['completed_steps'])
        if state['step_index'] >= len(steps):
            return outcome_question(state), True
        return step_answer(state, steps), False
    if pending in {'step_complete', 'step_problem'} and (failed(question) or reply in {'no', 'not yet'}):
        return ask(state, 'step_problem', 'What happened when you tried this step? You can describe it or attach a screenshot.'), True
    if state['step_index'] >= len(steps):
        return outcome_question(state), True
    if not short_reply(question) and has(r'\b(?:where|what does|what is|what.s|why|explain|site URL)\b', question) and pending:
        from troubleshooting import relevant_unit
        selected = relevant_unit(question, active, context)
        if selected:
            state.update(pending_question='explanation', resume_pending_question=pending)
            return render_unit(selected) + '\n\nWould you like to return to the current step?', True
        return ask(state, 'explanation_detail', 'That detail is not in the approved article. What part of the current step are you having trouble with?'), True
    return step_answer(state, steps), False
