import bcrypt
from flask import Flask,render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from forms import *
from flask_bcrypt import Bcrypt
from datetime import datetime,date
import matplotlib.pyplot as plt
from dateutil import parser

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///database.sqlite3"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['SECRET_KEY']='619619'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager=LoginManager(app)


class User(db.Model,UserMixin):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(20),unique=True)
    email=db.Column(db.String(200),unique=True)
    password=db.Column(db.String(200))
    trackers=db.relationship('Tracker', backref='user')

    def __repr__(self) -> str:
        return f"User('{self.username}', '{self.email}',)"

class Tracker(db.Model):
    sno=db.Column(db.Integer,primary_key=True )
    title=db.Column(db.String(200),nullable=False)
    type=db.Column(db.String(200),nullable=False)
    desc=db.Column(db.String(500),nullable=False)
    date=db.Column(db.DateTime,default=datetime.utcnow)
    settings=db.Column(db.String(300), nullable=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"))
    logs = db.relationship('Log', backref='tracker')


    def __repr__(self) -> str:
        return f"Tracker('{self.sno}', '{self.title}')"

class Log(db.Model):
    logno = db.Column(db.Integer, primary_key=True)
    tracker_id = db.Column(db.Integer, db.ForeignKey("tracker.sno"))
    value = db.Column(db.String(50))
    timestamp= db.Column(db.DateTime, default=datetime.utcnow)
    note=db.Column(db.String(200))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/home', methods=['GET','POST'])
#@login_required
def index():
    if current_user.is_authenticated:
        id=current_user.id
        if request.method=='POST': 
            title = request.form['title']
            type = request.form['type']
            desc = request.form['desc']
            now= datetime.now()
            s=""
            if (type=='mul'):
                s= request.form['settings']
            tracker=Tracker(title=title,type=type,desc=desc,settings=s, user_id=id, date=now)
            db.session.add(tracker)
            db.session.commit()
        alltrackers = Tracker.query.filter_by(user_id=id).all()
        return render_template('index.html', alltrackers=alltrackers)
    else: return redirect(url_for('login'))

@app.route("/addlog/<sno>", methods=['GET','POST'])
@login_required
def add_log(sno):
    tracker= Tracker.query.filter_by(sno=sno).first()
    if request.method=='GET':
        name= tracker.title
        types= tracker.type
        now= datetime.now().strftime("%Y-%m-%dT%H:%M")
        print(now)
        settings= tracker.settings
        if settings:
            options= settings.strip().split(',')
            print(options)
            return render_template("addlog.html", name=name, type=types, options=options, now=now, sno=sno)
        else:
            return render_template("addlog.html", name=name, type=types, now = now, sno=sno)
       
    elif request.method=='POST':
        tim=request.form.get("time")
        time=parser.parse(tim)
        tracker.date= date.today()
        if tracker.type=='num':
            value= int(request.form.get("input")) * 2
        else:
            value= request.form.get("input")
        note=request.form.get("note")
        log=Log(tracker_id=sno,value=value,note=note, timestamp=time)
        db.session.add(log)
        db.session.commit()
        logs = Log.query.filter_by(tracker_id=sno)
        return redirect(url_for('show_logs', sno=sno))

@app.route("/showlogs/<sno>", methods=['GET','POST'])
@login_required
def show_logs(sno):
    if request.method=='GET':
        logs = Log.query.filter_by(tracker_id=sno).all()
        col=[]
        col2=[]
        for log in logs:
            time=log.timestamp
            time=time.strftime("%d/%m/%y")
            col.append(time)
            col2.append(log.value)
        
        #generate plot
        # Define X and Y variable data
        y = col2
        plt.hist(y)
        plt.xlabel("Times")  # add X-axis label
        plt.ylabel("Value")  # add Y-axis label
        plt.savefig("static/graph.png")   
        plt.switch_backend('agg')  

        return render_template("showlogs.html", sno=sno, logs=logs)


@app.route("/signup", methods=['GET','POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data,password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Your account has been created! You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', title='Signup', form=form)

@app.route('/', methods=['GET','POST'])
@app.route("/login", methods=['GET','POST'])
def login():
    form = LoginForm()
    if request.method=="POST":
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('index'))
            else:
                flash('Login Unsuccessful. Please check email and password!!', 'danger')
    return render_template('login.html', title='Login', form=form)



@app.route("/logout",methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/update/<int:sno>", methods=['GET','POST'])
@login_required
def update(sno):
    if request.method=='POST':
        title = request.form['title']
        desc = request.form['desc']
        tracker = Tracker.query.filter_by(sno=sno).first()
        tracker.title=title
        tracker.desc=desc
        tracker.date= datetime.now()
        db.session.commit()
        return redirect(url_for('index'))

    tracker = Tracker.query.filter_by(sno=sno).first()
    return render_template('update.html', tracker=tracker)


@app.route("/delete/<int:sno>")
@login_required
def delete(sno):
    tracker = Tracker.query.filter_by(sno=sno).first()
    db.session.delete(tracker)
    db.session.commit()
    return redirect('/home')

@app.route("/updatelog/<int:logno>", methods=['GET','POST'])
@login_required
def update_log(logno):
    
    log= Log.query.filter_by(logno=logno).first()
    tracker_id = log.tracker_id
    tracker= Tracker.query.filter_by(sno=tracker_id).first()
    if request.method=='GET':
        trackername= tracker.title
        type= tracker.type
        settings= tracker.settings
        options=[]
        if settings:
            options= settings.strip().split(',')
        return render_template('updatelog.html', trackername=trackername, log=log, type=type, options=options)
    if request.method=='POST':
        time=request.form.get("timestamp")
        timestamp= parser.parse(time)
        value=request.form.get("value")
        note=request.form.get("note")
        log.timestamp=timestamp
        log.value=value
        log.note= note 
        tracker.date= date.today()
        db.session.commit()
        logs = Log.query.filter_by(tracker_id=tracker_id)
        return redirect(url_for("show_logs", sno=tracker_id))



@app.route("/deletelog/<logno>", methods=['GET', 'POST'])
@login_required
def delete_log(logno):
    log = Log.query.filter_by(logno=logno).first()
    print(log)
    id=log.tracker_id
    db.session.delete(log)
    db.session.commit()
    logs = Log.query.filter_by(tracker_id=id).all()
    return redirect(url_for('show_logs', sno=id))

if __name__=="__main__":
    app.run(debug=True, port=8000)