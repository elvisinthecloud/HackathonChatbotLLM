"""Local-only simulated preview; never connects to Atlas, Ollama, Jira, or a database."""
import sys, secrets, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'tests'),str(root/'backend')]
from test_ticket_handoff import import_api
api=import_api()
from fastapi.staticfiles import StaticFiles
from demo_policy import PROFILES,resolve_context
sessions={}
def create(profile,course):
 if profile not in PROFILES:raise ValueError()
 token=secrets.token_urlsafe(32)
 sessions[token]={'id':'local-'+secrets.token_hex(8),'profile':PROFILES[profile],'context':{},'selected_course_id':course,'version':0,'turns':[]}
 return {'session_id':token,'profile':PROFILES[profile]}
def load(token):
 if token not in sessions:raise api.SessionMissing()
 return sessions[token]
def save(session,course,context,changed,question,image_text,had_image,result):
 session['version']+=int(changed)
 session['context']=context;session['selected_course_id']=course
 session['turns'].append((question,result['answer'],image_text,session['version'],context))
async def answer(question,session,selected_course_id,image=None,selected_system=None,issue_category=None):
 context,conflict,changed=resolve_context(selected_course_id,session['context'],session['selected_course_id'],question,selected_system=selected_system)
 return {'answer':conflict or 'Local preview: your issue is recorded. You can add details or contact the Help Desk.',
 'sources':[],'retrieved_count':0,'trace_id':None,'context':context,'_context_changed':changed,'_image_text':''}
api.create_session=create;api.load_session=load;api.save_turn=save;api.answer_question=answer
api.app.mount('/',StaticFiles(directory=str(root/'frontend'),html=True),name='frontend')
import uvicorn
uvicorn.run(api.app,host='127.0.0.1',port=8765,lifespan='off',access_log=False)
