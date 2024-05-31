from flask import Flask, render_template, url_for, request, redirect, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from services.chatgpt import chat
import arrow
import random
import string
from hashlib import sha256
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:u1378755h%40U@localhost:3306/mchatbot'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://HuthaifaJanazreh:6JC0qH6eIF%3Az@HuthaifaJanazreh.mysql.pythonanywhere-services.com:3306/HuthaifaJanazreh$default'

db = SQLAlchemy(app)

class Conversations(db.Model):
    conversation_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    conversation_date = db.Column(db.Date, default=datetime.now())


    def __repr__(self):
        return '<Task %r>' % self.id
    
class Messages(db.Model):
    message_id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)
    message_content = db.Column(db.Text(), nullable=False)
    message_timestamp = db.Column(db.Date, default=datetime.now())
    message_type = db.Column(db.String(), nullable=False, default="user")
 

    def __repr__(self):
        return '<Task %r>' % self.id

class Users(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False)
    
    def __repr__(self):
        return '<User %r>' % self.user_id

# Define the index route to render the chat interface
@app.route("/") 
def index():
    user_id = request.cookies.get('user_id')
    user_name = request.cookies.get('user_name')
    if user_id: 
        conversations = Conversations.query.filter_by(user_id=user_id).order_by(Conversations.conversation_date).all()
        return render_template("index.html", conversations=conversations, user=user_name)
    else:
        return render_template("index.html", user=user_id) # user = None
    
@app.route("/topic", methods=["POST"])
def topic():
    id = 1
    topic = request.form['topic'].strip()
    if not topic:
        return 'Topic cannot be empty',400
    user_id = request.cookies.get('user_id')
    print(user_id)
    topic = Conversations(topic=topic, user_id=user_id)
    try:
      db.session.add(topic)
      db.session.commit()
      return redirect('/conversation/'+ str(topic.conversation_id))
    except:
        return 'There was an issue creating your topic, try again.'

@app.route("/conversation/<int:id>", methods=["POST","GET"])
def conversation(id):
    user_id = request.cookies.get('user_id')
    if user_id:
        conversations = Conversations.query.filter_by(user_id=user_id).order_by(Conversations.conversation_date).all()
        conversation = Conversations.query.get_or_404(id)
        messages = Messages.query.filter_by(conversation_id=id).order_by(Messages.message_timestamp).all()
        if request.method == 'POST':
            content = request.form['content']
            assistant_type = request.form['assistant_type']
            new_message = chat(message=content, assistant_type=assistant_type)
            # create user message in db
            user_message = Messages(conversation_id=id,sender_id=conversation.user_id, message_content=content, message_type="user")
            #  create chatgpt message in db 
            bot_message = Messages(conversation_id=id,sender_id=conversation.user_id, message_content=new_message, message_type="bot")

            try:
                db.session.add(user_message)
                db.session.add(bot_message)
                db.session.commit()
                return redirect('/conversation/'+ str(id))
            except:
                return 'There was an issue connecting with the chat bot, try again.'
        
        else:
            return render_template("conversation.html", conversations=conversations, conversation=conversation, messages=messages, arrow=arrow)
    else:
        # handle case where user is not logged in
        return redirect('/')

def generate_pin(size=6, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

@app.route('/signup', methods=['POST'])
def signup():
    user_pin = generate_pin()
    hashed_pin = sha256(user_pin.encode()).hexdigest() 
    user = Users(username=hashed_pin) # fetch he user id from user table based on user pin stored 
    try:
        db.session.add(user)
        db.session.commit()
        resp = make_response(redirect('/'))
        resp.set_cookie('user_name', str(user_pin)) # user.user_name
        resp.set_cookie('user_id', str(user.user_id)) # if user found ,... set the cookie and redirect to home page 
        return resp
    except:
            return 'There was an issue generating a PIN code, try again...'

@app.route('/login', methods=['POST'])
def login():
    user_pin = request.form['user_name']
    hashed_pin = sha256(user_pin.encode()).hexdigest()
    user = Users.query.filter_by(username=hashed_pin).first() 
    if user is None:   
        return redirect('/')   #  if user not found return to home page
    else:
        resp = make_response(redirect('/'))
        resp.set_cookie('user_name', str(user_pin))
        resp.set_cookie('user_id', str(user.user_id)) # if user found ,... set the cookie and redirect to home page 
        return resp

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.delete_cookie('user_id')
    resp.delete_cookie('user_name') 
    return resp

@app.route('/delete_user', methods=['POST'])
def delete():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect('/')
    
    try:
        # Delete messages sent by the user
        Messages.query.filter_by(sender_id=user_id).delete()
        
        # Delete conversations associated with the user
        Conversations.query.filter_by(user_id=user_id).delete()
        
        # Delete the user
        Users.query.filter_by(user_id=user_id).delete()
        
        # Commit the changes
        db.session.commit()
        
        # Clear cookies and redirect
        resp = make_response(redirect('/'))
        resp.delete_cookie('user_id')
        resp.delete_cookie('user_name')
        return resp
    except:
        # Rollback changes in case of an error
        db.session.rollback()
        return 'There was an issue deleting your data, please try again.' 
    

if __name__ == '__main__':
      
    app.run(debug=True)
