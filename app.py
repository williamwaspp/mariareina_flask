from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
import re

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicie sesión para acceder'

# Inicializar encriptación
cipher = Fernet(app.config['ENCRYPTION_KEY'].encode())

# Modelos
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    grupo = db.Column(db.Enum('admin', 'usuario'), default='usuario')
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    email = db.Column(db.String(120))
    documento = db.Column(db.String(20))
    activo = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.Text)
    codigo_postal = db.Column(db.String(10))
    ciudad = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    telefono1 = db.Column(db.String(20))
    telefono2 = db.Column(db.String(20))
    email = db.Column(db.String(120))
    documento_identidad = db.Column(db.String(20), unique=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

class DatoPago(db.Model):
    __tablename__ = 'datos_pago'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    tipo = db.Column(db.Enum('tarjeta', 'cuenta_bancaria'), nullable=False)
    datos_encriptados = db.Column(db.Text, nullable=False)
    ultimos_4_digitos = db.Column(db.String(4))
    fecha_vencimiento = db.Column(db.Date)
    activo = db.Column(db.Boolean, default=True)
    
    cliente = db.relationship('Cliente', backref=db.backref('datos_pago', lazy=True))

class Suscripcion(db.Model):
    __tablename__ = 'suscripciones'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date)
    monto = db.Column(db.Numeric(10, 2))
    estado = db.Column(db.Enum('activa', 'cancelada', 'pendiente', 'vencida'), default='activa')
    
    cliente = db.relationship('Cliente', backref=db.backref('suscripciones', lazy=True))

# Funciones de encriptación
def encrypt_payment_data(data):
    """Encripta datos de pago y extrae últimos 4 dígitos"""
    encrypted = cipher.encrypt(json.dumps(data).encode()).decode()
    
    # Extraer últimos 4 dígitos para referencia
    ultimos_4 = None
    if 'numero' in data:  # Tarjeta de crédito
        ultimos_4 = data['numero'][-4:] if len(data['numero']) >= 4 else data['numero']
    elif 'iban' in data:  # Cuenta bancaria
        ultimos_4 = data['iban'][-4:] if len(data['iban']) >= 4 else data['iban']
    
    return encrypted, ultimos_4

def decrypt_payment_data(encrypted_data):
    """Desencripta datos de pago"""
    return json.loads(cipher.decrypt(encrypted_data.encode()).decode())

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rutas
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username, activo=True).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirigir según grupo
            if user.grupo == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    es_admin = current_user.grupo == 'admin'
    
    # Estadísticas para el dashboard
    stats = {
        'total_clientes': Cliente.query.filter_by(activo=True).count(),
        'suscripciones_activas': Suscripcion.query.filter_by(estado='activa').count(),
        'cobranzas_mes': db.session.query(db.func.sum(Cobranza.monto)).filter(
            db.extract('month', Cobranza.fecha_pago) == datetime.now().month
        ).scalar() or 0,
        'clientes_nuevos_mes': Cliente.query.filter(
            db.extract('month', Cliente.fecha_registro) == datetime.now().month
        ).count()
    }
    
    return render_template('dashboard.html', es_admin=es_admin, usuario=current_user, stats=stats)

@app.route('/general', methods=['GET', 'POST'])
@login_required
def general():
    if request.method == 'POST':
        try:
            # Validar documento único
            documento = request.form.get('documento_identidad')
            if documento and Cliente.query.filter_by(documento_identidad=documento).first():
                flash('Ya existe un cliente con ese documento de identidad', 'error')
                return redirect(url_for('general'))
            
            cliente = Cliente(
                nombre=request.form['nombre'],
                apellido=request.form['apellido'],
                direccion=request.form.get('direccion'),
                codigo_postal=request.form.get('codigo_postal'),
                ciudad=request.form.get('ciudad'),
                provincia=request.form.get('provincia'),
                telefono1=request.form.get('telefono1'),
                telefono2=request.form.get('telefono2'),
                email=request.form.get('email'),
                documento_identidad=documento
            )
            db.session.add(cliente)
            db.session.commit()
            flash(f'Cliente {cliente.nombre} {cliente.apellido} guardado correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'error')
        
        return redirect(url_for('general'))
    
    # Mostrar lista de clientes
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.apellido).all()
    return render_template('general.html', clientes=clientes)

@app.route('/cobranza', methods=['GET', 'POST'])
@login_required
def cobranza():
    if request.method == 'POST':
        try:
            cliente_id = request.form.get('cliente_id')
            tipo = request.form.get('tipo')
            
            # Validar cliente
            cliente = Cliente.query.get_or_404(cliente_id)
            
            if tipo == 'tarjeta':
                # Validar datos de tarjeta básicamente
                numero = re.sub(r'\s+', '', request.form.get('numero_tarjeta', ''))
                if len(numero) < 13 or len(numero) > 19:
                    flash('Número de tarjeta inválido', 'error')
                    return redirect(url_for('cobranza'))
                
                datos_pago = {
                    'numero': numero,
                    'caducidad': request.form.get('caducidad'),
                    'cvv': request.form.get('cvv'),
                    'titular': f"{cliente.nombre} {cliente.apellido}"
                }
                
                fecha_vencimiento = None
                if request.form.get('caducidad'):
                    try:
                        fecha_vencimiento = datetime.strptime(f"01/{request.form.get('caducidad')}", "%d/%m/%Y").date()
                    except:
                        pass
                
            else:  # cuenta_bancaria
                datos_pago = {
                    'iban': request.form.get('iban', '').replace(' ', '').upper(),
                    'bic': request.form.get('bic', '').upper(),
                    'titular': f"{cliente.nombre} {cliente.apellido}"
                }
                fecha_vencimiento = None
            
            # Encriptar datos
            datos_encriptados, ultimos_4 = encrypt_payment_data(datos_pago)
            
            # Guardar en BD
            pago = DatoPago(
                cliente_id=cliente_id,
                tipo=tipo,
                datos_encriptados=datos_encriptados,
                ultimos_4_digitos=ultimos_4,
                fecha_vencimiento=fecha_vencimiento
            )
            db.session.add(pago)
            db.session.commit()
            
            flash(f'Datos de {tipo} guardados de forma segura para {cliente.nombre} {cliente.apellido}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar datos de pago: {str(e)}', 'error')
        
        return redirect(url_for('cobranza'))
    
    # Obtener clientes para el selector
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.apellido).all()
    # Obtener últimos pagos registrados (solo mostrando últimos 4 dígitos)
    ultimos_pagos = DatoPago.query.filter_by(activo=True).order_by(DatoPago.fecha_registro.desc()).limit(10).all()
    
    return render_template('cobranza.html', clientes=clientes, ultimos_pagos=ultimos_pagos)

@app.route('/suscripciones', methods=['GET', 'POST'])
@login_required
def suscripciones():
    if request.method == 'POST':
        try:
            suscripcion = Suscripcion(
                cliente_id=request.form.get('cliente_id'),
                plan=request.form.get('plan'),
                fecha_inicio=datetime.strptime(request.form.get('fecha_inicio'), '%Y-%m-%d').date(),
                fecha_fin=datetime.strptime(request.form.get('fecha_fin'), '%Y-%m-%d').date() if request.form.get('fecha_fin') else None,
                monto=request.form.get('monto'),
                estado=request.form.get('estado')
            )
            db.session.add(suscripcion)
            db.session.commit()
            flash('Suscripción creada correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear suscripción: {str(e)}', 'error')
        
        return redirect(url_for('suscripciones'))
    
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.apellido).all()
    suscripciones = Suscripcion.query.order_by(Suscripcion.fecha_inicio.desc()).all()
    return render_template('suscripciones.html', clientes=clientes, suscripciones=suscripciones)

@app.route('/api/clientes/buscar')
@login_required
def buscar_clientes():
    """API para búsqueda de clientes (autocompletado)"""
    termino = request.args.get('q', '')
    if len(termino) < 2:
        return jsonify([])
    
    clientes = Cliente.query.filter(
        (Cliente.nombre.like(f'%{termino}%')) |
        (Cliente.apellido.like(f'%{termino}%')) |
        (Cliente.documento_identidad.like(f'%{termino}%')) |
        (Cliente.email.like(f'%{termino}%'))
    ).limit(10).all()
    
    return jsonify([{
        'id': c.id,
        'nombre_completo': f"{c.nombre} {c.apellido}",
        'documento': c.documento_identidad,
        'email': c.email
    } for c in clientes])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# Modelo faltante para cobranzas
class Cobranza(db.Model):
    __tablename__ = 'cobranzas'
    id = db.Column(db.Integer, primary_key=True)
    suscripcion_id = db.Column(db.Integer, db.ForeignKey('suscripciones.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    metodo_pago = db.Column(db.String(50))
    referencia_pago = db.Column(db.String(100))
    estado = db.Column(db.Enum('pagado', 'pendiente', 'fallido'), default='pagado')
    
    suscripcion = db.relationship('Suscripcion', backref=db.backref('cobranzas', lazy=True))

# Crear tablas al iniciar
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Modo desarrollo: recarga automática y debug
    app.run(debug=True, host='0.0.0.0', port=5000)