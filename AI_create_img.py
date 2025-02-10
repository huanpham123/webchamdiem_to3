import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Thay đổi key này theo nhu cầu của bạn
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data.db')

def get_db():
    """Trả về đối tượng kết nối đến cơ sở dữ liệu, thiết lập row_factory để sử dụng tên cột."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    """Khởi tạo cơ sở dữ liệu, tạo bảng users nếu chưa có và đảm bảo tài khoản admin tồn tại."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            score REAL,
            attempts INTEGER NOT NULL
        )
    ''')
    # Kiểm tra và tạo tài khoản admin nếu chưa có
    cursor.execute("SELECT * FROM users WHERE username = ?", ('huankn1',))
    admin = cursor.fetchone()
    if not admin:
        # Ở đây, admin có lượt làm được biểu diễn bằng giá trị -1 (vô hạn)
        cursor.execute("INSERT INTO users (username, password, score, attempts) VALUES (?, ?, ?, ?)",
                       ('huankn1', '30082008', None, -1))
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    """Đóng kết nối cơ sở dữ liệu khi kết thúc app context."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Danh sách tiêu chí chấm điểm (không thay đổi)
criteria = [
    {"id": "criteria1", "name": "Tham gia hoạt động", "points": 5},
    {"id": "criteria2", "name": "Đóng góp quỹ", "points": 1},
    {"id": "criteria3", "name": "Tham gia trao đổi trên nhóm (Zalo)", "points": 1},
    {"id": "criteria4", "name": "Tích cực tham gia, tham gia nhiệt tình", "points": 1},
    {"id": "criteria5", "name": "Tham gia hoạt động nhóm (VD: Hội nhóm qua nhà làm)", "points": 0.5},
    {"id": "criteria6", "name": "Edit video", "points": 1},
    {"id": "criteria7", "name": "Soạn kịch bản", "points": 0.5},
]

# ------------------------
# ROUTE: ĐĂNG NHẬP / ĐĂNG KÝ
# ------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            if user['password'] == password:
                session['username'] = username
                flash("Đăng nhập thành công.", "success")
                return redirect(url_for('index'))
            else:
                flash("Mật khẩu không đúng.", "danger")
                return redirect(url_for('login'))
        else:
            # Tài khoản mới được tạo với 1 lượt làm (attempts = 1)
            cursor.execute("INSERT INTO users (username, password, score, attempts) VALUES (?, ?, ?, ?)",
                           (username, password, None, 1))
            db.commit()
            session['username'] = username
            flash("Tài khoản mới đã được tạo và đăng nhập.", "success")
            return redirect(url_for('index'))
    return render_template("Anh_AI.html", page="login")

# ------------------------
# ROUTE: ĐĂNG XUẤT
# ------------------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for('login'))

# ------------------------
# ROUTE: TRANG CHÍNH (Người dùng)
# ------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user is None:
        flash("Không tìm thấy thông tin tài khoản. Vui lòng đăng nhập lại.", "danger")
        return redirect(url_for('logout'))
    # Nếu là tài khoản admin, chuyển hướng sang trang quản trị
    if username == 'huankn1':
        return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        if user['attempts'] <= 0:
            flash("Bạn đã hoàn thành đánh giá và không có lượt làm lại.", "warning")
            return redirect(url_for('index'))
        total_score = 0
        for item in criteria:
            selection = request.form.get(item["id"])
            if selection == "yes":
                total_score += item["points"]
        new_attempts = user['attempts'] - 1
        cursor.execute("UPDATE users SET score = ?, attempts = ? WHERE username = ?", 
                       (total_score, new_attempts, username))
        db.commit()
        flash("Đánh giá của bạn đã được lưu.", "success")
        return redirect(url_for('index'))
    # Làm mới thông tin người dùng sau khi xử lý POST
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user is None:
        flash("Không tìm thấy thông tin tài khoản. Vui lòng đăng nhập lại.", "danger")
        return redirect(url_for('logout'))
    return render_template("Anh_AI.html", page="user", username=username, criteria=criteria,
                           total_score=user['score'], attempts=user['attempts'])

# ------------------------
# ROUTE: TRANG QUẢN TRỊ (Admin Panel)
# ------------------------
@app.route('/admin')
def admin_panel():
    if 'username' not in session or session['username'] != 'huankn1':
        flash("Truy cập không hợp lệ.", "danger")
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username != ?", ('huankn1',))
    users_rows = cursor.fetchall()
    ranking = []
    user_list = []
    for row in users_rows:
        user_dict = {'username': row['username'], 'score': row['score'], 'attempts': row['attempts']}
        user_list.append(user_dict)
        if row['score'] is not None:
            ranking.append({'username': row['username'], 'score': row['score']})
    ranking.sort(key=lambda x: x['score'], reverse=True)
    for i, item in enumerate(ranking):
        item['rank'] = i + 1
    return render_template("Anh_AI.html", page="admin", users=user_list, ranking=ranking)

# ------------------------
# ROUTE: ADMIN RESET – mở lại lượt cho tài khoản
# ------------------------
@app.route('/admin/reset/<username>')
def admin_reset(username):
    if 'username' not in session or session['username'] != 'huankn1':
        flash("Truy cập không hợp lệ.", "danger")
        return redirect(url_for('login'))
    if username != 'huankn1':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET attempts = ?, score = ? WHERE username = ?", (1, None, username))
        db.commit()
        flash(f"Đã mở lại lượt cho tài khoản {username}.", "success")
    else:
        flash("Không thể reset tài khoản admin.", "warning")
    return redirect(url_for('admin_panel'))

# ------------------------
# ROUTE: ADMIN DELETE – xóa điểm của tài khoản
# ------------------------
@app.route('/admin/delete/<username>')
def admin_delete(username):
    if 'username' not in session or session['username'] != 'huankn1':
        flash("Truy cập không hợp lệ.", "danger")
        return redirect(url_for('login'))
    if username != 'huankn1':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET score = ? WHERE username = ?", (None, username))
        db.commit()
        flash(f"Đã xóa điểm của tài khoản {username}.", "success")
    else:
        flash("Không thể xóa điểm của tài khoản admin.", "warning")
    return redirect(url_for('admin_panel'))

# ------------------------
# ROUTE: ADMIN EDIT – chỉnh sửa điểm của tài khoản
# ------------------------
@app.route('/admin/edit/<username>', methods=['GET', 'POST'])
def admin_edit(username):
    if 'username' not in session or session['username'] != 'huankn1':
        flash("Truy cập không hợp lệ.", "danger")
        return redirect(url_for('login'))
    if username == 'huankn1':
        flash("Không thể chỉnh sửa tài khoản admin.", "warning")
        return redirect(url_for('admin_panel'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        try:
            new_score = float(request.form.get("score"))
            cursor.execute("UPDATE users SET score = ? WHERE username = ?", (new_score, username))
            db.commit()
            flash(f"Đã cập nhật điểm cho tài khoản {username}.", "success")
            return redirect(url_for('admin_panel'))
        except ValueError:
            flash("Giá trị điểm không hợp lệ.", "danger")
    cursor.execute("SELECT score FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    current_score = row['score'] if row else None
    return render_template("Anh_AI.html", page="admin_edit", edit_username=username, current_score=current_score)

# Khởi tạo cơ sở dữ liệu khi chạy ứng dụng (chỉ chạy trong môi trường local)
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
