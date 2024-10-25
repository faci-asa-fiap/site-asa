from bson import ObjectId
from flask_pymongo import PyMongo
from datetime import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
mongo = PyMongo()

def init_db(app):
    mongo.init_app(app)
      
    with app.app_context():
        print("Conexão com MongoDB estabelecida:", mongo.db)

def create_pacient(name, email, birth_date, gender, mobile,cpf, password, google_id=None ):
    user = {
        "name": name,
        "email": email,
        "birth_date": birth_date,
        "gender": gender,
        "mobile": mobile,
        "cpf": cpf,
        "password": generate_password_hash(password, method="pbkdf2:sha256") if password else None,
        "google_id": google_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "sat":0,
        "temp":0
    }
    return mongo.db.paciente.insert_one(user)

def create_user_facebook(name, email, facebook_id):
    user = {
        "name": name,
        "email": email,
        "facebook_id": facebook_id
    }
    return mongo.db.paciente.insert_one(user)

def create_user_google(name, email, google_id):
    user = {
        "name": name,
        "email": email,
        "google_id": google_id
    }
    return mongo.db.paciente.insert_one(user)

def compare_password(cpf, password, user_type):
    if user_type == "paciente":
        user = get_user_by_cpf(cpf)
    else:
        user = get_physioterapist_by_cpf(cpf)
    if not user:
        return False, None
    else:
        return check_password_hash(user["password"], password), user

def get_user_by_email(email):
    return mongo.db.paciente.find_one({"email": email})

def update_patient(cpf, data):
    return mongo.db.paciente.update_one({"cpf": cpf}, {"$set": data})

def update_physioterapist(cpf, data):
    return mongo.db.medico.update_one({"cpf": cpf}, {"$set": data})
def get_user_by_cpf(cpf):
    return mongo.db.paciente.find_one({"cpf": cpf})

def get_physioterapist_by_cpf(cpf):
    return mongo.db.medico.find_one({"cpf": cpf})

def get_patient_by_id(user_id):
    return mongo.db.paciente.find_one({"_id": ObjectId(user_id)})

def get_physioterapist_by_id(user_id):
    return mongo.db.medico.find_one({"_id": ObjectId(user_id)})

def get_all_patients():
    return mongo.db.paciente.find()

def get_all_patients_like_cpf(query):
    return mongo.db.paciente.find({"cpf": {"$regex": query}})

def get_appointment_by_cpf(cpf):
    return mongo.db.consulta.find_one({"cpf": cpf})

def get_next_appointment_by_cpf(cpf):
    timezone_brasilia = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(timezone_brasilia)
    pipeline = [
        {
            "$match": {
                "cpf": cpf,
                "date_appointment": {"$gte": now}
            }
        },
        {
            "$sort": {
                "date_appointment": -1
            }
        },
        {
            "$lookup": {
                "from": "medico", 
                "localField": "health_cpf",
                "foreignField": "cpf",
                "as": "health_info"
            }
        },
        {
            "$unwind": "$health_info"
        }
    ]
    next_appointment = list(mongo.db.consulta.aggregate(pipeline))
    if len(next_appointment) == 0:
        return None
    return next_appointment

def get_all_appointment_by_cpf(cpf):

    timezone_brasilia = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(timezone_brasilia)
    pipeline = [
        {
            "$match": {
                "cpf": cpf,
                "date_appointment": {"$lte": now}
            }
        },
        {
            "$sort": {
                "date_appointment": -1
            }
        },
        {
            "$lookup": {
                "from": "medico",
                "localField": "health_cpf",
                "foreignField": "cpf",
                "as": "health_info"
            }
        },
        {
            "$unwind": "$health_info"
        }
    ]

    appointment = list(mongo.db.consulta.aggregate(pipeline))
    return appointment

def get_all_appointment_by_physioterapist_and_cpf(health_cpf, cpf):
    consultas = mongo.db.consulta.find(
    {
        "health_cpf": health_cpf,
        "cpf": {"$regex": cpf}
    }
).sort("date_appointment", -1)
    
    return consultas
def get_current_month_appointments_by_cpf(cpf):
    today = datetime.now()
    start_of_month = datetime(today.year, today.month, 1)
    next_month = today.month + 1 if today.month < 12 else 1
    start_of_next_month = datetime(today.year if today.month < 12 else today.year + 1, next_month, 1)
    consultas = list(mongo.db.consulta.find({
        "cpf": cpf,
        "date_appointment": {
            "$gte": start_of_month,
            "$lt": start_of_next_month
        }
    }))
    tipos_consultas = {}

    for consulta in consultas:
        tipo = consulta.get('type', 'Outro')
        if tipo in tipos_consultas:
            tipos_consultas[tipo] += 1
        else:
            tipos_consultas[tipo] = 1

    data = [['Tipo de Consulta', 'Quantidade']]
    for tipo, quantidade in tipos_consultas.items():
        data.append([tipo, quantidade])
    return data
def get_appointments_time_type_by_cpf(cpf):
    today = datetime.now()
    start_of_month = datetime(today.year, today.month, 1)
    next_month = today.month + 1 if today.month < 12 else 1
    start_of_next_month = datetime(today.year if today.month < 12 else today.year + 1, next_month, 1)

    consultas = list(mongo.db.consulta.find({
        "cpf": cpf,
        "date_appointment": {
            "$gte": start_of_month,
            "$lt": start_of_next_month
        }
    }))

    data = [['Hora', 'Tipo de Consulta']]
    for consulta in consultas:
        hora = consulta.get('hour_appointment', '00:00')
        tipo = consulta.get('type', 'Outro') 
        data.append([hora, tipo])

    return data

def get_appointments_by_cpf_dashboard(cpf):
    # Busca todas as consultas pelo CPF do paciente
    consultas = list(mongo.db.consulta.find({"cpf": cpf}))

    # Contador para os tipos de consultas
    tipos_consultas = {}
    for consulta in consultas:
        tipo = consulta.get('type', 'Outro')
        if tipo in tipos_consultas:
            tipos_consultas[tipo] += 1
        else:
            tipos_consultas[tipo] = 1

    # Preparar dados para Google Charts
    data = [['Tipo de Consulta', 'Quantidade']]
    for tipo, quantidade in tipos_consultas.items():
        data.append([tipo, quantidade])
    return data


def get_all_appointment_by_physioterapist(cpf):
    result = mongo.db.consulta.find(
    {
        "health_cpf": cpf
    }
).sort("date_appointment", -1)
    print(result)
    return result


def get_all_physioterapist():
    return mongo.db.medico.find()

def create_appointment(appointment):
    return mongo.db.consulta.insert_one(appointment)

def get_all_appointment_by_id(appointment_id):
    pipeline = [
        {
            "$match": {
                "_id": ObjectId(appointment_id)
            }
        },
        {
            "$lookup": {
                "from": "paciente",
                "localField": "cpf",
                "foreignField": "cpf",
                "as": "paciente_info"
            }
        },
        {
            "$unwind": "$paciente_info"
        }
    ]

    appointment = list(mongo.db.consulta.aggregate(pipeline))
    return appointment
def update_appointment(appointment_id, data):
    return mongo.db.consulta.update_one({"_id": ObjectId(appointment_id)}, {"$set": data})

def get_appointment_by_id(appointment_id):
    return mongo.db.consulta.find_one({"_id": ObjectId(appointment_id)})

def get_appointment():
    return mongo.db.consulta.find()

def add_exercise(appointment_id, exercise):
    result = mongo.db.consulta.update_one({"_id": ObjectId(appointment_id)}, {"$push": {"exercise": exercise}})

    if result.modified_count == 1:
        return "Exercício adicionado com sucesso", True
    elif result.matched_count == 1 and result.modified_count == 0:
        return "Exercício já adicionado", False

def get_exercises_by_appoiment(appointment_id):
    pipeline = [
    {
        "$match": {
            "_id": ObjectId(appointment_id)
        }
    },
    {
        "$unwind": "$exercise"
    },
    {
        "$addFields": {
            "exercise.exercise_id": { "$toObjectId": "$exercise.exercise_id" }
        }
    },
    {
        "$lookup": {
            "from": "exercicios", 
            "localField": "exercise.exercise_id",  
            "foreignField": "_id", 
            "as": "exercise_details"
        }
    },
    {
        "$unwind": "$exercise_details" 
    },
    {
        "$group": {
            "_id": "$_id",
            "exercises": {
                "$push": {  
                    "exercise_id": "$exercise.exercise_id",
                    "comment": "$exercise.comment", 
                    "exercise_details": { 
                        "video": "$exercise_details.video",
                        "name": "$exercise_details.name"
                    }
                }
            }
        }
    }
]
    exercicios = list(mongo.db.consulta.aggregate(pipeline))
    return exercicios

def get_exercises():
    return mongo.db.exercicios.find()

def get_exercises_by_id(exercise_id):
    return mongo.db.exercicios.find_one({"_id": ObjectId(exercise_id)})

# Create new patient
def create_patient(name, email, cpf, password):
    patient = {
        "name": name,
        "email": email,
        "cpf": cpf,
        "password": generate_password_hash(password, method="pbkdf2:sha256")
    }
    return mongo.db.paciente.insert_one(patient)