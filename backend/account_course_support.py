"""Bounded routing and extractive guidance for the four reviewed MCeLE articles.

This module deliberately contains routing vocabulary and prompts only.  Answer
facts come from retrieved article units passed to :func:`guide_reviewed_reply`.
The parent router owns role access and retrieval; this module never grants an
article to a role and never fabricates a source unit.
"""

from __future__ import annotations

import re
from copy import deepcopy


REVIEWED_ARTICLES = (
    "MCELE-UNLOCK-001",
    "MCELE-CAC-ASSOC-001",
    "MCELE-FIND-001",
    "MCELE-COURSES-001",
)

_RECOVERY_ARTICLE = "MCELE-RECOVERY-001"
_CAC_ARTICLE = "MCELE-CAC-ASSOC-001"
_UNLOCK_ARTICLE = "MCELE-UNLOCK-001"
_FIND_ARTICLE = "MCELE-FIND-001"
_COURSES_ARTICLE = "MCELE-COURSES-001"


def _has(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text or "", re.I))


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").casefold()).strip()


def _answer_text(question: str, image_text: str) -> str:
    return f"{question or ''}\n{image_text or ''}"


def _course_conflict(chosen, mentions) -> bool:
    mentions = list(mentions or [])
    return len(mentions) > 1 or bool(chosen and mentions and chosen not in mentions)


def _course_fields(selected, previous_selected, chosen, mentions, courses, previous):
    """Build the course fields without turning a course hint into a route."""
    course_id = chosen or (mentions[0] if len(mentions) == 1 and not selected else None)
    if not course_id and selected == previous_selected:
        course_id = previous.get("course_id")
    course = (courses or {}).get(course_id, {}) if course_id else {}
    return {
        "course_id": course_id,
        "course_title": course.get("title") or selected or previous.get("course_title"),
        "course_query": selected or previous.get("course_query"),
        "course_known": bool(course),
        "delivery_area": course.get("content_area"),
        "enrollment_area": course.get("enrollment_area"),
        "discovery_portal": course.get("discovery_portal"),
    }


def _changed(context, previous, course_fields) -> bool:
    keys = (
        "course_id", "course_query", "activity", "system_area", "topic",
        "support_article_id", "support_branch", "association_goal",
        "association_resume", "resume_after_recovery", "support_pending",
    )
    return any(context.get(key) != previous.get(key) for key in keys)


def _context(selected, previous_selected, chosen, mentions, courses, previous,
             *, article=None, activity="account-access", topic=None,
             branch=None, prompt=None):
    fields = _course_fields(selected, previous_selected, chosen, mentions, courses, previous)
    context = dict(fields)
    context.update({
        "activity": activity,
        "system_area": "MCeLE",
        "support_flow": True,
    })
    if topic is not None:
        context["topic"] = topic
    if article is not None:
        context["support_article_id"] = article
    if branch is not None:
        context["support_branch"] = branch
    if prompt:
        context["unresolved"] = True
    return context, prompt, _changed(context, previous, fields)


def _conflict_context(selected, previous_selected, chosen, mentions, courses, previous):
    context, _, changed = _context(
        selected, previous_selected, chosen, mentions, courses, previous,
        activity="course-routing", topic=previous.get("topic"),
        prompt=True,
    )
    context["unresolved"] = True
    return context, (
        "The course details conflict. Which one course do you need help with? "
        "Please update or clear the course field."
    ), True or changed


def _is_disabled_or_legacy_lock(text: str) -> bool:
    return (
        _has(r"\b(?:disabled|deactivated|inactive|reactivat\w*)\b", text)
        or _has(r"\b(?:moodle\s+(?:mobile\s+)?app|moodle app)\b", text)
        or _has(r"\b(?:CAC|card)\b.{0,30}\b(?:PIN|pin|personal identification)\b", text)
    )


def _is_unlock(text: str) -> bool:
    if _is_disabled_or_legacy_lock(text):
        return False
    if not _has(r"\b(?:lock(?:ed|out)?|lockout)\b", text):
        return False
    # Keep the reviewed route specific to a temporary MCeLE account lock.
    return _has(r"\bMCeLE\b|\baccount\b", text) and (
        _has(r"\b(?:three|3)\s+failed\b", text)
        or _has(r"\bfailed\s+(?:login\s+)?attempt", text)
        or _has(r"\b60\s*(?:minutes?|mins?)\b", text)
        or _has(r"\b(?:temporary|temporarily)\s+lock", text)
        or _has(r"\bMCeLE\b.{0,30}\block", text)
    )


def _ambiguous_lock(text: str) -> bool:
    return (
        _has(r"\b(?:locked out|lockout|locked)\b", text)
        and not _has(r"\bMCeLE\b", text)
        and not _has(r"\b(?:moodle|CAC|card|PIN)\b", text)
        and not _has(r"\b(?:disabled|deactivated|inactive)\b", text)
    )


def _is_cac_association(text: str) -> bool:
    return _has(
        r"\b(?:associat\w*|link\w*|unlinked)\b.{0,55}\bCAC\b"
        r"|\bCAC\b.{0,55}\b(?:associat\w*|link\w*|unlinked)\b"
        r"|\b(?:existing account start here|new account start here)\b",
        text,
    )


def _is_recovery(text: str) -> bool:
    return _has(
        r"\b(?:forgot|forget|forgotten|recover\w*|reset)\b.{0,45}\b(?:username|password|credential|login)\b"
        r"|\b(?:username|password|credential|login)\b.{0,45}\b(?:forgot|forget|recover\w*|reset)\b"
        r"|\binvalid credentials\b",
        text,
    )


def _account_existence(text: str) -> str | None:
    if _has(r"\b(?:do not|don't|dont|no)\b.{0,25}\b(?:already\s+)?have\b.{0,20}\bMCeLE\s+account\b", text):
        return "new_account"
    if _has(r"\b(?:new account|create an account|need an account|do not have an account|don't have an account)\b", text):
        return "new_account"
    if _has(r"\b(?:already\s+have|have an?|my)\b.{0,35}\bMCeLE\s+account\b", text):
        return "existing_account"
    if _has(r"\b(?:my|existing|an?)\s+(?:MCeLE\s+)?(?:username|login|password|credentials)\b", text):
        return "existing_account"
    if _has(r"\b(?:already\s+have|have)\b.{0,35}\b(?:MCeLE\s+)?(?:username|login|password|credentials)\b", text):
        return "existing_account"
    return None


def _is_pme_or_staff(text: str) -> bool:
    # The reviewed self-enrollment scope explicitly says non-PME; do not let
    # the substring "PME" in that qualifier route to the legacy PME flow.
    text = re.sub(r"\b(?:non[- ]|not (?:a )?)PME(?:\s+(?:seminar|course))?\b", "", text, flags=re.I)
    text = re.sub(r"\bnot (?:a )?(?:seminar|staff|other user)(?:\s+request)?\b", "", text, flags=re.I)
    return _has(
        r"\b(?:PME|EPME\w*|ECDEP|seminar|professional military education)\b"
        r"|\b(?:another|other|someone else|a Marine|user)\b.{0,35}\b(?:enroll|enrollment|request|record|course)\b"
        r"|\b(?:recommend|deny|approve|review)\b.{0,35}\b(?:enroll|enrollment|request)\b",
        text,
    )


def _is_find_course(text: str) -> bool:
    return _has(
        r"\b(?:find|search|catalog|catalog search|course details|eligib\w*|enroll\w*|register\w*|sign up)\b"
        r"|\b(?:enroll now|re-enroll now|course request|request form)\b"
        r"|\brequest\b.{0,70}\bcourse\b",
        text,
    )


def _is_view_course(text: str) -> bool:
    return _has(
        r"\b(?:my\s+(?:own\s+)?(?:MCeLE\s+)?courses|student dashboard|course status|status of (?:my|the) course|completed course|view\s+(?:my|on|a|completed)|course listing|transcript|certificate|diploma|disenroll|sub-?courses?|course details)\b"
        r"|\b(?:download|print|request)\b.{0,25}\b(?:certificate|transcript|diploma)\b",
        text,
    )


def _is_legacy_course_scope(text: str, chosen=None) -> bool:
    if _has(r"\b(?:Moodle|Instructor[- ]Led)\b", text):
        return True
    # These course IDs are already covered by the reviewed PME/ECDEP flows.
    if chosen in {"5500", "6800", "EPME3000", "EPME4000", "EPME5000", "EPME6000", "CSC"}:
        return True
    if _has(r"\b(?:CSC|RRC|Reserve Retirement|retirement points?|Enrollment Report|enrollment status)\b", text):
        return True
    if _has(r"\b(?:redo|repeat|retake)\b.{0,45}\b(?:completed|course)\b", text) and _has(r"\b(?:point|credit|anniversary|calendar|fiscal)\b", text):
        return True
    if _has(r"\bverif\w*\b.{0,35}\b(?:Marine|enroll\w*)\b", text):
        return True
    return _is_pme_or_staff(text)


def _failed_launch(text: str) -> bool:
    return _has(
        r"\b(?:launch|open|opening)\b.{0,45}\b(?:fail\w*|won.t|wouldn.t|doesn.t|cannot|can.t|not|error|broken|stuck)\b"
        r"|\b(?:cannot|can.t|unable|won.t|doesn.t)\b.{0,30}\b(?:launch|open)\b"
        r"|\b(?:launch|open|opening)\b.{0,60}\b(?:active session|refused to connect|blank|white|nothing happens)\b",
        text,
    )


def reviewed_course_mentions(text, chosen, mentions):
    if not chosen and _has(r'\b(?:non[- ]PME|not (?:a )?PME)\b', text):
        # A list explicitly denied by the user does not assert two active courses.
        denied = re.search(r'\b(?:not|neither)\s+(5500|6800)\s+(?:or|nor|and)\s+(5500|6800)\b', text, re.I)
        if denied:
            mentions = [cid for cid in mentions if cid not in denied.groups()]
    return mentions


def resolve_reviewed_context(selected, previous, previous_selected, question,
                             image_text, courses, chosen, mentions):
    """Resolve one of the four reviewed routes, or return ``None``.

    ``chosen`` and ``mentions`` are supplied by the existing server course
    resolver.  This function only chooses an article after task and location
    evidence is present; an unresolved course conflict remains unresolved.
    """
    previous = previous if isinstance(previous, dict) else {}
    text = _answer_text(question, image_text)
    prior_article = previous.get("support_article_id")
    prior_assoc = prior_article == _CAC_ARTICLE or previous.get("association_goal") == "cac-association"
    mentions = reviewed_course_mentions(text, chosen, mentions)
    course_hint = chosen or (mentions[0] if len(mentions) == 1 else None)
    clauses = re.split(r'[,;.]|\b(?:but|however|and)\b', text, flags=re.I)
    positive = ' '.join(c for c in clauses if not _has(r"\b(?:not|never|haven.t|didn.t|can.t|cannot|how|need|trying|going to)\b", c))
    recovered = bool(prior_assoc and (
        _has(r"\b(?:I|I.ve|already)\b.{0,35}\b(?:recovered|remembered|reset|changed)\b", positive)
        or _has(r'\b(?:completed|finished)\b.{0,35}\b(?:password|credential) recovery\b', positive)
        or (previous.get('resume_after_recovery') and _has(r'\b(?:that worked|it works now|go back|continue association)\b', positive))
        or (previous.get('resume_after_recovery') and previous.get('troubleshooting', {}).get('pending_question') == 'outcome' and _norm(question) == 'yes')))
    if recovered:
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_CAC_ARTICLE, activity="account-access", topic="cac-association", branch="existing_account")
        context.update(association_goal="cac-association", resume_association=True, association_entry_reached=True)
        return context, prompt, True

    # A recovery detour must retain the association goal.  The old reviewed
    # recovery article handles credential facts; this route resumes association
    # only once the user reports recovery or explicitly asks to continue.
    if prior_assoc and _is_recovery(text):
        recovery_branch = "Forgot username" if _has(r"\b(?:forgot|forgotten|recover\w*)\b.{0,25}\busername\b", text) else "Reset password"
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_RECOVERY_ARTICLE, activity="account-access",
            topic="credential-recovery", branch=recovery_branch,
        )
        context.update({
            "association_goal": "cac-association",
            "association_resume": _CAC_ARTICLE,
            "resume_after_recovery": True,
        })
        return context, prompt, True or changed
    if (previous.get("association_goal") == "cac-association"
            and prior_article == _RECOVERY_ARTICLE
            and not _is_view_course(text) and not _is_find_course(text)
            and not _has(r'\b(?:Moodle|launch|copy|enroll)\b', text)):
        # Keep ordinary recovery turns in the canonical existing recovery
        # branch while retaining the parent CAC objective across history turns.
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_RECOVERY_ARTICLE, activity="account-access",
            topic="credential-recovery", branch=previous.get("support_branch") or "Reset password",
        )
        context.update({
            "association_goal": "cac-association",
            "association_resume": _CAC_ARTICLE,
            "resume_after_recovery": True,
        })
        return context, prompt, changed
    # Preserve the existing task/course conflict contract before selecting a
    # reviewed article.  A source must never leak while the course is unclear.
    candidate = (
        _is_unlock(text) or _ambiguous_lock(text) or _is_cac_association(text)
        or _is_find_course(text) or _is_view_course(text)
        or prior_article in REVIEWED_ARTICLES
    )
    if candidate and _course_conflict(chosen, mentions):
        return _conflict_context(selected, previous_selected, chosen, mentions, courses, previous)

    if (_has(r'\b(?:locked|lockout)\b', text) and _has(r'\bCAC\b', text)
            and (_has(r'\bPIN\b', text) or _has(r'\bCAC\b.{0,15}\b(?:locked|lockout)\b', text))):
        context, _, _ = _context(selected, previous_selected, chosen, mentions, courses, previous,
            activity='account-access', topic='account-lockout', prompt=True)
        context['support_pending'] = 'lock_location'
        return context, 'Is the message about your CAC/PIN being locked, or your MCeLE account? Please type the exact message so I can use the right guidance.', True

    if _ambiguous_lock(text) and prior_article != _UNLOCK_ARTICLE:
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            activity="account-access", topic="account-lockout", branch="lock_location",
            prompt=True,
        )
        context["support_pending"] = "lock_location"
        return context, (
            "Where are you locked out: MCeLE, the Moodle app, or your CAC/PIN? "
            "What exact message do you see?"
        ), True or changed

    if (previous.get('support_pending') == 'lock_location' and not _is_unlock(text)
            and not _has(r'\b(?:Moodle|disabled|deactivated)\b', text)):
        context, _, _ = _context(selected, previous_selected, chosen, mentions, courses, previous,
            activity='account-access', topic='account-lockout', prompt=True)
        context['support_pending'] = 'lock_location'
        return context, 'What exact message do you see, and is it on the MCeLE login page or the CAC/PIN prompt?', True

    continued_unlock = (prior_article == _UNLOCK_ARTICLE and
        _has(r'\b(?:lock\w*|unlock\w*|wait\w*|browser|cache|Help Desk|Administrator)\b', text)
        and not _is_disabled_or_legacy_lock(text))
    if _is_unlock(text) or continued_unlock:
        branch = previous.get('support_branch') if continued_unlock else "after_three_failed_attempts"
        if _has(r"\b(?:already|have|ve)?\s*waited\b.{0,30}\b(?:60|sixty|hour)\b", text) and _has(r"\b(?:still|persists|remains)\b", text):
            branch = "account_still_locked"
        elif _has(r'\b(?:how long|automatic|can wait|normal wait)\b', text):
            branch = "after_three_failed_attempts"
        elif _has(r"\b(?:sooner|right now|urgent|immediately|early|manual\w*)\b|\baccess\b.{0,20}\bbefore\b", text) and not _has(r'\b(?:not|don.t)\b.{0,20}\b(?:need|want)\b.{0,15}\bmanual\b', text):
            branch = "need_access_before_wait"
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_UNLOCK_ARTICLE, activity="account-access", topic="account-lockout",
            branch=branch,
        )
        context["support_scope"] = "temporary_mcele_account_lock"
        return context, prompt, changed

    # A location correction can omit the word "locked" from the earlier report.
    # Keep this as account intake rather than falling through to a course guide.
    if (previous.get('topic') == 'account-lockout'
            and _has(r'\bCAC\b.{0,25}\bPIN\b', text)
            and _has(r'\b(?:message|prompt|box|location)\b', text)
            and not _has(r'\b(?:locked|lockout)\b', text)):
        context, _, _ = _context(selected, previous_selected, chosen, mentions, courses, previous,
            activity='account-access', topic='account-lockout', branch='cac_pin_message', prompt=True)
        context['system_area'] = None
        return context, 'What exact message appears at the CAC/PIN prompt?', True

    # Disabled MCeLE accounts, Moodle app lockouts and CAC-PIN lockouts stay on
    # their existing routes, including the existing Help Desk handoff.
    if _is_disabled_or_legacy_lock(text):
        return None

    if (_is_find_course(text) and _has(r'\b(?:non[- ]PME|not (?:a )?PME)\b', text)
            and _has(r'\bMoodle\b', text)):
        context, _, _ = _context(selected, previous_selected, chosen, mentions, courses, previous,
            article=_FIND_ARTICLE, activity='course-enrollment', topic='course-finding', branch='request_form' if _has(r'\brequest\b', text) else 'find_and_enroll', prompt=True)
        return context, 'Do you mean enrolling yourself in a non-PME self-paced MCeLE course, or accessing a course in Moodle?', True

    other_task = _is_view_course(text) or _is_find_course(text) or _failed_launch(text) or _is_legacy_course_scope(text, course_hint)
    if _is_cac_association(text) or (prior_assoc and not _is_recovery(text) and not other_task):
        existence = _account_existence(text)
        pending = previous.get("support_pending")
        if existence is None and pending == "account_exists":
            existence = {"yes": "existing_account", "no": "new_account"}.get(_norm(question))
        if existence is None and previous.get("support_branch") in {"existing_account", "new_account"}:
            existence = previous["support_branch"]
        if existence is None:
            context, _, changed = _context(
                selected, previous_selected, chosen, mentions, courses, previous,
                article=_CAC_ARTICLE, activity="account-access", topic="cac-association",
                branch="account_exists", prompt=True,
            )
            context.update({
                "association_goal": "cac-association",
                "support_pending": "account_exists",
                "association_entry_reached": bool(previous.get('association_entry_reached') or
                    _has(r"\b(?:prompt|screen|asks|says|start here|accepted)\b", text)),
            })
            return context, "Do you already have an MCeLE account?", True or changed
        branch = existence
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_CAC_ARTICLE, activity="account-access", topic="cac-association",
            branch=branch,
        )
        context.update({
            "association_goal": "cac-association",
            "support_pending": None,
        })
        context['association_entry_reached'] = bool(previous.get('association_entry_reached') or
            _has(r"\b(?:prompt|screen|asks|says|start here|accepted|entered.{0,12}PIN)\b", text))
        return context, prompt, changed

    own_request = (prior_article == _FIND_ARTICLE and _has(r'\b(?:request|form|Overview|Enrollment tab)\b', text))
    if (_is_view_course(text) and not own_request and not _failed_launch(text)
            and not _is_legacy_course_scope(text, course_hint)):
        branch = "transcripts" if _has(r"\btranscript\b", text) else "common_actions"
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_COURSES_ARTICLE, activity="course-records", topic="course-viewing",
            branch=branch,
        )
        context["support_scope"] = "own_mcele_course_records"
        return context, prompt, changed

    if ((_is_find_course(text) or own_request) and not _is_legacy_course_scope(text, course_hint)
            and (own_request or chosen or prior_article == _FIND_ARTICLE or _has(r'\b(?:course|courses|curriculum|catalog|self[- ]paced)\b', text))
            and not _failed_launch(text)):
        branch = "request_form" if own_request or _has(r"\b(?:request|open (?:the )?form)\b", text) else "find_and_enroll"
        context, prompt, changed = _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=_FIND_ARTICLE, activity="course-enrollment", topic="course-finding",
            branch=branch,
        )
        context["support_scope"] = "own_non_pme_self_paced_enrollment"
        return context, prompt, changed

    # A follow-up that belongs to a reviewed branch remains bounded to that
    # branch.  The parent router clears state when the topic/article changes.
    if (prior_article in REVIEWED_ARTICLES
            and not _failed_launch(text)
            and not _is_recovery(text)
            and not _is_legacy_course_scope(text, course_hint)):
        return _context(
            selected, previous_selected, chosen, mentions, courses, previous,
            article=prior_article, activity=previous.get("activity", "account-access"),
            topic=previous.get("topic"), branch=previous.get("support_branch"),
        )
    return None


def _source_units(chunks):
    # Keep imports local: troubleshooting imports this module for dispatch.
    from troubleshooting import source_units
    return source_units(chunks)


def _render(unit):
    from troubleshooting import render_unit
    return render_unit(unit)


def _article_id(chunks):
    if not chunks:
        return None
    return chunks[0].get("source_path") or chunks[0].get("article_id")


def _section_units(units, patterns):
    return [unit for unit in units if unit.get("section") and any(
        re.search(pattern, unit["section"], re.I) for pattern in patterns
    )]


def _matching_unit(question, units, patterns):
    for unit in units:
        if any(_has(pattern, unit.get("text", "")) for pattern in patterns):
            return unit
    return None


def _reply_done(question):
    return _norm(question) in {
        "yes", "done", "next", "ready", "completed", "already done",
        "i did that", "okay", "ok",
    }


def _reply_failed(question):
    return _has(r"\b(?:still|stuck|not working|doesn.t work|cannot|can.t|failed|failure|error)\b", question)


def _step_reply(question, units, state):
    from troubleshooting import ask, failed, advance_completed, completed_from_report
    steps = [unit for unit in units if unit.get("kind") == "step"]
    if not steps:
        return None
    index = max(0, min(int(state.get("step_index", 0)), len(steps)))
    reports = completed_from_report(question, state.get('article_id'), steps)
    positive = ' '.join(c for c in re.split(r'[,;.]|\b(?:but|however)\b', question, flags=re.I)
        if not _has(r"\b(?:not|never|haven.t|didn.t|can.t|cannot|need|how|where)\b", c))
    if state.get('article_id') == _FIND_ARTICLE and state.get('active_branch') == 'request_form':
        if _has(r'\b(?:already (?:at|in|on)|opened|am (?:at|in|on)|see)\b', positive):
            if _has(r'\b(?:Overview|Request)\b', positive):
                reports.extend(range(min(4, len(steps))))
            elif _has(r'\bEnrollment\b', positive):
                reports.extend(range(min(3, len(steps))))
    if reports:
        advance_completed(state, steps, reports)
        index = state['step_index']
    if state.get('pending_question') in {'step_complete', 'step_problem'} and (failed(question) or _norm(question) in {'no', 'not yet'}):
        return ask(state, 'step_problem', 'What happened when you tried this step? You can describe it or attach a screenshot.')
    if _reply_done(question) and state.get("pending_question") in {"step_complete", "step_problem"}:
        completed = set(state.get("completed_steps", []))
        completed.add(index)
        state["completed_steps"] = sorted(i for i in completed if i < len(steps))
        while index < len(steps) and index in completed:
            index += 1
        state["step_index"] = index
    if index >= len(steps):
        state["pending_question"] = "outcome"
        state["status"] = "checking"
        return "Did that resolve the issue?"
    state["pending_question"] = "step_complete"
    state["status"] = "guiding"
    return _render(steps[index]) + "\n\nTell me when you've completed this step, or what is stopping you."


def reviewed_units(units, article, context):
    branch = context.get("support_branch")
    if article == _UNLOCK_ARTICLE:
        section_patterns = {
            "after_three_failed_attempts": (r"three failed",),
            "need_access_before_wait": (r"before the wait",),
            "account_still_locked": (r"still appears locked",),
            "unsure_credentials": (r"unsure of your credentials",),
        }
        patterns = section_patterns.get(branch, section_patterns["after_three_failed_attempts"])
        active = _section_units(units, patterns)
    elif article == _CAC_ARTICLE:
        active = _section_units(units, (
            r"existing account",) if branch in {"existing_account", "association_recovery"}
            else (r"do not already have", r"when you do not") if branch == "new_account"
            else (r"before you begin",))
        if branch == "existing_account" and not active:
            active = units
        if branch == 'existing_account' and not context.get('association_entry_reached'):
            active = _section_units(units, (r'before you begin',)) + active
    elif article == _FIND_ARTICLE:
        active = _section_units(units, (r"open a course request",)) if branch == "request_form" else _section_units(units, (r"find and enroll",))
    else:
        active = _section_units(units, (r"transcript",)) if branch == "transcripts" else _section_units(units, (r"common course actions", r"find your courses"))
    return active or units



def guide_reviewed_reply(question, chunks, state, context):
    """Return ``(answer, needs_clarification)`` using exact source units.

    This follows the existing ``troubleshooting.guide_reply`` contract:
    source facts and one-step guidance return ``False``; routing questions or
    unsupported details return ``True``.
    """
    state = state if isinstance(state, dict) else {}
    context = context if isinstance(context, dict) else {}
    article = _article_id(chunks)
    if article not in REVIEWED_ARTICLES or not chunks:
        return "I do not have an approved source unit for that question.", False
    branch = context.get("support_branch")
    if state.get("article_id") != article or state.get("active_branch") != branch:
        preserved = {
            key: deepcopy(state[key]) for key in ("profile_id", "known_facts")
            if key in state
        }
        state.clear()
        state.update(preserved)
        state.update({
            "schema": 1,
            "article_id": article,
            "active_branch": branch,
            "step_index": 0,
            "completed_steps": [],
            "pending_question": None,
            "status": "intake",
        })
    units = _source_units(chunks)
    if not units:
        return "I do not have an approved source unit for that question.", False

    # The account-existence question is resolved by routing, so an account
    # association turn never repeats prerequisites after an explicit answer.
    if article == _CAC_ARTICLE and branch == "account_exists":
        return "Do you already have an MCeLE account?", True

    if not context.get('_interpretation') and state.get('pending_question') == 'outcome' and _norm(question) == 'yes':
        state.update(status='resolved', pending_question=None)
        return "Glad that resolved it. What else would you like help with?", False

    if _reply_failed(question) and state.get("pending_question") == "outcome":
        escalation = _matching_unit(question, units, (r"Help Desk", r"Administrator", r"persists"))
        if escalation:
            state["status"] = "handoff"
            return _render(escalation), False

    active = reviewed_units(units, article, context)

    if article == _UNLOCK_ARTICLE and _has(r'\b(?:how long|how many|minutes|hour|when|wait)\b', question):
        wait = _matching_unit(question, active, (r'Wait 60 minutes',))
        if wait:
            return _render(wait), False

    # Keep the approved limitation visible without repeating the source's
    # unreviewed account-creation wording.
    if article == _CAC_ARTICLE and branch == "new_account":
        active = [unit for unit in active if not _has(r"separately approved", unit.get("text", ""))]
        if not active:
            active = units

    # The approved form boundary answers submission/approval questions before
    # generic model progression, even if the model supplied no answer-unit ID.
    if article == _FIND_ARTICLE and branch == 'request_form':
        if _has(r"\b(?:submit\w*|approv\w*)\b", question):
            limit = _matching_unit(question, active, (r"does not mean", r"submission", r"approved"))
            if limit:
                return _render(limit), False
    from intent_interpreter import interpreted_guidance
    interpreted = interpreted_guidance(chunks, context, state, active)
    if interpreted is not None:
        return interpreted

    # Exact source-unit selection for records/actions questions avoids dumping
    # unrelated procedures and avoids inventing action behavior.
    if article == _COURSES_ARTICLE:
        keyword_patterns = (
            (r"certificate|diploma", (r"certificate", r"diploma")),
            (r"(?:\bView\b.{0,35}\bcompleted|\bcompleted\b.{0,35}\bView\b|does View|View button|enroll me again)", (r"reviews completed", r"does not enroll")),
            (r"launch", (r"opens the course enrollment",)),
            (r"status|pending|progress|failed|passed|equivalency", (r"status", r"Pending")),
            (r"transcript", (r"Request Official Transcript", r"Print Transcript")),
        )
        selected = None if _has(r'\b(?:where|find|locate|get to)\b', question) and not _has(r'\b(?:transcript|certificate|diploma)\b', question) else next((
            _matching_unit(question, active, pats)
            for trigger, pats in keyword_patterns if _has(trigger, question)
        ), None)
        if selected:
            state["status"] = "information"
            state["pending_question"] = None
            return _render(selected), False
        # Course-location/status questions use the reviewed navigation steps;
        # broader records questions may return the active exact units.
        if not [u for u in active if u.get("kind") == "step"]:
            return "\n\n".join(_render(unit) for unit in active), False

    # A request-form answer begins at its reviewed path.  Do not claim that
    # opening the form submitted or approved anything; the exact source unit
    # contains the explicit limit.
    if article == _FIND_ARTICLE and branch == "request_form":
        result = _step_reply(question, active, state)
        if result:
            return result, False

    # Recovery is intentionally handled by the existing recovery guide; this
    # branch is only used if a caller accidentally sends its chunks here.
    if article == _CAC_ARTICLE and branch == "association_recovery":
        unit = _matching_unit(question, active, (r"Forgot your MCeLE credentials", r"Pause the CAC"))
        if unit:
            return _render(unit), False

    old_state = dict(state)
    if active:
        # Restrict progression to the selected section, preserving exact units.
        state["section"] = active[0].get("section")
        result = _step_reply(question, active, state)
        if result:
            return result, False
    selected = _matching_unit(question, active, (r"username|password|CAC|account|course|status|View|Launch|Request|certificate|transcript",))
    if selected:
        state["status"] = "information"
        state["pending_question"] = None
        return _render(selected), False
    state.update(old_state)
    return "I do not have enough information in the approved article to answer that.", False


# A descriptive alias makes the hook easy to discover for callers that prefer
# the existing access-support naming.
guided_account_course_reply = guide_reviewed_reply
