import os
from datetime import datetime, timedelta
import pytz
import re
from flask import Flask, redirect, render_template, request, url_for, session, flash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
import random
import whisper
from wtforms import *
from wtforms.validators import *

from model.user import *

app = Flask(__name__)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

MONGO_URI = "mongodb+srv://admin-asa:vW2okkevyfnjOUrQ@clusterasa.bb8oo.mongodb.net/asa?retryWrites=true&w=majority&appName=ClusterAsa"
SECRET_KEY = os.urandom(32)

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
google_token = "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"

app.config['SECRET_KEY'] = SECRET_KEY
app.config["MONGO_URI"] = MONGO_URI

perfil = None
timezone_brasilia = pytz.timezone("America/Sao_Paulo")
init_db(app)

google_bp = make_google_blueprint(
    client_id="550611890275-894bsqu08hlo6mljvg5paabkngoo600t.apps.googleusercontent.com",
    client_secret="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",
    redirect_to="google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

from flask_dance.contrib.facebook import make_facebook_blueprint, facebook

facebook_bp = make_facebook_blueprint(
    client_id="your_facebook_app_id",
    client_secret="your_facebook_app_secret",
    redirect_to="facebook_login"
)
app.register_blueprint(facebook_bp, url_prefix="/login")

class LoginForm(FlaskForm):
    username = StringField('CPF', name="cpf", validators=[DataRequired()])
    password = PasswordField('Senha',name="password", validators=[DataRequired()])
    usertype = RadioField('Tipo de Usuário', choices=[('paciente', 'Paciente'), ('fisioterapeuta', 'Fisioterapeuta')], validators=[DataRequired()])

class RegisterForm(FlaskForm):
    nome = StringField('Nome', name="name", validators=[DataRequired()])
    cpf = StringField('CPF', name="cpf", validators=[DataRequired()])
    password = PasswordField('Senha',name="password", validators=[DataRequired(), Length(min=6, message='A senha deve ter no mínimo 6 caracteres'), EqualTo('confirm_password', message='As senhas devem ser iguais'), Regexp(r'[a-zA-Z0-9]+', message='A senha deve conter apenas letras e números')])
    confirm_password = PasswordField('Confirme a senha',name="confirm", validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais')])
    role = RadioField('Tipo de Usuário', name="role", choices=[('paciente', 'Paciente'), ('profissional', 'Fisioterapeuta')], validators=[DataRequired()])
    email = StringField('E-mail', name="email", validators=[DataRequired()])
    health_id = StringField('Crefito', name="health_id", validators=[DataRequired()])
    mobile = TelField('Telefone', name="mobile", validators=[DataRequired()])
    birth_date = DateField('Data de nascimento', format='%Y-%m-%d', name="birth_date", validators=[DataRequired()])
    gender = SelectField('Gênero', choices=[('masculino', 'Masculino'), ('feminino', 'Feminino'), ('outro', 'Outro')], validators=[DataRequired()])

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/fisioterapeuta/transcricao', methods=['GET', 'POST'])
@login_required
def transcricao():
    return render_template('transcricao.html')

@app.route("/upload", methods=["POST"])
def upload():
    print(request)
    print(request.files)
    if 'audio' in request.files:
        audio = request.files['audio']
        file_path = os.path.join(UPLOAD_FOLDER, audio.filename)
        print(file_path)
        audio.save(file_path)
        return "Áudio recebido e armazenado com sucesso!", 200
    return "Nenhum áudio recebido", 400

@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.json
    file_name = data.get('filename')
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    if os.path.exists(file_path):
        
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        transcription = result['text']
        return transcription, 200
    else:
        return "Arquivo não encontrado", 404

@app.route('/paciente/consulta', methods=['GET'])
@login_required
def get_consulta():
    consulta = get_appointments_by_cpf_dashboard(current_user.cpf)
    return consulta,200

@app.route('/paciente/consultames', methods=['GET'])
@login_required
def get_consulta_mes():
    consulta = get_current_month_appointments_by_cpf(current_user.cpf)
    return consulta,200

@app.route('/paciente/dispersao', methods=['GET'])
@login_required
def get_dispercao():
    consulta = get_appointments_time_type_by_cpf(current_user.cpf)
    return consulta,200

@app.route("/")
@login_required
def home():
    if current_user.is_authenticated:
        return redirect(url_for('perfil'))
    return render_template("login.html")

@app.route('/fisioterapeuta/historico', methods=['GET'])
@login_required
def historico_fisioterapeuta():
    cpf = request.args.get('cpf', '')
    # print(cpf)
    if cpf:
        consultas = get_all_appointment_by_physioterapist_and_cpf(current_user.cpf, cpf)
    else:
        consultas = get_all_appointment_by_physioterapist(current_user.cpf)
    return render_template('historico_fisioterapeuta.html', consultas=consultas)

@app.template_filter('formata_data')
def formata_data(value):
    if value:
        return value.strftime("%d/%m/%Y")
    return value

@app.route('/paciente/historico', methods=['GET'])
@login_required
def historico_paciente():
    print(current_user.cpf)
    next_appointments = get_next_appointment_by_cpf(current_user.cpf)
    appointments = get_all_appointment_by_cpf(current_user.cpf)
    return render_template('historico_paciente.html', appointments=appointments, next_appointments=next_appointments)

@app.route('/paciente/agenda', methods=['GET', 'POST'])
@login_required
def agenda_consulta_paciente():
    if request.method == 'POST':
        ids = []
        physioterapists = get_all_physioterapist()
        for physioterapist in physioterapists:
            ids.append(physioterapist['_id'])
        physioterapist_id = random.choice(ids)
        physioterapist_cpf = get_physioterapist_by_id(physioterapist_id)['cpf']
        date = request.form.get('date')
        date_obj = datetime.strptime(date, "%Y-%m-%dT%H:%M")
        print(date_obj)
        print(type(date_obj))
        hour = date_obj.strftime("%H:%M")
        # date = datetime.strptime(date, "%Y-%m-%dT%H:%M").isoformat() + ".000+00:00"
        print(type(date))
        data = {
            "cpf": current_user.cpf,
            "health_cpf": physioterapist_cpf,
            "date_appointment": date_obj,
            "hour_appointment": hour,
            "type": request.form.get('type'),
            "status": 'Pendente',
            "created_at": datetime.now(timezone_brasilia).isoformat(),
            "updated_at": datetime.now(timezone_brasilia).isoformat(),
            "email": current_user.email,
            "pacient_name": current_user.nome,
            "post_guidance": "",
            "exercise": []
        }
        print(data)
        create_appointment(data)
        return redirect('/paciente/historico')
    return render_template('agenda_consulta_paciente.html')

@app.route('/fisioterapeuta/adicionar_exercicio/<exercicio_id>/<consulta_id>', methods=['POST'])
@login_required
def adicionar_exercicio(exercicio_id, consulta_id):
    data = {
            "exercise_id": exercicio_id,
            'comment'    : request.form.get('comment').strip()
    }
    print(f"Consulta ID: {consulta_id}, Exercicio ID: {exercicio_id}, Comment: {request.form.get('comment')}")
    message, result = add_exercise(consulta_id, data)
    if result:
        flash(message, 'success')
        return redirect(f'/fisioterapeuta/exercicios/{consulta_id}')
    else:
        flash(message, 'error')
        return redirect('/historico')
@app.route('/fisioterapeuta/exercicios_comentario/<consulta_id>', methods=['GET', 'POST'])
@login_required
def detalhe_exercicio_comentario_fisioterapeuta(consulta_id):
    exercicio_id = request.args.get('exercicio_id')
    exercicios = get_exercises_by_id(exercicio_id)      
        
    return render_template('detalhe_exercicio_comentario_fisioterapeuta.html',exercicios=exercicios, consulta_id=consulta_id)

@app.route('/paciente/exercicios_comentario/<consulta_id>', methods=['GET', 'POST'])
@login_required
def exercicios_paciente(consulta_id):
    exercicios = get_exercises_by_appoiment(consulta_id)
    return render_template('exercicios_paciente.html', exercicios=exercicios)

@app.route('/fisioterapeuta/exercicios/<consulta_id>')
@login_required
def exercicios_fisioterapeuta(consulta_id):
    exercicios = get_exercises()
    
    print(exercicios)
    return render_template('exercicios_fisioteurapeta.html', exercicios=exercicios,consulta_id=consulta_id)

@app.route('/fisioterapeuta/detalhe_consulta/<consulta_id>')
@login_required
def detalhe_consulta_fisio(consulta_id):
    consultas = get_all_appointment_by_id(consulta_id)
    print(consultas[0])
    return render_template('detalhe_consulta_fisio.html', consulta=consultas[0])

@app.route('/fisioterapeuta/detalhe_orientacao/<consulta_id>', methods=['GET', 'POST'])
@login_required
def detalhe_orientacao_fisioterapeuta(consulta_id):
    consulta = get_appointment_by_id(consulta_id)
    print(consulta)
    if request.method == 'POST':
        post_guidance = request.form.get('post_guidance')
        data = {
            "post_guidance": post_guidance.strip()
        }
        update_appointment(consulta_id, data)
        return redirect('/fisioterapeuta/historico')
    return render_template('detalhe_orientacao_fisioterapeuta.html', consulta=consulta,consulta_id=consulta_id)

@app.route('/fisioterapeuta/detalhe_orientacao_comentario/<consulta_id>')
@login_required
def detalhe_orientacao_comentario_fisioterapeuta(consulta_id):
    consulta = get_appointment_by_id(consulta_id)
    return render_template('detalhe_orientacao_comentario_fisioterapeuta.html', consulta=consulta)

def get_week_dates():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    return [(start_of_week + timedelta(days=i)).strftime('%d %b %Y') for i in range(7)]

def get_month_dates():
    today = datetime.today()
    start_of_month = today.replace(day=1)
    next_month = today.replace(day=28) + timedelta(days=4)
    end_of_month = next_month - timedelta(days=next_month.day)
    return [(start_of_month + timedelta(days=i)).strftime('%d %b %Y') for i in range((end_of_month - start_of_month).days + 1)]

@app.route('/calendario')
@login_required
def calendario():
    week_dates = get_week_dates()
    month_dates = get_month_dates()
    today_date = datetime.today().strftime('%d %b %Y')
    return render_template('calendario.html', week_dates=week_dates, month_dates=month_dates,today_date=today_date)
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    if session.get('was_once_logged_in'):
        del session['was_once_logged_in']
    flash('Deslogado com sucesso', 'success')
    return redirect('/login')

@app.route("/google_login")
def google_login():
    print(google.authorized)
    if not google.authorized:
        return redirect(url_for("google.login"))
    print("Passou")
    try:
        #resp = google.get("userinfo/v2/me")
        
        resp = google.get(f"/oauth2/v1/userinfo")
        user_info = resp.json()
        print(resp.json())
        user = get_user_by_email(user_info["email"])
    except Exception as e:
        print(e)
        return redirect(url_for("register"))   
    if not user:
        mongo.db.paciente.insert_one({
            "name": user_info["name"],
            "email": user_info["email"]
        })

    return f"Hello, {user_info['name']}!"

# @app.route("/facebook_login")
# def facebook_login():
#     if not facebook.authorized:
#         return redirect(url_for("facebook.login"))

#     resp = facebook.get("/me?fields=name,email")
#     user_info = resp.json()
#     user = get_user_by_email(user_info["email"])

#     if not user:
#         mongo.db.users.insert_one({
#             "name": user_info["name"],
#             "email": user_info["email"]
#         })

#     return f"Hello, {user_info['name']}!"

@login_manager.user_loader
def load_user(user_id):

    # O user_id será composto pelo ID do usuário e seu papel (paciente ou fisioterapeuta)
    user_id, role = user_id.split("|")  # Dividimos o user_id e o role
    # print(user_id, role)
    if role == 'paciente':
        # Buscar o paciente pelo id_paciente
        paciente_data = get_patient_by_id(user_id)
        # print(paciente_data)
        if paciente_data:
            # Retornar o objeto User para o paciente
            return User(
                id_usuario=paciente_data['_id'],
                cpf=paciente_data['cpf'],
                nome=paciente_data['name'],
                genero=paciente_data['gender'],
                telefone=paciente_data.get('mobile'),
                email=paciente_data['email'],
                data_criacao=paciente_data['created_at'],
                data_atualizacao=paciente_data['updated_at'],
                role='paciente',
                data_nascimento=paciente_data['birth_date']
            )

    elif role == 'fisioterapeuta':
        # Buscar o fisioterapeuta pelo id_fisioterapeuta       
        # print(user_id)
        fisioterapeuta_data = get_physioterapist_by_id(user_id)
        # print(fisioterapeuta_data)
        if fisioterapeuta_data:
            # Retornar o objeto User para o fisioterapeuta
            return User(
                id_usuario=fisioterapeuta_data['_id'],
                cpf=fisioterapeuta_data['cpf'],
                nome=fisioterapeuta_data['name'],
                genero=fisioterapeuta_data['gender'],
                email=fisioterapeuta_data['email'],
                telefone=fisioterapeuta_data.get('mobile'),
                data_criacao=fisioterapeuta_data['created_at'],
                data_atualizacao=fisioterapeuta_data['updated_at'],
                data_nascimento=fisioterapeuta_data['birth_date'],
                role='fisioterapeuta',
                #crefito=fisioterapeuta_data['crefito'],
                #status=fisioterapeuta_data['status']
            )

    # Se não encontrar nada, retorna None
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('perfil'))
    
    form = LoginForm()
    if request.method == "POST":
        cpf = request.form.get("cpf")
        password = request.form.get("password")
        user_type = request.form.get("usertype")

        if user_type is None:
            flash("Por favor, selecione o tipo de usuário.", "error")
            return redirect(url_for('login'))

        valid, user_data = compare_password(cpf, password, user_type)
        if valid:
            role = 'paciente' if user_type == 'paciente' else 'fisioterapeuta'
            crefito = user_data.get('crefito') if role == 'fisioterapeuta' else None
            status = user_data.get('status') if role == 'fisioterapeuta' else None

            user = User(
                id_usuario=f"{user_data['_id']}|{role}",
                cpf=user_data['cpf'],
                nome=user_data['name'],
                genero=user_data['gender'],
                email=user_data['email'],
                telefone=user_data.get('mobile'),
                data_criacao=user_data['created_at'],
                data_atualizacao=user_data['updated_at'],
                role=role,
                data_nascimento=user_data['birth_date'],
                crefito=crefito,  # Adiciona o campo exclusivo do profissional
                status=status  # Adiciona o campo exclusivo do profissional
            )
            login_user(user)
            flash("Login realizado com sucesso", "success")
            return redirect(url_for('perfil'))
        else:
            flash("CPF ou senha inválidos", "error")
            return redirect(url_for('login'))
    
    return render_template("login.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('perfil'))
    
    form = RegisterForm()
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")
        
        birth_date = request.form.get("birth_date")
        gender = request.form.get("gender")
        mobile = request.form.get("mobile")
        cpf = request.form.get("cpf")
        new_cpf = re.sub(r'\D', '', cpf)
        print(name)
        print(new_cpf)
        password = request.form.get("password")
        if role == "paciente":
            exist_pacient = get_user_by_email(email) or get_user_by_cpf(new_cpf)
            if exist_pacient:
                flash("Email ou CPF já cadastrado.", "error")
                return redirect(url_for("register"))
            create_pacient(name, email,birth_date, gender, mobile, new_cpf, password)
            flash("Registro realizado com sucesso!", "success")
            return redirect(url_for("login"))

    return render_template("register.html",form=form)

@app.route("/fisioterapeuta/pacientes")
@login_required
def list_pacientes():
    cpf = request.args.get('cpf')  # Captura o CPF da query string

    # Se o CPF for passado na URL, filtra por ele; caso contrário, exibe todos
    if cpf:
        pacientes = get_all_patients_like_cpf(cpf)
    else:
        pacientes = get_all_patients()
    # print(pacientes)
    return render_template("lista_paciente.html", pacientes=pacientes, cpf_filtro=cpf, perfil=perfil)

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if current_user.role == "fisioterapeuta":
        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            birth_date = request.form.get("birth_date")
            mobile = request.form.get("mobile")
            data = {
                "name": name,
                "email": email,
                "birth_date": birth_date,
                "mobile": mobile,
                "updated_at": datetime.now(timezone_brasilia)
            }
            update_physioterapist(current_user.cpf, data)
            flash("Perfil atualizado com sucesso", "success")
            return redirect(url_for('perfil'))
        perfil = get_physioterapist_by_cpf(current_user.cpf)
        return render_template("perfil.html", perfil=perfil)
    if current_user.role == "paciente":
        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            birth_date = request.form.get("birth_date")
            mobile = request.form.get("mobile")
            data = {
                "name": name,
                "email": email,
                "birth_date": birth_date,
                "mobile": mobile,
                "updated_at": datetime.now(timezone_brasilia)
            }
            update_patient(current_user.cpf, data)
            flash("Perfil atualizado com sucesso", "success")
            return redirect(url_for('perfil'))
        perfil = get_user_by_cpf(current_user.cpf)
        return render_template("perfil.html", perfil=perfil)
    # print(perfil)
   
class User(UserMixin):
    def __init__(self, id_usuario, cpf,email, nome, genero, telefone, data_criacao, data_atualizacao, role, crefito=None, status=None, data_nascimento=None):
        self.id = id_usuario  # Esse campo será id_paciente ou id_fisioterapeuta
        self.cpf = cpf
        self.email = email
        self.nome = nome
        self.genero = genero
        self.telefone = telefone
        self.data_criacao = data_criacao
        self.data_atualizacao = data_atualizacao
        self.role = role  # paciente ou fisioterapeuta
        self.crefito = crefito  # Campo específico para fisioterapeutas
        self.status = status  # Campo específico para fisioterapeutas
        self.data_nascimento = data_nascimento  # Campo específico para pacientes

if __name__ == "__main__":
    app.run(debug=True)