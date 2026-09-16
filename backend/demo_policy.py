"""Server-owned simulated identities and explicit, non-inherited article access."""
from contextvars import ContextVar
from dataclasses import dataclass
import re

COURSES = {
    'CYBERM0000': {'id':'CYBERM0000','title':'CYBERM0000 biennial training','aliases':['CYBERM0000'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':None},
    '5500': {'id':'5500','title':'Sergeants School Seminar Program','aliases':['5500','EPME5500','Sergeants School Seminar','Sergeants School Seminar Program'], 'discovery_portal':'MCeLE','content_area':'Moodle','enrollment_area':'MCeLE'},
    '6800': {'id':'6800','title':'SNCO Leadership School Seminar','aliases':['6800','EPME6800','SNCO Leadership School Seminar'], 'discovery_portal':'MCeLE','content_area':None,'enrollment_area':'MCeLE'},
    'EPME3000': {'id':'EPME3000','title':'Leading Marines DEP','aliases':['EPME3000','EPME3000AA','Leading Marines','Leading Marines DEP'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':'MCeLE'},
    'EPME4000': {'id':'EPME4000','title':'Corporals Course DEP','aliases':['EPME4000','EPME4000AA','Corporals Course','Corporals Course DEP'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':'MCeLE'},
    'EPME5000': {'id':'EPME5000','title':'Sergeants School DEP','aliases':['EPME5000','EPME5000BA','Sergeants School DEP'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':'MCeLE'},
    'EPME6000': {'id':'EPME6000','title':'Career Course DEP','aliases':['EPME6000','EPME6000BA','Career Course DEP'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':'MCeLE'},
    'CSC': {'id':'CSC','title':'Command and Staff (CSC)','aliases':['CSC','Command and Staff','Command and Staff (CSC)'], 'discovery_portal':'MCeLE','content_area':'Moodle','enrollment_area':'MCeLE'},
    'EWS': {'id':'EWS','title':'EWS','aliases':['EWS','expiditionary school warfare'], 'discovery_portal':'MCeLE','content_area':'Moodle','enrollment_area':'MCeLE'},
    'CDETBAIC01': {'id':'CDETBAIC01','title':'Basic AI Course','aliases':['CDETBAIC01','Basic AI Course'], 'discovery_portal':'MCeLE','content_area':'MCeLE','enrollment_area':'MCeLE'},
}

PROFILES = {
    'student': {'id':'student','name':'Demo Student','role':'Student','display_role':'Student','course_ids':['CYBERM0000'],'delivery_areas':['MCeLE']},
    'instructor': {'id':'instructor','name':'Demo Instructor','role':'Adjunct Faculty','display_role':'Instructor','course_ids':[],'delivery_areas':['Moodle']},
    'ao': {'id':'ao','name':'Demo Academics Officer','role':'Academics Officer','display_role':'Academics Officer (AO)','course_ids':[],'delivery_areas':['Moodle']},
    'training-manager': {'id':'training-manager','name':'Demo Training Manager','role':'Training Manager','display_role':'Training Manager','course_ids':['5500','6800'],'delivery_areas':['MCeLE']},
    'regional-director': {'id':'regional-director','name':'Demo Regional Director','role':'Regional Director','display_role':'Regional Director','course_ids':[],'delivery_areas':[]},
}
# These are independent grants. Profile course associations are context hints only.
ARTICLE_POLICY = {
    'MCELE-LAUNCH-001': ('Student','MCeLE','general',()),
    'MOODLE-COPY-002': ('Adjunct Faculty','Moodle','general',()),
    'MOODLE-COPY-001': ('Academics Officer','Moodle','general',()),
    'MOODLE-COPY-003': ('Academics Officer','Moodle','general',()),
    'MCELE-ECDEP-001': ('Training Manager','MCeLE','courses',('5500','6800')),
    'MCELE-ENROLLMENT-REPORT-001': ('Training Manager','MCeLE','general',()),
    'MCELE-RRC-001': ('Student','MCeLE','general',()),
    'MCELE-EPME-001': ('Student','MCeLE','courses',('EPME3000','EPME4000','EPME5000','EPME6000','5500','6800')),
    'MCELE-CSC-001': ('Student','MCeLE','courses',('CSC',)),
}
ERROR_HOST = 'sts1.auth.ecuf.deas.mil'

@dataclass(frozen=True)
class RetrievalAccess:
    role: str
    delivery_area: str | None
    course_id: str | None
    article_ids: tuple[str, ...]

ACCESS: ContextVar[RetrievalAccess | None] = ContextVar('demo_retrieval_access', default=None)
ACCESS_FILTER_SQL = """
    a.metadata->>'dataset_id' = 'mcele-curated-v1'
    AND a.metadata->'allowed_roles' @> %s::jsonb
    AND a.metadata->>'service_area' = %s
    AND a.source_path = ANY(%s::text[])
"""

def access_parameters():
    import json
    access = ACCESS.get()
    if access is None:
        raise RuntimeError('Retrieval requires server-resolved demo access')
    return [json.dumps([access.role]), access.delivery_area, list(access.article_ids)]


def exact_error(text: str) -> bool:
    # Error evidence must include the hostname and message, not a vague launch failure.
    text = re.sub(r'\s+', ' ', text.lower())
    return bool(re.search(r'(?<![a-z0-9.])sts1\.auth\.ecuf\.deas\.mil[\s\"\u201c\u201d:\-]*refused to connect\b', text))


def find_course(query: str | None) -> str | None:
    if not query:
        return None
    normalized=re.sub(r"\s+", " ", query).strip().casefold()
    for cid,course in COURSES.items():
        names=[cid,course['title'],cid+' · '+course['title'],*course['aliases']]
        if normalized in [name.casefold() for name in names]:
            return cid
    return None


def course_mentions(text: str) -> list[str]:
    found=[]
    for cid,course in COURSES.items():
        if any(re.search(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',text,re.I) for name in [cid,course['title'],*course['aliases']]):
            found.append(cid)
    return found


def task_activity(text: str) -> str | None:
    management=bool(re.search(r'\b(?:copy|copying|create|creating|AO|academics officer|permissions?|MClearn)\b',text,re.I))
    enrollment=bool(re.search(r'\b(?:enroll\w*|eligib\w*|prerequisit\w*|recommend|deny|11580|NAVMC)\b',text,re.I)) or bool(re.search(r'\b(?:seminar|EPME\w*|PME|ECDEP)\b',text,re.I) and re.search(r'\b(?:request|approv\w*|requirements?|qualif\w*|take|start)\b',text,re.I))
    content=bool(re.search(r'\b(?:launch\w*|content|lesson|refused to connect|screenshot|error)\b',text,re.I))
    credit=bool(re.search(r'\b(?:RRC|Reserve Retirement Credits?|retirement points?|SAT year|anniversary year|calendar year|fiscal year)\b',text,re.I))
    if management and enrollment:
        return 'ambiguous'
    if management:return 'course-management'
    if credit:return 'course-credit'
    if enrollment:return 'enrollment'
    if content:return 'course-content'
    return None


def resolve_context(selected: str | None, previous: dict, previous_selected: str | None,
                    question: str, image_text: str = '') -> tuple[dict, str | None, bool]:
    selected=(selected or '').strip() or None
    if selected and len(selected)>160:
        raise ValueError('Course query is too long')
    chosen=find_course(selected)
    unknown=bool(selected and not chosen)
    changed_selection=selected != previous_selected
    mentions=course_mentions(question+'\n'+image_text)
    question_moodle=bool(re.search(r'\bmoodle\b',question,re.I))
    screenshot_moodle=bool(re.search(r'\bmoodle\b',image_text,re.I))
    activity=task_activity(question)
    csc_context=chosen=='CSC' or mentions==['CSC']
    if csc_context and re.search(r"\b(?:access|get to|missing|not (?:appear|show)|doesn't (?:appear|show)|can't find|cannot find|where is|My Courses|Moodle)\b",question,re.I):
        # CSC discovery/enrollment begins in MCeLE even though its content opens in Moodle.
        activity='enrollment'
    course_id=chosen or (mentions[0] if len(mentions)==1 and not unknown else None)
    # An explicitly new, general Moodle task may leave an automatically inferred course.
    if not course_id and not unknown and not changed_selection and not (question_moodle and activity and activity!=previous.get('activity')):
        course_id=previous.get('course_id')
    course_changed=changed_selection or course_id != previous.get('course_id')
    if activity is None and not course_changed:
        activity=previous.get('activity')
    if activity is None and image_text:
        activity=task_activity(image_text)
    course=COURSES.get(course_id,{})
    system=None
    if course:
        if activity=='course-credit':
            system='MCeLE'
        else:
            system=course.get('enrollment_area') if activity=='enrollment' else (course.get('content_area') if activity in ('course-content','course-management') else None)
    else:
        if question_moodle or screenshot_moodle:
            system='Moodle'
        if re.search(r'\b(?:in|on|through|delivered by|hosted by)\s+mcele\b',question,re.I):
            system='MCeLE'
        if activity=='enrollment' and re.search(r'\b(?:ECDEP|EPME\w*|PME|seminar)\b',question,re.I):
            system='MCeLE'
        if activity=='enrollment' and re.search(r'\b(?:Enrollment Report|enrollment status|verify (?:a )?Marine)\b',question,re.I):
            system='MCeLE'
        if activity=='course-credit':
            system='MCeLE'
        if not system and not course_changed and activity==previous.get('activity'):
            system=previous.get('system_area')
    if not system and not course_changed and activity==previous.get('activity') and not previous.get('unresolved'):
        system=previous.get('system_area')
    # A user may clarify a registry gap for this conversation without rewriting course records.
    if not system and activity and activity != 'ambiguous':
        if question.strip().casefold() == 'moodle' or re.search(r'\b(?:in|on)\s+moodle\b',question,re.I):
            system='Moodle'
        elif question.strip().casefold() == 'mcele' or re.search(r'\b(?:in|on)\s+mcele\b',question,re.I):
            system='MCeLE'
    context={'course_id':course_id,'course_title':course.get('title') or selected,'course_query':selected,
             'course_known':bool(course), 'activity':activity if activity!='ambiguous' else None,
             'system_area':system,'delivery_area':course.get('content_area'),
             'enrollment_area':course.get('enrollment_area'),'discovery_portal':course.get('discovery_portal')}
    conflict=len(mentions)>1 or bool(chosen and mentions and mentions!=[chosen])
    # For known courses, task mapping wins over a casual mention of the other portal.
    # Explicit contradictory task location or screenshot evidence must be clarified.
    explicit_wrong_moodle=bool(system=='MCeLE' and (screenshot_moodle or
        (question_moodle and activity=='course-content') or re.search(r'(?:enrollment|request) (?:page|screen|form).{0,12}(?:in|on)\s+moodle',question,re.I)))
    explicit_wrong_mcele=bool(system=='Moodle' and re.search(r'(?:content|course window).{0,15}(?:running|displayed|opens)\s+(?:in|on)\s+mcele',question,re.I))
    conflict=conflict or explicit_wrong_moodle or explicit_wrong_mcele or activity=='ambiguous'
    if conflict:
        context['unresolved']=True
        return context,'The course, task, and system details conflict. Are you working on enrollment in MCeLE or course content/management in Moodle? Please confirm the task and change or clear the course field if needed.',True
    changed=course_changed or bool(previous.get('unresolved')) or any(context.get(k)!=previous.get(k) for k in ('activity','system_area'))
    if not activity:
        return context,'What are you trying to do with this course: enroll or manage an enrollment request, launch/access course content, or copy/manage the course?',changed
    if not system:
        context['unresolved']=True
        return context,'I do not have a confirmed system mapping for this course and task yet. Does this step open in MCeLE or Moodle? Please specify the system and task; a course listing in the MCeLE catalog alone is not enough.',True
    return context,None,changed


def resolve_access(profile: dict, context: dict, evidence: str) -> RetrievalAccess:
    role=profile['role']
    area,course=context.get('system_area'),context.get('course_id')
    enrollment_report=bool(re.search(r'\b(?:Enrollment Report|enrollment status|verif\w+.{0,30}enroll\w*)\b',evidence,re.I))
    activities={'MCELE-LAUNCH-001':'course-content','MOODLE-COPY-002':'course-management',
                'MOODLE-COPY-001':'course-management','MOODLE-COPY-003':'course-management',
                'MCELE-ECDEP-001':'enrollment','MCELE-ENROLLMENT-REPORT-001':'enrollment',
                'MCELE-RRC-001':'course-credit','MCELE-EPME-001':'enrollment',
                'MCELE-CSC-001':'enrollment'}
    ids=tuple(aid for aid,(grant,delivery,scope,courses) in ARTICLE_POLICY.items()
              if role==grant and area==delivery and not context.get('unresolved')
              and context.get('activity')==activities[aid]
              and (scope=='general' or course in courses or (course is None and not context.get('course_query')))
              and (aid!='MCELE-ENROLLMENT-REPORT-001' or enrollment_report)
              and (aid!='MCELE-ECDEP-001' or not enrollment_report)
              and (aid!='MCELE-CSC-001' or course=='CSC')
              and (aid!='MCELE-LAUNCH-001' or exact_error(evidence)))
    return RetrievalAccess(role,area,course,ids)


def clarification(profile: dict, context: dict, evidence: str) -> str | None:
    if profile['role']=='Regional Director':
        return 'Regional Director is a presentation placeholder. No knowledge articles are assigned to this demo role yet.'
    if profile['role']=='Student' and context.get('system_area')=='MCeLE' and context.get('activity')=='course-content' and not exact_error(evidence):
        return 'Please attach a screenshot or type the exact error shown when the course fails to launch. A launch failure alone is not enough to choose the right troubleshooting steps.'
    return None
