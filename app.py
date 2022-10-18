import os
import psycopg2, psycopg2.extras
import hashlib
from flask import Flask, render_template, session, request
from flask_session import Session
from flask_recaptcha import ReCaptcha
from werkzeug.utils import secure_filename
import app_config

import json
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

w3 = Web3(HTTPProvider('https://ropsten.infura.io/v3/0ba47a68dee04243bfa4b69d148ede22'))
print(w3.isConnected())

contract_address = Web3.toChecksumAddress('0xb04F7A9910b21fA707f1d39A55c4A9AC389F0ECB')

key='insert your private key'
account_address = Web3.toChecksumAddress('0x81676973515a3e1e4BE74923b1b0c001844f3aa6')
w3.eth.defaultAccount = account_address

myContract = json.load(open('./build/contracts/VerifyDoc.json'))
abi = myContract['abi']
bytecode = myContract['bytecode']

contract = w3.eth.contract(bytecode=bytecode, abi=abi)
contract_instance = w3.eth.contract(abi=abi, address=contract_address)

app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

conn = psycopg2.connect(user="postgres", password="root", host="localhost", database="blockchain")
cursor = conn.cursor() #create cursor to perform database operations

app.secret_key = "MySecretKey"
UPLOAD_FOLDER= "C:/Users/pc/dapp/static/uploads/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024 
app.config["ALLOWED_EXTENSIONS"]= ["pdf"]
app.config["RECAPTCHA_SITE_KEY"]="6LfVW1QdAAAAAOxXvddlwp7GNFPclqZAIeUoNi4q"
app.config["RECAPTCHA_SECRET_KEY"]="6LfVW1QdAAAAALmXuhn4iqApa74MOFGGY3idk-y3"
recaptcha = ReCaptcha(app)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/adminsignin", methods = ["POST", "GET"])
def adminsignin():
    
    error = ""
    
    if request.method == "POST":
        
        username = request.form["username"] 
        pwd = request.form["pwd"]
        hashed_pwd = hashlib.sha512(pwd.encode("utf-8")).hexdigest()

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        postgres_select_query = "SELECT * FROM admin WHERE username = %s AND password = (SELECT CAST(%s AS text))"
        cursor.execute(postgres_select_query, (username,hashed_pwd))
        account = cursor.fetchone() #fetch result
        
        if account:
            session["loggedin"] = True
            session["id"] = account["id"]
            session["username"] = account["username"]
            return render_template("issuerecord.html")
        elif username == '' and pwd == '':
            error = 'Please fill in username and password'
        elif pwd == '':
            error = 'Please fill in password'
        elif username == '':
            error = 'Please fill in username'
        else:
            error = "Incorrect username/password"

    return render_template("adminsignin.html", error = error)

@app.route("/issuerecord")
def issuerecord():

    error = ''

    if 'username' in session:
        return render_template('issuerecord.html')
    else :
        error = "Please log in first"
        return render_template('adminsignin.html', error = error)

def allowed_file(filename):

    ext = filename.rsplit('.', 1)[1]

    if '.' in filename and ext in app.config["ALLOWED_EXTENSIONS"]:
        return True

@app.route ("/upload", methods = ["POST", "GET"])
def upload():

    error="" 
    success=""
    message=""    
    
    if request.method == 'POST' and 'username' in session:
        file = request.files['file']

        if 'file' not in request.files:
            error = 'No file detected'
        elif file.filename == '':
            error = 'No filename detected'
        elif file and allowed_file(file.filename):

            filename = file.filename
            print('Filename is', filename)

            file_hash = hashlib.sha256()
            bytes = file.read()
            file_hash.update(bytes)
            readable_hash = file_hash.hexdigest()
            print('Hash of document is', readable_hash)

            tx = contract_instance.functions.getHash(readable_hash).call()
            if tx:
                error = 'Document exists in blockchain'
            else:
                tx = contract_instance.functions.issueCertificate(readable_hash).buildTransaction({'nonce':w3.eth.getTransactionCount(account_address)})
                signed_tx = w3.eth.account.signTransaction(tx,key)
                tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
                tx_original = tx_hash.hex()
                print('Transaction hash:',tx_original)

                tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
                message = tx_original
            return render_template("issuerecord.html", error = error, success = success, message = message, hash = readable_hash, filename = filename)  
        else:
            error = 'Only document with .pdf extension is accepted'
        return render_template("issuerecord.html", error = error )
    else:
        error = "Please log in first."
        return render_template('adminsignin.html',error = error)

@app.route ("/adminlogout")
def adminlogout():

    #remove session data
    session.pop("loggedin", None) 
    session.pop("id", None)
    session.pop("username", None)

    return render_template("home.html")

@app.route("/orgsignup", methods=["POST","GET"])
def orgsignup():

    error="" 
    success=""

    if request.method == "POST":

        orgname = request.form.get("orgname") 
        email = request.form.get("email")
        pwd = request.form.get("pwd")
        confirm_pwd = request.form.get("confirm_pwd")
        
        postgres_select_query = "SELECT * FROM org WHERE email= %s"
        cursor.execute(postgres_select_query, (email,))
        account = cursor.fetchone()
        #validation
        if account:
            error = "Email already exist"
        elif orgname == '' or email == '' or pwd == '' or confirm_pwd =='':
            error = 'Please fill in the credentials'
        elif pwd != confirm_pwd:
            error = "Password does not match"
        elif not recaptcha.verify():
            error = "reCAPTCHA verification failed"
        else:
            hashed_pwd = hashlib.sha512(pwd.encode("utf-8")).hexdigest()
            postgres_insert_query = "INSERT INTO org(organization_name, email, password) VALUES (%s, %s, %s)"
            cursor.execute(postgres_insert_query, (orgname, email, hashed_pwd))
            conn.commit()
            success = "Registration successful"
            return render_template("orgsignin.html", success=success)

    return render_template("orgsignup.html", error = error)

@app.route("/orgsignin", methods = ["POST", "GET"])
def orgsignin():
    
    error = ""
    
    if request.method == "POST":
        
        orgname = request.form["orgname"] 
        pwd = request.form["pwd"]
        hashed_pwd = hashlib.sha512(pwd.encode("utf-8")).hexdigest()

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        postgres_select_query = "SELECT * FROM org WHERE organization_name = %s AND password = (SELECT CAST(%s AS text))"
        cursor.execute(postgres_select_query, (orgname,hashed_pwd))
        account = cursor.fetchone() #fetch result
        
        if account:
            session["loggedin"] = True
            session["id"] = account["id"]
            session["orgname"] = account["organization_name"]
            return render_template("verifynow.html")
        elif orgname == '' and pwd == '':
            error = 'Please fill in username and password'
        elif pwd == '':
            error = 'Please fill in password'
        elif orgname == '':
            error = 'Please fill in username'
        else:
            error = "Incorrect username/password"

    return render_template("orgsignin.html", error = error)

@app.route ("/orglogout")
def orglogout():

    #remove session data
    session.pop("loggedin", None) 
    session.pop("id", None)
    session.pop("orgname", None)

    return render_template("home.html")

@app.route("/verifynow")
def verifynow():

    error = ''

    if 'orgname' in session:
        return render_template('verifynow.html')
    else :
        error = "Please log in first."
        return render_template('orgsignin.html', error = error)

@app.route("/verify", methods = ["POST","GET"])
def verify():

    error=""     
    
    if request.method == 'POST' and 'orgname' in session:
        file = request.files['file']

        if 'file' not in request.files:
            error = 'No file detected'
        elif file.filename == '':
            error = 'No filename detected'  
        elif file and allowed_file(file.filename):
            
            file_hash2 = hashlib.sha256()
            bytes = file.read()
            file_hash2.update(bytes)
            readable_hash2 = file_hash2.hexdigest()
            print('hash of file is', readable_hash2)

            tx = contract_instance.functions.getHash(readable_hash2).call()
            if tx:
                return render_template("success.html", hash2 = readable_hash2)  
            else:
                return render_template("fail.html")
            
        else:
            error = 'Only document with .pdf extension is accepted'
        return render_template("verifynow.html", error = error)
    else:
        error = "Please log in first."
        return render_template('orgsignin.html',error = error)

if __name__ == "__main__":
    app.run()
