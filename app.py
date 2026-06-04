from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci_rahasia_bioskop_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bioskop.db'
db = SQLAlchemy(app)

# Konfigurasi Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ==================== DATABASE MODELS ====================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='pengguna') # 'admin' atau 'pengguna'

class Film(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    sinopsis = db.Column(db.Text, nullable=False)
    poster = db.Column(db.String(500), nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    film_id = db.Column(db.Integer, db.ForeignKey('film.id'), nullable=False)
    jumlah_tiket = db.Column(db.Integer, nullable=False)
    total_harga = db.Column(db.Integer, nullable=False)
    metode_bayar = db.Column(db.String(50), nullable=True)
    jam_tayang = db.Column(db.String(20), nullable=True)
    nomor_kursi = db.Column(db.String(50), nullable=True)

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))
    film = db.relationship('Film', backref=db.backref('bookings', lazy=True, cascade="all,delete-orphan"))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== ROUTES (RUTE WEB) ====================

# 1. Halaman Autentikasi (Login & Register)
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        
        if user:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('dashboard_admin'))
            return redirect(url_for('dashboard_pengguna'))
        else:
            flash('Username atau password salah!', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username sudah digunakan!', 'danger')
        else:
            new_user = User(username=username, password=password, role='pengguna')
            db.session.add(new_user)
            db.session.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ==================== ROLE: ADMIN (CRUD FILM) ====================
@app.route('/admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        return "Akses Ditolak! Anda bukan Admin.", 403
    semua_film = Film.query.all()
    semua_order = Booking.query.all()
    return render_template('admin_dashboard.html', films=semua_film, orders=semua_order)

@app.route('/admin/tambah', methods=['POST'])
@login_required
def tambah_film():
    if current_user.role != 'admin':
        return "Akses Ditolak! Anda bukan Admin.", 403
        
    # Ambil data dari form HTML
    judul = request.form.get('judul')
    genre = request.form.get('genre')
    harga = request.form.get('harga')
    sinopsis = request.form.get('sinopsis')
    poster = request.form.get('poster')
    
    # Buat objek film baru dan masukkan ke database
    film_baru = Film(judul=judul, genre=genre, harga=int(harga), sinopsis=sinopsis, poster=poster)
    db.session.add(film_baru)
    db.session.commit()
    
    flash('Film berhasil ditambahkan!', 'success')
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/edit/<int:id>', methods=['POST'])
@login_required
def edit_film(id):
    if current_user.role == 'admin':
        film = Film.query.get_or_404(id)
        film.judul = request.form.get('judul')
        film.genre = request.form.get('genre')
        film.harga = request.form.get('harga')
        film.sinopsis = request.form.get('sinopsis')
        db.session.commit()
        flash('Film berhasil diperbarui!', 'success')
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/hapus/<int:id>')
@login_required
def hapus_film(id):
    if current_user.role == 'admin':
        film = Film.query.get_or_404(id)
        db.session.delete(film)
        db.session.commit()
        flash('Film berhasil dihapus!', 'warning')
    return redirect(url_for('dashboard_admin'))


# ==================== ROLE: PENGGUNA (BOOKING) ====================
@app.route('/dashboard')
@login_required
def dashboard_pengguna():
    if current_user.role != 'pengguna':
        return redirect(url_for('dashboard_admin'))
    
    semua_film = Film.query.all()
    tiket_saya = Booking.query.filter_by(user_id=current_user.id).all()
    
    # Ambil SEMUA kursi yang sudah pernah dibooking di aplikasi
    booking_terisi = Booking.query.all()
    # Kumpulkan nomor kursinya ke dalam sebuah list teks (misal: ['A1', 'A2'])
    kursi_terpesan = [b.nomor_kursi for b in booking_terisi if b.nomor_kursi]
    
    return render_template('pengguna_dashboard.html', 
                           films=semua_film, 
                           my_tickets=tiket_saya, 
                           kursi_terpesan=kursi_terpesan) # <-- Kirim data kursi terpesan ke HTML

@app.route('/booking/<int:film_id>', methods=['POST'])
@login_required
def pesan_tiket(film_id):
    film = Film.query.get_or_404(film_id)
    
    jumlah = int(request.form.get('jumlah_tiket', 1))
    metode = request.form.get('metode_bayar', 'DANA')
    jam = request.form.get('jam_tayang', '13:00 WIB')       
    kursi = request.form.get('nomor_kursi') # Menangkap nomor kursi yang diklik dari kotak HTML
    
    if not kursi:
        flash('Silakan pilih kursi terlebih dahulu!', 'danger')
        return redirect(url_for('dashboard_pengguna'))
        
    total = film.harga * jumlah
    
    booking_baru = Booking(
        user_id=current_user.id,
        film_id=film.id,
        jumlah_tiket=jumlah,
        total_harga=total,
        metode_bayar=metode,
        jam_tayang=jam,       
        nomor_kursi=kursi     
    )
    
    db.session.add(booking_baru)
    db.session.commit()
    
    return redirect(url_for('struk_pembayaran', booking_id=booking_baru.id))

@app.route('/struk/<int:booking_id>')
@login_required
def struk_pembayaran(booking_id):
    # Ambil data booking yang barusan dibuat beserta detailnya
    booking = Booking.query.get_or_404(booking_id)
    return render_template('struk.html', booking=booking)

# ==================== JALANKAN APLIKASI ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Membuat file database otomatis jika belum ada
        
        # Buat Akun Admin Default jika database masih kosong
        if not User.query.filter_by(username='admin').first():
            admin_default = User(username='admin', password='admin123', role='admin')
            db.session.add(admin_default)
            db.session.commit()
            
    app.run(debug=True)