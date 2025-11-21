from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'luxstyle.db')}",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ============================================================
# MODELOS
# ============================================================

class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    appointments = db.relationship("Appointment", back_populates="service")


class Barber(db.Model):
    __tablename__ = "barbers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)

    appointments = db.relationship("Appointment", back_populates="barber")

class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))

    appointments = db.relationship("Appointment", back_populates="client")


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="pendiente")
    notes = db.Column(db.String(255))

    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    barber_id = db.Column(db.Integer, db.ForeignKey("barbers.id"), nullable=False)

    client = db.relationship("Client", back_populates="appointments")
    service = db.relationship("Service", back_populates="appointments")
    barber = db.relationship("Barber", back_populates="appointments")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="cliente")


# ============================================================
# RUTAS PÚBLICAS
# ============================================================

@app.route("/")
def index():
    services = Service.query.filter_by(is_active=True).all()
    return render_template("index.html", services=services)


@app.route("/services")
def list_services():
    services = Service.query.all()
    return render_template("services.html", services=services)


@app.route("/book", methods=["GET", "POST"])
def book_appointment():

    # Solo usuarios logueados pueden reservar
    if not session.get("user_id"):
        flash("Debes iniciar sesión para reservar una cita.", "warning")
        return redirect(url_for("login"))

    services = Service.query.filter_by(is_active=True).all()
    barbers = Barber.query.filter_by(is_active=True).all()

    if request.method == "POST":

        # ============================
        # CAPTURA Y LIMPIEZA DE DATOS
        # ============================
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        service_id = request.form.get("service_id")
        barber_id = request.form.get("barber_id")
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        notes = (request.form.get("notes") or "").strip()

        # ============================
        # VALIDACIONES
        # ============================
        if not full_name or not phone or not service_id or not barber_id or not date_str or not time_str:
            flash("Por favor completa todos los campos obligatorios.", "warning")
            return redirect(url_for("book_appointment"))

        service = Service.query.get(service_id)
        barber = Barber.query.get(barber_id)

        if not service or not barber:
            flash("Servicio o profesional no válido.", "danger")
            return redirect(url_for("book_appointment"))

        # Fecha y hora válidas
        try:
            appointment_datetime = datetime.strptime(
                f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            flash("Fecha u hora inválida.", "danger")
            return redirect(url_for("book_appointment"))

        # No aceptar citas en el pasado
        if appointment_datetime < datetime.now():
            flash("No puedes reservar una cita en el pasado.", "warning")
            return redirect(url_for("book_appointment"))

        # Evitar choques con el barbero
        existing = Appointment.query.filter_by(
            barber_id=barber_id,
            appointment_datetime=appointment_datetime
        ).first()

        if existing:
            flash("Ese horario ya está ocupado con ese profesional. Elige otra hora.", "warning")
            return redirect(url_for("book_appointment"))

        # ============================
        # CONECTAR CITA AL USUARIO REAL
        # ============================
        logged_user_id = session.get("user_id")

        # Buscar perfil de cliente ligado al usuario
        client = Client.query.filter_by(user_id=logged_user_id).first()

        # Si no existe, se crea
        if not client:
            client = Client(
                full_name=full_name,
                phone=phone,
                email=email,
                user_id=logged_user_id
            )
            db.session.add(client)
            db.session.flush()  # Obtiene client.id antes del commit

        # ============================
        # CREAR LA CITA
        # ============================
        new_appointment = Appointment(
            appointment_datetime=appointment_datetime,
            client=client,
            service_id=service_id,
            barber_id=barber_id,
            notes=notes,
            status="pendiente"
        )

        db.session.add(new_appointment)
        db.session.commit()

        flash("Tu cita ha sido registrada con éxito.", "success")
        return redirect(url_for("index"))

    return render_template("book_appointment.html", services=services, barbers=barbers)


# ============================================================
# ADMINISTRACIÓN: CITAS
# ============================================================

@app.route("/admin/appointments")
def admin_appointments():
    if session.get("role") != "admin":
        flash("No tienes permiso para acceder aquí.", "danger")
        return redirect(url_for("index"))

    appointments = Appointment.query.order_by(
        Appointment.appointment_datetime.desc()
    ).all()
    return render_template("admin_appointments.html", appointments=appointments)


@app.route("/admin/appointment/<int:appointment_id>/<string:new_status>")
def update_appointment_status(appointment_id, new_status):

    if session.get("role") != "admin":
        flash("No tienes permiso para acceder aquí.", "danger")
        return redirect(url_for("index"))

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = new_status
    db.session.commit()

    flash("Estado de la cita actualizado.", "success")
    return redirect(url_for("admin_appointments"))


# ============================================================
# ADMINISTRACIÓN: CRUD SERVICIOS (NUEVO COMPLETO)
# ============================================================

@app.route("/admin/services")
def admin_services():
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    services = Service.query.order_by(Service.id.desc()).all()
    return render_template("admin_services.html", services=services)


@app.route("/admin/services/create", methods=["GET", "POST"])
def admin_service_create():
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        duration = request.form.get("duration")
        price = request.form.get("price")

        if not name or not duration or not price:
            flash("Completa los campos obligatorios.", "warning")
            return redirect(url_for("admin_service_create"))

        new_service = Service(
            name=name,
            description=description,
            duration_minutes=int(duration),
            price=float(price),
            is_active=True,
        )

        db.session.add(new_service)
        db.session.commit()
        flash("Servicio creado correctamente", "success")
        return redirect(url_for("admin_services"))

    return render_template("admin_service_create.html")


@app.route("/admin/services/edit/<int:service_id>", methods=["GET", "POST"])
def admin_service_edit(service_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    service = Service.query.get_or_404(service_id)

    if request.method == "POST":
        service.name = request.form.get("name")
        service.description = request.form.get("description")
        service.duration_minutes = int(request.form.get("duration"))
        service.price = float(request.form.get("price"))

        db.session.commit()
        flash("Servicio actualizado", "success")
        return redirect(url_for("admin_services"))

    return render_template("admin_service_edit.html", service=service)


@app.route("/admin/services/toggle/<int:service_id>")
def admin_service_toggle(service_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    service = Service.query.get_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()

    flash("Estado actualizado", "info")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/delete/<int:service_id>")
def admin_service_delete(service_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    service = Service.query.get_or_404(service_id)

    has_appointments = Appointment.query.filter_by(service_id=service.id).first()
    if has_appointments:
        flash(
            "No puedes eliminar un servicio con citas registradas. Desactívalo.",
            "warning",
        )
        return redirect(url_for("admin_services"))

    db.session.delete(service)
    db.session.commit()

    flash("Servicio eliminado", "success")
    return redirect(url_for("admin_services"))


# ============================================================
# ADMINISTRACIÓN: CRUD BARBEROS
# ============================================================

@app.route("/admin/barbers")
def admin_barbers():
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    barbers = Barber.query.order_by(Barber.id.desc()).all()
    return render_template("admin_barbers.html", barbers=barbers)


@app.route("/admin/barbers/add", methods=["GET", "POST"])
def add_barber():
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name")
        specialty = request.form.get("specialty")

        if not name:
            flash("El nombre es obligatorio", "warning")
            return redirect(url_for("add_barber"))

        new_barber = Barber(name=name, specialty=specialty)
        db.session.add(new_barber)
        db.session.commit()

        flash("Barbero agregado", "success")
        return redirect(url_for("admin_barbers"))

    return render_template("add_barber.html")


@app.route("/admin/barbers/edit/<int:barber_id>", methods=["GET", "POST"])
def edit_barber(barber_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    barber = Barber.query.get_or_404(barber_id)

    if request.method == "POST":
        barber.name = request.form.get("name")
        barber.specialty = request.form.get("specialty")

        db.session.commit()
        flash("Barbero actualizado", "success")
        return redirect(url_for("admin_barbers"))

    return render_template("edit_barber.html", barber=barber)


@app.route("/admin/barbers/toggle/<int:barber_id>")
def toggle_barber(barber_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    barber = Barber.query.get_or_404(barber_id)
    barber.is_active = not barber.is_active

    db.session.commit()
    flash("Estado actualizado", "info")
    return redirect(url_for("admin_barbers"))


@app.route("/admin/barbers/delete/<int:barber_id>")
def delete_barber(barber_id):
    if session.get("role") != "admin":
        flash("No tienes permiso", "danger")
        return redirect(url_for("index"))

    barber = Barber.query.get_or_404(barber_id)

    has_appointments = Appointment.query.filter_by(barber_id=barber.id).first()
    if has_appointments:
        flash("No puedes eliminar un barbero con citas registradas.", "warning")
        return redirect(url_for("admin_barbers"))

    db.session.delete(barber)
    db.session.commit()

    flash("Barbero eliminado", "success")
    return redirect(url_for("admin_barbers"))

# ============================================================
# HISTORIAL DE CITAS DEL USUARIO
# ============================================================

@app.route("/mis-citas")
def user_appointments():

    # Debe estar logueado
    if not session.get("user_id"):
        flash("Debes iniciar sesión para ver tus citas.", "warning")
        return redirect(url_for("login"))

    logged_user_id = session["user_id"]

    # Buscar el perfil de cliente asociado al usuario
    client = Client.query.filter_by(user_id=logged_user_id).first()

    if not client:
        appointments = []  # No tiene citas aún
    else:
        appointments = Appointment.query.filter_by(client_id=client.id) \
            .order_by(Appointment.appointment_datetime.desc()) \
            .all()

    return render_template("user_appointments.html", appointments=appointments)

@app.route("/mis-citas/cancel/<int:appointment_id>")
def cancel_user_appointment(appointment_id):

    # Debe estar logueado
    if not session.get("user_id"):
        flash("Debes iniciar sesión.", "warning")
        return redirect(url_for("login"))

    logged_user_id = session["user_id"]

    # Buscar al cliente asociado
    client = Client.query.filter_by(user_id=logged_user_id).first()
    if not client:
        flash("No tienes permiso para cancelar esta cita.", "danger")
        return redirect(url_for("user_appointments"))

    appointment = Appointment.query.get_or_404(appointment_id)

    # Verifica que la cita pertenezca al usuario
    if appointment.client_id != client.id:
        flash("No puedes cancelar una cita que no es tuya.", "danger")
        return redirect(url_for("user_appointments"))

    # No se puede cancelar citas pasadas
    if appointment.appointment_datetime < datetime.now():
        flash("No puedes cancelar una cita que ya pasó.", "warning")
        return redirect(url_for("user_appointments"))

    # Cancelamos la cita
    appointment.status = "cancelada"
    db.session.commit()

    flash("Cita cancelada correctamente.", "success")
    return redirect(url_for("user_appointments"))

# ============================================================
# LOGIN / REGISTRO / LOGOUT
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("El usuario debe tener al menos 3 caracteres.", "warning")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "warning")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Ese usuario ya existe.", "danger")
            return redirect(url_for("register"))

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role="cliente",
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registro exitoso.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            flash("Completa todos los campos.", "warning")
            return redirect(url_for("login"))

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("Credenciales incorrectas.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        session["role"] = user.role

        flash(f"Bienvenido {user.username}", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))


# ============================================================
# INICIALIZACIÓN
# ============================================================

def seed_initial_data():
    if Service.query.count() == 0:
        db.session.add_all([
            Service(name="Corte clásico", description="Corte tradicional", duration_minutes=30, price=10.0),
            Service(name="Afeitado premium", description="Afeitado con toalla caliente", duration_minutes=40, price=15.0),
            Service(name="Masaje relajante", description="Masaje de cuello y hombros", duration_minutes=20, price=12.0),
        ])

    if Barber.query.count() == 0:
        db.session.add_all([
            Barber(name="Carlos", specialty="Cortes modernos"),
            Barber(name="Luis", specialty="Barbas y afeitados"),
            Barber(name="Ana", specialty="Spa y masajes"),
        ])

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_initial_data()

        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin = User(
                username="admin",
                password=generate_password_hash("1234"),
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
