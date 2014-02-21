import os
import random,time
from bottle import *

from ext.bottle_mysql import MySQLPlugin

#Constants
DEBUGGING = True 
COOKIE_KEY = 'i_miss_kookies!'
COOKIE_NAME = 'auth'
MAX_EXAM_SECS = 60 * 30
MAX_EXAM_QUESTS = 47
#MAX_QUES = 78
ANS_SEPERATOR = '###'
ADMIN_USERNAME = 'root'

MYDIR = os.path.dirname(os.path.realpath(__file__))

static_path=MYDIR+'/static/'

class ExamStatus:
    unattented, attending, attened = range(3)


install(MySQLPlugin(dbuser='root', dbpass='', dbname='kmcq'))

def userSignedIn():
    return request.get_cookie(COOKIE_NAME, secret=COOKIE_KEY)

def getQidFromQno(qorder,qno):
    return qorder[qno-1] if qno>0 else 0

def updateUserStatus(udata,dbx=None):
    response.set_cookie(COOKIE_NAME,udata,COOKIE_KEY,path='/')
    if dbx:
        dbx.execute('update users set status=%s,tstart=%s,qorder=%s where id = %s',                    
                    (udata['status'],udata['tstart'],
                    ','.join(str(x) for x in udata['qorder']),udata['id']))
    
def putAnswer(uid,qid,ans,time,dbx):
    dbx.execute('select * from answers where uid=%s and qid=%s',(uid,qid))
    row=dbx.fetchone();
    if row:
        dbx.execute('UPDATE `answers` SET `choice`=%s,`time`=%s WHERE uid=%s and qid=%s',(ans,time,uid,qid))
    else:
        dbx.execute('insert into answers(uid,qid,choice,time) values(%s,%s,%s,%s)',(uid,qid,ans,time))

def getAnswer(uid,qid,dbx):
    dbx.execute('select choice from answers where uid=%s and qid=%s',(uid,qid))
    row=dbx.fetchone()
    return tuple(row.values()) if row is not None else None

def getQuestion(qid,dbx):
    dbx.execute('select question,options from questions where id = %s',(qid,))
    row=dbx.fetchone()
    #udb = tuple([tuple(i.values()) for i in (dbx.fetchall())])
    row=tuple(row.values())
   
    if row is not None:
        return row[0],row[1].split("###")
    else:
        return None,None

def getTimeleft(uid,dbx):
    dbx.execute('insert into answers(uid,qid,choice,time) values(%s,%s,%s,%s)',(uid,))
                
def authUser(username,password,dbx):
    dbx.execute('select id,qorder,status,tstart from users where username=%s and password=%s',
                   (username,password))
    udb=dbx.fetchall();
    #udb = tuple([tuple(i.values()) for i in (dbx.fetchall())])
    if udb:
        #udata=dict(zip(('id','qorder','status','tstart'), udb[0]))
        udata=udb[0]
        if udata['tstart'] and (time.time()-udata['tstart']) > MAX_EXAM_SECS:
            udata['status'] = ExamStatus.attened

        if udata['qorder']:
            udata['qorder'] = [int(q) for q in udata['qorder'].split(',')]
        return udata

    else:
        return False
    
def message(type,title,msg, login=False):
    return template('view/msg.html',type=type,title=title,text=msg,loggedIn=login)

def intval(x):
    return 0 if x=='' else int(x)
    

@route('/api/exam',method='POST')
def ret_question(db):
    usr=userSignedIn()    
    if usr is not None:
        qno = request.forms.get('qno')
        aqno = intval(request.forms.get('answerqno'))
        answer = intval(request.forms.get('answer'))
        answertime = intval(request.forms.get('answertime'))
        timeleft = intval(request.forms.get('timeleft'))
        
        if usr['status']==ExamStatus.unattented:           
            usr['status']=1
            usr['tstart']=int(time.time())            
            usr['qorder']=range(1,MAX_EXAM_QUESTS+1)
            #usr['qorder']=range(1,MAX_QUES+1)
            random.shuffle(usr['qorder']) 
            #usr['qorder']=usr['qorder'][0:MAX_EXAM_QUESTS]        
            updateUserStatus(usr,db)
                         
        if usr['status']==ExamStatus.attending:
            if aqno>0 and answer > 0 and qno=='submit':
                putAnswer(usr['id'],getQidFromQno(usr['qorder'],aqno), answer, timeleft,db)
            
            if qno in ['submit','pass']:                
                inextq = aqno if aqno  < MAX_EXAM_QUESTS else 0
            else:
                inextq = int(qno)-1
            if inextq < 0 or inextq >= MAX_EXAM_QUESTS:
                return {'err':'Please select a valid question'}    
            qid = usr['qorder'][inextq]
            quest,choices = getQuestion(qid,db)            
            answer = getAnswer(usr['id'], qid,db)
            timeleft = MAX_EXAM_SECS - (int(time.time())-usr['tstart'])
            
            return {'qno':inextq+1, 'question':quest,'choices':choices, 'answer':answer,'timeleft':timeleft}                 
        else:
            return {'err':'Your time is Up!','redirect':'/completed'}
    else:
        return {'err':'You session has expired, please login','redirect':'/login'}
        

@route('/api/qstatus')
def ret_qstatus(db):
    usr=userSignedIn()
    if usr is not None:
        stat={}
        quests = range(1,MAX_EXAM_QUESTS+1)
        db.execute('select qid from answers where uid=%s',(usr['id'],))
        sqr=db.fetchall()
        sqr = tuple(tuple(i.values()) for i in sqr)
        attempted = [q[0] for q in sqr]
        if usr['qorder']:
            for q in quests:
                if usr['qorder'][q-1] in attempted:
                    stat[q]='answered'
                else:
                    stat[q]=''
        else:
            stat={q:'' for q in quests}
        return template("""
                %for q in stat:
                <a href="{{q}}" class="{{stat[q]}}">{{q}}</a>
            """,stat=stat)
    else:
        return '<script>window.location="/logout"</script>'

@route('/questions')
def ret_questions(db):
    usr=userSignedIn()
    if usr is not None: 
        return template('view/questions.html')
    else:
        redirect('/login')

@route('/completed')
def finish_exam(db):
    usr=userSignedIn()
    if usr is not None:
        usr['status']=ExamStatus.attened
        updateUserStatus(usr,db)
        return message('terminal', 'Exam finished', 
                       'You have finished the exam.<br><tt class="swars">May the source be with you</tt>', 
                       True)
    else:
        redirect('/login')

@route('/login')
def show_login():
    return template('view/login.html',InvalidLogin=False)

@route('/login',method='POST')
def do_login(db):
    submitted = request.forms.get('submit')
    if submitted != None:
        username = request.forms.get('username')
        password = request.forms.get('password')
        udata=authUser(username,password,db)    
        if not udata:
            return template('view/login.html',InvalidLogin=True)
        else:
            if username == ADMIN_USERNAME: 
                udata['god']=True 
            updateUserStatus(udata)            
            redirect('/')
    return "F*** you"


@route('/logout')
def do_logout():
    response.delete_cookie(COOKIE_NAME)
    return message('info text-center','',"You have logged out.<br><br><a href='/' class='btn btn-default btn-primary'>Login again ?</a>")


@route('/exam-home')
def show_exam_intro():
    usr=userSignedIn()
    if usr is not None:
        return template('view/exam-home',ExamWritten=usr['status']==ExamStatus.attened)
    else:
        redirect('/login')
      

#Show The Result  God Mod
@route('/god')
def show_exam_intro(db):
    usr=userSignedIn()
    if usr is not None and 'god' in usr:
        sql="""select uid,users.username,count(*) as asd from answers 
                    left join users on answers.uid = users.id
                    left join questions on answers.qid = questions.id
                    where answers.choice = questions.answer
                    group by answers.uid order by asd desc
            """
        db.execute(sql)
        results=db.fetchall()

        results=tuple([tuple(i.values()) for i in results])
        return template('view/score.html',title='Result',loggedIn=True, results=results)
    else:
        redirect('/login')

@route('/admin')
def admininterface():
    usr=userSignedIn()
    if usr is not None and 'god' in usr:
        return template('view/admin.html')
    else:
        redirect('/login')    
    


@route('/useradd')
def showuseradd(db):
    usr=userSignedIn()
    if usr is not None and 'god' in usr:
        sql="select id,username from users order by id"
        db.execute(sql)
        results=db.fetchall()
        results=tuple([tuple(i.values()) for i in results])
        return template('view/adduser.html',title='Admin',loggedIn=True,results=results,error=False)
    else:
        redirect('/login')


@route('/useradd',method='POST')
def douseradd(db):
    usr=userSignedIn()
    if usr is not None and 'god' in usr:
        uid = request.forms.get('id')
        username = request.forms.get('username')
        password = request.forms.get('password')
        error=False

        try:
            db.execute('INSERT INTO `users`(`id`,`username`, `password`) VALUES (%s,%s,%s)',(uid,username,password))
            sql="select id,username from users order by id"
            db.execute(sql)
            results=db.fetchall()
            results=tuple([tuple(i.values()) for i in results])
        except :
            sql="select id,username from users order by id"
            db.execute(sql)
            results=db.fetchall()
            results=tuple([tuple(i.values()) for i in results])
            return template('view/adduser.html',title='Admin',loggedIn=True,results=results,error=True)
        return template('view/adduser.html',title='Admin',loggedIn=True,results=results,error=False)
        
    else:
        redirect('/login')





@route('/')
def do_index():
    usr=userSignedIn()
    if usr is not None:
        redirect('/admin' if 'god' in usr else '/exam-home')
    else:
        redirect('/login')


@route('/js/exams.js')
def getJSFile():
    return template('static/js/exams.js',MAX_EXAM_SECS=MAX_EXAM_SECS)


#serves Static Files

@route('/<path:path>')
def serve_static(path):
    return static_file(path,static_path)


if __name__ == '__main__':
    if DEBUGGING:
        run(host='localhost', port=8090,debug=True,reloader=True)
    else:
        run(host='localhost', port=8090)


