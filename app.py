from flask import Flask, flash
from random import randint
from flask import Flask, render_template, request, Response, redirect, send_file, session, url_for
from flask_login import LoginManager, login_required, UserMixin, current_user, login_user, logout_user
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
import os
import cv2
import numpy as np
import csv
import face_recognition
from deepface import DeepFace
from datetime import datetime
# import pyshine as ps
import timeit
import time
from playsound import playsound
import pandas as pd
import plotly
import plotly.express as px
import json
from flask import Flask, request, render_template, jsonify
from chatbot_routes import chatbot_bp
from models import db, employee, users, UnansweredQuestion
import chardet
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# تسجيل البلوبرينت في التطبيق



app = Flask(__name__)

# configurations for database and mail
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///EmployeeDB.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '654@gmail.com'
app.config['MAIL_PASSWORD'] = 'facerecogManisha'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail_ = Mail(app)


# تسجيل البلوبرينت
app.register_blueprint(chatbot_bp, url_prefix="/chatbot")

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(user_id)


# employee database
class employee(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    hiringDate = db.Column(db.String(10), default=datetime.now().strftime("%d-%m-%Y"))

    def __repr__(self) -> str:
        return f"{self.id} - {self.name} - {self.department} - {self.email} - {self.hiringDate}"


# users/owner database
class users(db.Model, UserMixin):
    id = db.Column(db.String(20), primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(80), nullable=True)
    mail = db.Column(db.String(80), nullable=True)
    password = db.Column(db.String(80), nullable=False)
    dateCreated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<User {}>'.format(self.username)

# تعريف جدول الأسئلة غير المجابة
class UnansweredQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    answer = db.Column(db.String(255), nullable=True)

# نموذج لجدول الحضور
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)  # مفتاح أساسي تلقائي الزيادة
    employee_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)

# إنشاء الجدول إذا لم يكن موجودًا
with app.app_context():
    db.create_all()


path = 'static/TrainingImages'


@app.route('/')
def index():
    try:
        cap.release()
    except:
        pass
    try:
        cap2.release()
    except:
        pass
    return render_template('index.html')


# user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.query.filter_by(username=username).first()
        # if user exist in database then login otherwise back to login page a message
        if user is not None and user.password == password:
            login_user(user)
            return redirect('/')
        else:
            return render_template('login.html', incorrect=True)
    return render_template('login.html')


# user logout
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect('/')


# to mail employee/user for successful registraition
def send_mail(email, text):
    msg = Message('Successfully Registered', recipients=[email], sender='employeesecurity@facerecog.com', body=text)
    mail_.send(msg)


# user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        id = request.form['id']
        username = request.form['username']
        name = request.form['name']
        mail = request.form['mail']
        pass1 = request.form['pass']
        pass2 = request.form['pass2']

        # check if the owner id and username are unique or not.
        user = users.query.filter_by(username=username).first()
        user2 = users.query.filter_by(id=id).first()
        # if not unique or passwords do not match then back to sign up page with informative message, otherwise register the user
        if user is not None or user2 is not None:
            return render_template('signup.html', incorrect=True, msg='User with same ID or Username already exist')
        elif pass1 != pass2:
            return render_template('signup.html', incorrect=True, msg="Passwords do not match")
        else:
            new_user = users(id=id, name=name, mail=mail, username=username, password=pass1)
            db.session.add(new_user)
            db.session.commit()
            msg = f'''Hello {new_user.name}
Your owner account has been successfully created

Thank You.
Face Recognition Based Employee Attendance Logger
'''
            send_mail(new_user.mail, msg)
            return render_template('login.html', registered=True)

    return render_template('signup.html')


# user password reset request
@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['mail']
        user = users.query.filter_by(mail=email).first()
        # if user with given mail id exists then generate an OTP and mail to the user
        if user:
            otp = randint(000000, 999999)
            sendResetMail(email, otp)
            session['id'] = user.id
            session['otp'] = otp
            return render_template('OTP.html')
        else:
            return render_template('resetRequest.html', incorrect=True)
    return render_template('resetRequest.html')


# function to mail password reset OTP
def sendResetMail(mail, otp):
    msg = Message('Reset Password', recipients=[mail], sender='employeesecurity@facerecog.com')
    msg.body = f''' your otp is {str(otp)}. if you didn't send a password reset request, please ignore this message'''
    mail_.send(msg)


# to verigy OTP
@app.route('/verifyOTP', methods=['GET', 'POST'])
def verifyOTP():
    # if sent OTP matches with user typed OTP then redirect to reset password page
    otp2 = int(request.form['otp'])
    if session['otp'] == otp2:
        return render_template('resetPassword.html')
    else:
        return render_template('OTP.html', incorrect=True)


# user password reset
@app.route('/resetPass', methods=['GET', 'POST'])
def resetPass():
    if request.method == 'POST':
        pw1 = request.form['pass1']
        pw2 = request.form['pass2']

        # التحقق من قوة كلمة المرور (طولها لا يقل عن 8 أحرف وتحتوي على أرقام وحروف)
        def is_strong_password(password):
            if len(password) < 8:
                return False
            has_digit = any(char.isdigit() for char in password)
            has_alpha = any(char.isalpha() for char in password)
            return has_digit and has_alpha

        # تحقق من تطابق كلمتي المرور ومن قوة كلمة المرور
        if pw1 == pw2 and is_strong_password(pw1):
            try:
                user = users.query.filter_by(id=session.get('id')).first()
                if user:
                    # تخزين كلمة المرور بعد تشفيرها
                    user.password = pw1  # يفضل استخدام مكتبة لتشفير كلمات المرور مثل `bcrypt`
                    db.session.commit()
                    return render_template('login.html', reseted=True)
                else:
                    return "User not found.", 404
            except Exception as e:
                print(f"Error resetting password: {e}")
                return "An error occurred while resetting your password.", 500
        else:
            # عرض خطأ إذا كانت كلمة المرور ضعيفة أو لا تتطابق
            incorrect = True if pw1 != pw2 else False
            weak_password = not is_strong_password(pw1)
            return render_template('resetPassword.html', incorrect=incorrect, weak_password=weak_password)
    else:
        return render_template('resetPassword.html')



# add new employee in the employee database
@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    try:
        cap2.release()
    except:
        pass

    invalid = 0  # حالة الخطأ الافتراضية
    if request.method == 'POST':
        id = request.form['id']
        name = request.form['name']
        dept = request.form['dept']
        mail = request.form['mail']

        # تحقق من الأخطاء عند الإضافة
        try:
            invalid = 1  # إذا لم يكن المعرف فريدًا
            emp = employee(id=id, name=name, department=dept, email=mail)
            db.session.add(emp)
            db.session.commit()

            # اسم ملف الصورة بناءً على المعرف
            fileNm = id + '.jpg'

            # حاول حفظ الصورة من الملف أو من الكاميرا
            try:
                photo = request.files.get('photo')  # الحصول على الصورة من النموذج
                if photo and photo.filename:  # إذا تم تحميل صورة
                    photo.save(os.path.join(path, fileNm))
                elif 'pic' in globals():  # إذا تم التقاط صورة بالكاميرا
                    cv2.imwrite(os.path.join(path, fileNm), pic)
                    del globals()['pic']
                else:
                    invalid = 2  # لم يتم تحميل الصورة أو التقاطها
            except Exception as e:
                print(f"Error saving photo: {e}")
                invalid = 2

            # إذا نجحت العملية، أرسل البريد الإلكتروني
            if invalid == 0:
                try:
                    send_email(mail, name)
                except Exception as e:
                    print(f"Error sending email: {e}")

            # إذا كانت العملية ناجحة، قم بإعادة تعيين الحالة إلى 0
            invalid = 0
        except Exception as e:
            print(f"Error adding employee: {e}")
            db.session.rollback()

    # استرجاع جميع السجلات لعرضها في الجدول
    allRows = employee.query.all()
    return render_template("insertPage.html", allRows=allRows, invalid=invalid)

def send_email(to_email, name):
    """إرسال رسالة بريد إلكتروني لإبلاغ الموظف بتسجيله."""
    sender_email = "your_email@example.com"
    sender_password = "your_password"

    # إعداد محتوى الرسالة
    subject = "إكمال التسجيل في النظام"
    body = f"""\
مرحبًا {name},

تم تسجيلك بنجاح في نظام تسجيل الحضور باستخدام التعرف على الوجه.

شكرًا،
إدارة النظام
"""

    # إعداد الرسالة
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # إرسال الرسالة باستخدام SMTP
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()  # بدء الاتصال الآمن
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print(f"Email sent successfully to {to_email}")


# to delete an existing employee
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    # حذف الموظف من قاعدة البيانات
    emp = employee.query.filter_by(id=id).first()
    if emp:
        # حذف السجلات المرتبطة بالموظف من جدول الحضور
        AttendanceRecord.query.filter_by(employee_id=id).delete()
        db.session.delete(emp)
        db.session.commit()

    # حذف الصورة المخزنة في المجلد static/TrainingImages
    fn = id + ".jpg"
    try:
        os.unlink(os.path.join("static/TrainingImages", fn))
    except FileNotFoundError:
        pass

    return redirect("/add")


# to update an existing employee
@app.route("/update", methods=['GET', 'POST'])
@login_required
def update():
    # 1) الحصول على المعرف القديم من الطلب
    id = request.form['id']
    # 2) جلب الموظف من قاعدة البيانات
    emp = employee.query.filter_by(id=id).first()
    if not emp:
        flash("الموظف غير موجود", "danger")
        return redirect("/add")

    # 3) تحديث بيانات الموظف
    emp.name = request.form['name']
    emp.department = request.form['dept']
    emp.email = request.form['mail']
    db.session.commit()

    # 4) تحديث الصورة (الاسم = <id>.jpg)
    fileNm = id + '.jpg'
    try:
        try:
            # إذا رفع المستخدم صورة جديدة بحقل 'photo'
            photo = request.files['photo']
            photo.save(os.path.join(path, fileNm))
        except:
            # إن لم يجدها، خذ الصورة الملتقطة (pic) واحفظها
            cv2.imwrite(os.path.join(path, fileNm), pic)
            del globals()['pic']
    except:
        pass

    # 5) تحديث سجلات الحضور في جدول AttendanceRecord
    records = AttendanceRecord.query.filter_by(employee_id=id, status='On Service').all()
    for rec in records:
        rec.name = emp.name
        rec.department = emp.department
    db.session.commit()

    # 6) إعادة التوجيه إلى صفحة الإضافة
    return redirect("/add")


# Generating frames for capturing photo
# تعديل الدالة لاستقبال emp_id
def gen_frames_takePhoto(emp_id):
    """
    يلتقط صورة لشخص واحد بعد عد تنازلي من 3..2..1..
    ثم يحفظ الصورة في مجلد static/TrainingImages/<emp_id>.jpg
    """
    countdown = 3  # العد التنازلي
    countdown_in_progress = False

    while True:
        ret, frame = cap2.read()  # قراءة الإطار من الكاميرا
        if not ret:
            break

        # قلب الإطار لسهولة العرض
        frame = cv2.flip(frame, 1)

        # تقليل حجم الإطار للمعالجة
        frameS = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        frameS = cv2.cvtColor(frameS, cv2.COLOR_BGR2RGB)

        # اكتشاف الوجه
        facesLoc = face_recognition.face_locations(frameS)

        if len(facesLoc) > 1:
            # إذا تم العثور على أكثر من وجه
            cv2.putText(frame, "رجاءً: شخص واحد فقط", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            countdown_in_progress = False
            countdown = 3
        elif len(facesLoc) == 1:
            # إذا تم العثور على وجه واحد
            y1, x2, y2, x1 = facesLoc[0]
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

            # رسم مستطيل حول الوجه
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            if not countdown_in_progress:
                countdown_in_progress = True
            else:
                if countdown > 0:
                    # نص العد التنازلي بالعربية
                    pil_img = Image.fromarray(frame)
                    draw = ImageDraw.Draw(pil_img)
                    reshaped_countdown = arabic_reshaper.reshape(f"التقاط خلال: {countdown}")
                    bidi_countdown = get_display(reshaped_countdown)
                    font_path = "static/arial.ttf"  # مسار الخط
                    font = ImageFont.truetype(font_path, 32)
                    draw.text((50, 50), bidi_countdown, font=font, fill=(255, 255, 255))
                    frame = np.array(pil_img)

                    time.sleep(1)
                    countdown -= 1
                else:
                    # عند انتهاء العد التنازلي
                    photos_path = "static/TrainingImages"
                    if not os.path.exists(photos_path):
                        os.makedirs(photos_path)

                    filename = f"{emp_id}.jpg"
                    save_path = os.path.join(photos_path, filename)
                    cv2.imwrite(save_path, frame)

                    # نص التأكيد بالعربية
                    pil_img = Image.fromarray(frame)
                    draw = ImageDraw.Draw(pil_img)
                    reshaped_saved = arabic_reshaper.reshape("تم حفظ الصورة بنجاح")
                    bidi_saved = get_display(reshaped_saved)
                    font_path = "static/arial.ttf"
                    font = ImageFont.truetype(font_path, 32)
                    draw.text((50, 50), bidi_saved, font=font, fill=(0, 255, 0))
                    frame = np.array(pil_img)

                    # إرسال آخر إطار
                    ret2, buffer2 = cv2.imencode('.jpg', frame)
                    if ret2:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer2.tobytes() + b'\r\n')

                    cap2.release()
                    break
        else:
            # إذا لم يتم العثور على أي وجه
            pil_img = Image.fromarray(frame)
            draw = ImageDraw.Draw(pil_img)
            reshaped_no_face = arabic_reshaper.reshape("الرجاء وضع وجهك أمام الكاميرا")
            bidi_no_face = get_display(reshaped_no_face)
            font_path = "static/arial.ttf"
            font = ImageFont.truetype(font_path, 32)
            draw.text((50, 50), bidi_no_face, font=font, fill=(255, 255, 255))
            frame = np.array(pil_img)

        # إرسال الإطار الحالي
        ret2, buffer2 = cv2.imencode('.jpg', frame)
        if not ret2:
            break
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer2.tobytes() + b'\r\n')


# Passing generated frames to HTML page
@app.route('/takePhoto/<emp_id>')
def takePhoto(emp_id):
    global cap2
    cap2 = cv2.VideoCapture(0)
    return Response(gen_frames_takePhoto(emp_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')




##########################
# مسار /encode
##########################
@app.route("/encode")
@login_required
def encode():
    # الصور ومصفوفاتنا المعروفة
    images = []
    myList = os.listdir(path)

    # جعلها متغيرات عامة (حذر في المشاريع الكبيرة)
    global encodedList
    global imgNames

    def findClassNames(file_list):
        cNames = []
        for file_name in file_list:
            curImg = cv2.imread(f'{path}/{file_name}')
            # إذا لم يستطع قراءة الصورة، نتجاهل
            if curImg is None:
                continue
            images.append(curImg)
            # إزالة الامتداد
            cNames.append(os.path.splitext(file_name)[0])
        return cNames

    def findEncodings(imgs):
        encodeListLocal = []
        for img in imgs:
            # تحويل لـ RGB قبل face_recognition
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            try:
                encode = face_recognition.face_encodings(img)[0]
                encodeListLocal.append(encode)
            except IndexError:
                # لم يجد أي وجه في الصورة
                pass
        return encodeListLocal

    imgNames = findClassNames(myList)
    encodedList = findEncodings(images)

    # يمكنك طباعة حجم القوائم للتأكد
    print(f"[INFO] Found {len(imgNames)} images.")
    print(f"[INFO] Encoded {len(encodedList)} faces.")

    return render_template("recogPage.html")


##########################
# مسار /video لبدء الكاميرا واستخدام gen_frames
##########################
@app.route('/video', methods=['GET', 'POST'])
def video():
    global cap
    # افتح الكاميرا مرة واحدة
    cap = cv2.VideoCapture(0)

    # اختياري: اضبط دقة الكاميرا على 640×480 (مثال)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


##########################
# دالة gen_frames للتعرّف على الوجوه وبث الإطارات
##########################
def gen_frames():
    oldIds = []

    face_detection_model = "hog"
    distance_threshold = 0.4

    # دالة تسجيل الحضور في قاعدة البيانات
    def markEntry(emp_id):
        today_str = datetime.now().strftime('%d-%m-%Y')
        existing_record = AttendanceRecord.query.filter_by(
            employee_id=emp_id,
            date=today_str
        ).first()
        if not existing_record:
            now = datetime.now()
            date_str = now.strftime("%d-%m-%Y")
            time_str = now.strftime("%H:%M:%S")
            emp = employee.query.filter_by(id=emp_id).first()
            if emp:
                new_rec = AttendanceRecord(
                    employee_id=emp_id,
                    name=emp.name,
                    department=emp.department,
                    time=time_str,
                    date=date_str,
                    status="On Service"
                )
                db.session.add(new_rec)
                db.session.commit()

    try:
        while True:
            success, img = cap.read()
            if not success:
                break

            # قلب الإطار (Mirror)
            img = cv2.flip(img, 1)

            # تصغير الإطار ثم تحويله لـ RGB
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            # ضع التاريخ والوقت على الإطار الأصلي (باستخدام cv2.putText)
            cv2.putText(
                img,
                datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                (10, 15),
                cv2.FONT_HERSHEY_COMPLEX_SMALL,
                1,
                (0, 0, 255),
                1
            )

            # اكتشاف الوجوه
            facesCurFrame = face_recognition.face_locations(imgS, model=face_detection_model)
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodedList, encodeFace, tolerance=distance_threshold)
                faceDis = face_recognition.face_distance(encodedList, encodeFace)
                matchIndex = np.argmin(faceDis) if len(faceDis) > 0 else None

                # إعادة إحداثيات الوجه للحجم الأصلي
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4

                if matchIndex is not None and matches[matchIndex]:
                    # وجه معروف
                    Id = imgNames[matchIndex]
                    emp_data = employee.query.filter_by(id=Id).first()

                    if emp_data:
                        # تحويل إطار img إلى PIL لاستخدام العربية
                        pil_img = Image.fromarray(img)
                        draw = ImageDraw.Draw(pil_img)

                        # 1) إعادة تشكيل النص العربي + التعامل مع اتجاهه
                        reshaped_name = arabic_reshaper.reshape(emp_data.name)
                        bidi_name = get_display(reshaped_name)

                        # 2) استخدام خط يدعم العربية (ضع المسار الصحيح للخط)
                        font_path = "static/arial.ttf"  # مثال
                        font = ImageFont.truetype(font_path, 28)

                        # 3) نرسم الـ ID (غالبًا أرقام) والنص العربي
                        #    رسم الـ ID
                        draw.text((x1, y2+25), str(Id), font=font, fill=(0, 255, 0))
                        #    رسم الاسم بالعربية
                        draw.text((x1, y2+60), bidi_name, font=font, fill=(0, 255, 0))

                        # تحويل الصورة PIL إلى NumPy array مجددًا
                        img = np.array(pil_img)

                        # رسم المستطيل بعد تحويل img
                        cv2.rectangle(img, (x1, y1), (x2, y2-4), (0, 255, 0), 2)

                        # تسجيل الحضور إذا لم يكن موجودًا
                        if Id not in oldIds:
                            markEntry(Id)
                            oldIds.append(Id)
                    else:
                        # المستخدم غير موجود في DB
                        cv2.putText(img, str(Id), (x1, y2+25), cv2.FONT_HERSHEY_TRIPLEX,
                                    0.8, (255, 255, 0), 2)
                        cv2.putText(img, "Not in DB", (x1, y2+50), cv2.FONT_HERSHEY_TRIPLEX,
                                    0.8, (255, 255, 0), 2)
                        cv2.rectangle(img, (x1, y1), (x2, y2-4), (255, 255, 0), 2)
                else:
                    # وجه غير معروف
                    # رسم "غير معروف" بالعربية كمثال
                    pil_img = Image.fromarray(img)
                    draw = ImageDraw.Draw(pil_img)
                    reshaped_unknown = arabic_reshaper.reshape("غير معروف")
                    bidi_unknown = get_display(reshaped_unknown)

                    font_path = "static/arial.ttf"  # نفس الخط
                    font = ImageFont.truetype(font_path, 28)
                    draw.text((x1, y2+25), bidi_unknown, font=font, fill=(255, 0, 0))
                    img = np.array(pil_img)

                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)

            ret, buffer = cv2.imencode('.jpg', img)
            if not ret:
                break

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            )

    finally:
        cap.release()



# عرض سجلات الحضور
@app.route("/AttendanceSheet")
@login_required
def AttendanceSheet():
    try:
        records = AttendanceRecord.query.all()
        rows = [
            {
                'Id': record.employee_id,
                'Name': record.name,
                'Department': record.department,
                'Time': record.time,
                'Date': record.date,
                'Status': record.status
            } for record in records
        ]
    except Exception as e:
        app.logger.error(f"Error fetching attendance records: {e}")
        return "Error fetching attendance records.", 500

    fieldnames = ['Id', 'Name', 'Department', 'Time', 'Date', 'Status']
    return render_template('RecordsPage.html', allrows=rows, fieldnames=fieldnames, len=len)

# تنزيل جميع السجلات
@app.route("/downloadAll")
def downloadAll():
    try:
        records = AttendanceRecord.query.all()
        rows = [
            {
                'Id': record.employee_id,
                'Name': record.name,
                'Department': record.department,
                'Time': record.time,
                'Date': record.date,
                'Status': record.status
            } for record in records
        ]
        # تحويل البيانات إلى CSV أو صيغة مناسبة أخرى إذا لزم الأمر
        return render_template('DownloadPage.html', rows=rows)  # تحديث هذا لتلبية التنزيل المناسب
    except Exception as e:
        app.logger.error(f"Error downloading all records: {e}")
        return "Error downloading all records.", 500

# حذف سجل محدد
@app.route("/deleteRecord", methods=["POST"])
@login_required
def deleteRecord():
    try:
        record_id = request.form.get("record_id")
        record = AttendanceRecord.query.filter_by(employee_id=record_id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
        return redirect('/AttendanceSheet')
    except Exception as e:
        app.logger.error(f"Error deleting record: {e}")
        return "Error deleting the record.", 500

# تنزيل سجلات اليوم فقط
@app.route("/downloadToday")
def downloadToday():
    try:
        today_date = datetime.now().strftime("%d-%m-%Y")
        today_records = AttendanceRecord.query.filter_by(date=today_date).all()
        rows = [
            {
                'Id': record.employee_id,
                'Name': record.name,
                'Department': record.department,
                'Time': record.time,
                'Date': record.date,
                'Status': record.status
            } for record in today_records
        ]
        # تحويل البيانات إلى CSV أو صيغة أخرى إذا لزم الأمر
        return render_template('DownloadPage.html', rows=rows)  # تحديث هذا لتلبية التنزيل المناسب
    except Exception as e:
        app.logger.error(f"Error fetching today's records: {e}")
        return "Error fetching today's records.", 500

# إعادة تعيين حضور اليوم
@app.route("/resetToday")
@login_required
def resetToday():
    try:
        today_date = datetime.now().strftime("%d-%m-%Y")
        AttendanceRecord.query.filter_by(date=today_date).delete()
        db.session.commit()
        return redirect('/AttendanceSheet')
    except Exception as e:
        app.logger.error(f"Error resetting today's records: {e}")
        return "Error resetting today's records.", 500

# إحصائيات سجلات الحضور
@app.route("/stats")
@login_required
def stats():
    try:
        # 1) كل سجلات AttendanceRecord
        all_records = AttendanceRecord.query.all()

        # 2) تاريخ اليوم
        today_date = datetime.now().strftime("%d-%m-%Y")

        # 3) إحضار جميع الأقسام من جدول employee
        employees = employee.query.all()
        if not employees:
            # لو لم يوجد أي موظف في النظام
            return render_template('statsPage.html', JSON1=None, data=[], len=0, td=[0, 0])

        # جمع الأقسام (قد يكون بعض الأقسام مكررًا في employees)
        departments = list(set(emp.department for emp in employees))

        data = []
        # نحسب لكل قسم عدد المسجّلين والحاضرين اليوم
        for dept in departments:
            total_registered = employee.query.filter_by(department=dept).count()
            present_today = AttendanceRecord.query.filter_by(date=today_date, department=dept,
                                                             status='On Service').count()
            absent_today = total_registered - present_today
            data.append({
                'Department': dept,
                'Registered': total_registered,
                'Present': present_today,
                'Absent': absent_today
            })

        # مجموع الكل
        total_registered = sum(d['Registered'] for d in data)
        total_present = sum(d['Present'] for d in data)
        td = [total_registered, total_present]  # لعرض  [الحاضرون , المسجّلون] أو العكس

        # استخدام Plotly أو غيره لرسم البيانات
        if data:
            df = pd.DataFrame(data)
            fig1 = px.bar(
                df,
                x='Department',
                y=['Registered', 'Present', 'Absent'],
                barmode='group',
                labels={'value': 'Number of Employees'},
                title='Department-wise Attendance'
            )
            JSON1 = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            JSON1 = None

        return render_template('statsPage.html', JSON1=JSON1, data=data, len=len, td=td)
    except Exception as e:
        app.logger.error(f"Error generating stats: {e}")
        return render_template('statsPage.html', JSON1=None, data=[], len=0, td=[0, 0])


@app.route('/get')
def get_bot_response():
    userText = request.args.get('msg').lower()
    user = request.args.get('user', 'Anonymous')

    question = UnansweredQuestion.query.filter_by(question=userText).first()

    if question:
        if question.answer:
            return question.answer
        else:
            return "عذرًا، لا يمكنني المساعدة :("
    else:
        new_question = UnansweredQuestion(question=userText, user=user)
        db.session.add(new_question)
        db.session.commit()
        return "عذرًا، لا يمكنني المساعدة :("

@app.route('/helpBot')
def helpBot():
    """
    تحميل الردود من ملف JSON وعرض واجهة الشات بوت.
    """
    global bot_responses
    with open('static/help.json') as f:
        bot_responses = json.load(f)
    return render_template('chatBot.html', keys=[*bot_responses])

@app.route('/getUnanswered', methods=['GET'])
def get_unanswered_questions():
    questions = UnansweredQuestion.query.all()
    return jsonify([{
        "id": q.id,
        "question": q.question,
        "user": q.user,
        "timestamp": q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "answer": q.answer
    } for q in questions])

@app.route('/updateUnanswered', methods=['POST'])
def update_unanswered():
    data = request.json
    question_text = data.get('question')
    answer_text = data.get('answer')

    question = UnansweredQuestion.query.filter_by(question=question_text).first()

    if question:
        question.answer = answer_text
        db.session.commit()
        return jsonify({"message": "تم تحديث الإجابة بنجاح."})
    else:
        return jsonify({"message": "السؤال غير موجود."}), 404

if __name__ == "__main__":
    db.create_all()
    app.run(debug=False, port=8000)