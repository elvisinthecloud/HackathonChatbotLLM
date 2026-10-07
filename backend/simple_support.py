"""Simple grounded support: one model reply per turn over the role's permitted articles,
then a server-side fact gate.

The model sees only articles whose explicit grants include the session role (missing
grant = deny). It writes its own reply, but every bold label, link, phone number,
email address and course code must appear in a permitted article, and every citation
must name a permitted article. A failing draft gets one repair; anything still
unsupported is removed sentence by sentence, falling back to the Help Desk.
"""
import hashlib
import re

from article_registry import DEFAULT_MANIFEST, REGISTRY, read_json_file

HISTORY_EXCHANGES = 10
HISTORY_CHARS = 16000
FALLBACK = "I don't have approved guidance for that. Please contact the Help Desk for help."


def load_articles(manifest=DEFAULT_MANIFEST, registry=REGISTRY):
    root = manifest.parent
    out = []
    for entry in registry['articles']:
        path = root / entry['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['file_sha256']:
            raise ValueError('Article does not match its reviewed release hash: ' + entry['article_id'])
        record = read_json_file(path, root)
        out.append({'id': entry['article_id'], 'title': record['title'], 'content': record['content'],
                    'roles': tuple(entry['allowed_roles']), 'courses': tuple(entry['course_ids']),
                    'bucket': entry['bucket_id']})
    return out


ARTICLES = load_articles()


def permitted(role):
    return [a for a in ARTICLES if role in a['roles']]


COURSE_CODES = sorted({c for a in ARTICLES for c in a['courses']}, key=len, reverse=True)


def mentioned_courses(text):
    """Course codes named anywhere in the user's side of the conversation."""
    found = set()
    for code in COURSE_CODES:
        if re.search(r'(?<![A-Za-z0-9])' + re.escape(code) + r'(?![0-9])', text, re.I) or \
           (code.isdigit() and re.search(r'[A-Za-z]' + code + r'(?![0-9])', text)):
            found.add(code)
    return found


def in_scope(role, conversation_text, course_id=None):
    """Permitted articles, minus course-scoped ones when the user named only other courses."""
    named = mentioned_courses(conversation_text) | ({course_id} if course_id else set())
    return [a for a in permitted(role)
            if not a['courses'] or not named or named & set(a['courses'])]


SYSTEM = """You are the MCeLE help desk assistant for {name}, whose role is {role}.
Help them finish what they are trying to do, like a friendly, competent help desk tech.
{course_line}
Rules:
- Use only the articles below for facts: steps, button names, links, phone numbers, emails, course rules. Never invent a fact, link, button or contact.
- You may write in your own words, but keep links, button names and numbers exactly as written in the article.
- Give only the next steps that fit where the user is now. Don't repeat steps they say they already did, and don't re-send a whole procedure when they ask about one step.
- Ask a question only when you truly cannot help without the answer, and ask at most one.
- If the user says a button or option isn't there, or the articles don't cover their situation, say so plainly and point them to the Help Desk route given in the articles. Don't loop back to the same steps.
- If the user changes topic, follow the new topic.
- If the user asks for something their role isn't covered for here, say you can't help with that for their role.
- Use **bold** ONLY for exact on-screen labels, menu items, buttons, links and phone numbers copied character-for-character from an article. Never bold anything else.
- If the articles don't say where to go or who to contact, say "contact the Help Desk" and nothing more. Never name any other office, unit, command, region, administrator or website.
- Never describe what other roles can or cannot do, and never explain how another role does their task.
- Don't add tips, causes or troubleshooting ideas (browser settings, incognito, retry later, etc.) unless an article states them.
- Don't say what a button or page does, what an error means, or what will happen next (e.g. "the request moves on", "View shows the certificate") unless an article says exactly that.
- Don't tell the user something isn't available to them, or that they lack access, unless an article says so.
- When the user reports a button or option isn't there and the article doesn't cover that, say the articles don't cover it and point to the Help Desk route the relevant article gives.
- Cite the articles you used at the end of a sentence like [MCELE-LOGIN-001].
- Keep replies short and easy to read on a phone.

Articles this user may see:
{articles}"""


def system_prompt(profile, course_id=None, articles=None):
    arts = '\n\n'.join(
        f"=== {a['id']}: {a['title']}" + (f" (applies to courses: {', '.join(a['courses'])})" if a['courses'] else '')
        + '\n' + a['content'] for a in (permitted(profile['role']) if articles is None else articles))
    course_line = f'The user selected course: {course_id}.\n' if course_id else ''
    return SYSTEM.format(name=profile['name'], role=profile['role'], course_line=course_line, articles=arts)


# ---- fact gate ----
def norm(s):
    return re.sub(r'\s+', ' ', s.lower())


def squash(s):
    return re.sub(r'[\s\-]', '', s)


CITE = re.compile(r'\[([A-Z]+(?:-[A-Z0-9]+)+)\]')


def items(reply):
    out = [('link', u.rstrip('.,')) for u in re.findall(r'https?://[^\s)\]>"*]+', reply)]
    out += [('phone', p) for p in re.findall(r'(?:1-)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}', reply)]
    out += [('email', e) for e in re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', reply)]
    out += [('label', b) for b in re.findall(r'\*\*([^*\n]{1,80})\*\*', reply)]
    out += [('code', c) for c in re.findall(r'\b[A-Z]{2,}[A-Z0-9]*\d{3,}[A-Z]*\b', reply)]
    return out


def violations(reply, role):
    allowed = {a['id']: a['content'] for a in permitted(role)}
    v = [('citation', c) for c in sorted(set(CITE.findall(reply))) if c not in allowed]
    text = norm(' '.join(allowed.values()))
    flat, digits = squash(text), re.sub(r'\D', '', text)
    for kind, val in items(reply):
        if kind == 'phone':
            ok = re.sub(r'\D', '', val)[-10:] in digits
        else:
            ok = squash(norm(val).strip(' .:')) in flat
        if not ok:
            v.append((kind, val))
    return v


def drop_unsupported(reply, bad):
    keep = [s for s in re.split(r'(?<=[.!?])\s+|\n', reply)
            if not any(val in s for _, val in bad)]
    out = '\n'.join(keep).strip()
    return out if re.search(r'[A-Za-z]{3,}', out) and CITE.search(out) else FALLBACK


def number_citations(reply, role):
    """Replace article-ID citations with [n] and build the source list."""
    by_id = {a['id']: a for a in permitted(role)}
    order = []
    def sub(m):
        aid = m.group(1)
        if aid not in by_id:
            return ''
        if aid not in order:
            order.append(aid)
        return f'[{order.index(aid) + 1}]'
    text = re.sub(r' ?' + CITE.pattern, lambda m: (lambda n: ' ' + n if n else '')(sub(m)), reply)
    sources = [{'citation': i + 1, 'title': by_id[aid]['title'], 'source_path': aid, 'chunk_index': 0, 'score': 1.0,
                'preview': by_id[aid]['content'][:240].strip(), 'bucket_label': by_id[aid]['bucket'], 'category_path': []}
               for i, aid in enumerate(order)]
    return text, sources


# ---- conversation ----
def history(session, changed):
    if changed:
        return []
    turns = [t for t in session['turns'] if t[3] == session['version']][-HISTORY_EXCHANGES:]
    msgs = []
    for question, answer, image_text, _, _ in turns:
        user = question[:4000] + (f'\n[Screenshot description: {image_text[:2000]}]' if image_text else '')
        msgs += [{'role': 'user', 'content': user}, {'role': 'assistant', 'content': answer[:6000]}]
    total, kept = 0, []
    for m in reversed(msgs):
        if total + len(m['content']) > HISTORY_CHARS:
            break
        kept.append(m)
        total += len(m['content'])
    kept.reverse()
    while kept and kept[0]['role'] != 'user':
        kept.pop(0)
    return kept


async def chat(rag, name, messages):
    import httpx
    s = rag.settings
    payload = {'model': s.chat_model, 'messages': messages, 'stream': False,
               'options': {'temperature': s.temperature, 'num_ctx': s.num_ctx, 'num_predict': 700}}
    with rag.langfuse.start_as_current_generation(name=name, model=s.chat_model, input=messages,
                                                  model_parameters={'temperature': s.temperature, 'num_ctx': s.num_ctx}):
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{s.ollama_base_url.rstrip('/')}/api/chat", json=payload)
        if response.status_code >= 400:
            raise rag.OllamaError('Model service could not complete the response.')
        try:
            content = (response.json().get('message') or {}).get('content')
        except ValueError:
            content = None
        if not isinstance(content, str) or not content.strip():
            raise rag.OllamaError('Model service returned no reply.')
        data = response.json()
        rag.langfuse.update_current_generation(output=content, usage_details={
            'input': data.get('prompt_eval_count'), 'output': data.get('eval_count')})
        return content.strip()


async def answer(rag, question, session, selection, image=None, issue_category=None):
    profile = session['profile']
    role = profile['role']
    with rag.langfuse.start_as_current_span(name='simple_answer', input={'question': question, 'has_image': bool(image)}) as trace:
        rag.langfuse.update_current_trace(tags=['mcele-hackathon-demo', 'curated-demo', 'simple-gated-rag'],
                                          session_id=session['id'], user_id=profile['id'])
        image_text = (await rag.extract_image_context(image)).get('description', '')[:4000] if image else ''
        previous = session.get('selected_course_id')
        changed = selection != previous and selection is not None and previous is not None
        course_id = selection or previous
        user = question + (f'\n[Screenshot description: {image_text}]' if image_text else '')
        past = history(session, changed)
        said = ' '.join([m['content'] for m in past if m['role'] == 'user'] + [user])
        scoped = in_scope(role, said, course_id)
        messages = [{'role': 'system', 'content': system_prompt(profile, course_id, scoped)},
                    *past, {'role': 'user', 'content': user}]
        draft = await chat(rag, 'simple_reply', messages)
        first = violations(draft, role)
        final, second, gate = draft, [], 'first'
        if first:
            fix = ('Your reply was not sent. These items are not supported by the articles or are not available to this user: '
                   + '; '.join(f'{k}: {v}' for k, v in first)
                   + '. Rewrite the reply without them. Copy labels, links and numbers exactly from an article and cite it, '
                     "or say the articles don't cover it and to contact the Help Desk. Reply with only the rewritten message.")
            repaired = await chat(rag, 'simple_repair', messages + [{'role': 'assistant', 'content': draft},
                                                                    {'role': 'user', 'content': fix}])
            second = violations(repaired, role)
            final, gate = (repaired, 'repaired') if not second else (drop_unsupported(repaired, second), 'stripped')
        text, sources = number_citations(final, role)
        context = {'selected_course_id': course_id, 'engine': 'simple-gated'}
        metadata = {'architecture': 'simple-gated-rag', 'role': role, 'course_id': course_id,
                    'allowed_article_ids': [a['id'] for a in scoped],
                    'cited_source_ids': [s['source_path'] for s in sources], 'gate': gate,
                    'first_violations': [f'{k}: {v}' for k, v in first][:20],
                    'repair_violations': [f'{k}: {v}' for k, v in second][:20]}
        rag.langfuse.update_current_trace(metadata=metadata)
        trace.update(metadata=metadata, output={'answer': text})
        return {'answer': text, 'response_kind': 'support', 'suggested_replies': [], 'sources': sources,
                'retrieved_count': len(sources), 'trace_id': rag.langfuse.get_current_trace_id(),
                'needs_clarification': text.rstrip().endswith('?'), 'matched_bucket_id': None, 'context': context,
                '_image_text': image_text, '_context_changed': changed}
