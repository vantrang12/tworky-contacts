from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from supabase import create_client, Client
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-thiss')

# Khởi tạo Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Decorator kiểm tra đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Truy vấn user từ database
            response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['fullname'] = user['fullname']
                return redirect(url_for('contacts'))
            else:
                return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không đúng')
        except Exception as e:
            return render_template('login.html', error=f'Lỗi kết nối: {str(e)}')
    
    return render_template('login.html')

# Trang đăng xuất
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Trang danh bạ
@app.route('/contacts')
@login_required
def contacts():
    try:
        # Lấy danh sách tất cả organizations
        orgs_response = supabase.table('organizations').select('*').order('name').execute()
        organizations = orgs_response.data if orgs_response.data else []
        
        return render_template('contacts.html', 
                             username=session.get('fullname'),
                             organizations=organizations)
    except Exception as e:
        return render_template('contacts.html', 
                             username=session.get('fullname'),
                             organizations=[],
                             error=f'Lỗi kết nối: {str(e)}')

# API lấy danh sách contacts
@app.route('/api/contacts')
@login_required
def api_contacts():
    try:
        search = request.args.get('search', '')
        org_id = request.args.get('organization', '')
        
        # Truy vấn users với join organizations
        query = supabase.table('users').select('id, username, fullname, description, organization_id, organizations(name)')
        
        # Lọc theo organization nếu có
        if org_id and org_id != 'all':
            query = query.eq('organization_id', org_id)
        
        response = query.execute()
        users = response.data if response.data else []
        
        # Lọc theo search text (tìm kiếm trong username, fullname, description)
        if search:
            search_lower = search.lower()
            users = [
                user for user in users
                if (search_lower in (user.get('username') or '').lower() or
                    search_lower in (user.get('fullname') or '').lower() or
                    search_lower in (user.get('description') or '').lower())
            ]
        
        # Format lại dữ liệu
        formatted_users = []
        for user in users:
            org_name = ''
            if user.get('organizations'):
                org_name = user['organizations'].get('name', '')
            
            formatted_users.append({
                'username': user.get('username', ''),
                'fullname': user.get('fullname', ''),
                'organization': org_name,
                'description': user.get('description', '')
            })
        
        return jsonify({'success': True, 'contacts': formatted_users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)