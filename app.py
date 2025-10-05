from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-thiss')

# Kết nối Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Decorator kiểm tra đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Trang chủ - chuyển hướng đến login hoặc contacts
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('contacts'))
    return redirect(url_for('login'))

# Trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Vui lòng nhập đầy đủ thông tin', 'danger')
            return render_template('login.html')
        
        try:
            # Tìm user trong database
            response = supabase.table('users').select('*').eq('username', username).execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                # Kiểm tra mật khẩu (lưu ý: trong thực tế nên hash password)
                if user['password'] == password:
                    # Lưu thông tin vào session
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['fullname'] = user['fullname']
                    flash(f'Chào mừng {user["fullname"]}!', 'success')
                    return redirect(url_for('contacts'))
                else:
                    flash('Sai mật khẩu', 'danger')
            else:
                flash('Tên đăng nhập không tồn tại', 'danger')
        except Exception as e:
            flash(f'Lỗi kết nối: {str(e)}', 'danger')
    
    return render_template('login.html')

# Trang đăng xuất
@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất thành công', 'info')
    return redirect(url_for('login'))

# Trang danh bạ
@app.route('/contacts')
@login_required
def contacts():
    try:
        # Lấy tham số tìm kiếm và lọc
        search = request.args.get('search', '').strip()
        org_filter = request.args.get('org_filter', '').strip()
        
        # Query cơ bản
        query = supabase.table('users').select('id, username, fullname, description, organization_id')
        
        # Thêm điều kiện lọc theo organization nếu có
        if org_filter:
            query = query.eq('organization_id', org_filter)
        
        # Lấy dữ liệu
        response = query.execute()
        users = response.data if response.data else []
        
        # Tìm kiếm trên client-side (vì Supabase free có giới hạn query phức tạp)
        if search:
            search_lower = search.lower()
            users = [u for u in users if 
                     search_lower in (u.get('username') or '').lower() or
                     search_lower in (u.get('fullname') or '').lower() or
                     search_lower in (u.get('description') or '').lower()]
        
        # Lấy danh sách các organization_id duy nhất để làm bộ lọc
        all_orgs = supabase.table('users').select('organization_id').execute()
        organizations = sorted(list(set([org['organization_id'] for org in all_orgs.data if org.get('organization_id')])))
        
        return render_template('contacts.html', 
                             users=users, 
                             organizations=organizations,
                             current_search=search,
                             current_org=org_filter)
    except Exception as e:
        flash(f'Lỗi khi tải danh bạ: {str(e)}', 'danger')
        return render_template('contacts.html', users=[], organizations=[])

# API endpoint để lấy danh sách user (cho AJAX nếu cần)
@app.route('/api/users')
@login_required
def api_users():
    try:
        search = request.args.get('search', '').strip()
        org_filter = request.args.get('org_filter', '').strip()
        
        query = supabase.table('users').select('id, username, fullname, description, organization_id')
        
        if org_filter:
            query = query.eq('organization_id', org_filter)
        
        response = query.execute()
        users = response.data if response.data else []
        
        if search:
            search_lower = search.lower()
            users = [u for u in users if 
                     search_lower in (u.get('username') or '').lower() or
                     search_lower in (u.get('fullname') or '').lower() or
                     search_lower in (u.get('description') or '').lower()]
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)