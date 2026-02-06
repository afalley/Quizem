import os
import json
import uuid
from datetime import datetime, UTC
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session, g
from dotenv import load_dotenv

# Local helpers
from grader import grade_quiz
from mailer import send_email

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
QUIZZES_DIR = DATA_DIR / 'quizzes'
RESPONSES_DIR = DATA_DIR / 'responses'

for d in (DATA_DIR, QUIZZES_DIR, RESPONSES_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

DEFAULT_TEACHER_EMAIL = os.environ.get('TEACHER_EMAIL', '')

# Users storage (very simple JSON file with hashed passwords)
USERS_FILE = DATA_DIR / 'users.json'

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except Exception:
    # Fallback: very weak hashing if Werkzeug isn't available (but Flask bundles it)
    import hashlib

    def generate_password_hash(pw: str):
        return hashlib.sha256(pw.encode('utf-8')).hexdigest()

    def check_password_hash(h: str, pw: str):
        return h == hashlib.sha256(pw.encode('utf-8')).hexdigest()


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open('r', encoding='utf-8') as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_users(users: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix('.json.tmp')
    with tmp.open('w', encoding='utf-8') as fh:
        json.dump(users, fh, indent=2, ensure_ascii=False)
    tmp.replace(USERS_FILE)


def ensure_default_users():
    users = _load_users()
    changed = False
    # Create default teacher and student if missing
    if 'teacher' not in users:
        users['teacher'] = {
            'role': 'teacher',
            'password_hash': generate_password_hash('teacher'),
        }
        changed = True
    if 'student' not in users:
        users['student'] = {
            'role': 'student',
            'password_hash': generate_password_hash('student'),
        }
        changed = True
    if changed:
        _save_users(users)


ensure_default_users()


def get_user(username: str):
    return _load_users().get(username)


def set_user(username: str, role: str, password: str | None = None):
    users = _load_users()
    if role not in ('teacher', 'student'):
        raise ValueError('Invalid role')
    rec = users.get(username, {'role': role})
    rec['role'] = role
    if password is not None:
        rec['password_hash'] = generate_password_hash(password)
    users[username] = rec
    _save_users(users)


def delete_user(username: str):
    users = _load_users()
    if username in users:
        # protect built-ins
        if username in ('teacher', 'student'):
            raise ValueError('Cannot delete default user')
        del users[username]
        _save_users(users)


def list_users(role: str | None = None) -> dict:
    users = _load_users()
    if role is None:
        return users
    return {u: rec for u, rec in users.items() if rec.get('role') == role}


@app.before_request
def load_current_user():
    username = session.get('username')
    if username:
        u = get_user(username)
        g.user = {'username': username, 'role': u['role']} if u else None
    else:
        g.user = None


@app.context_processor
def inject_user():
    return {'current_user': g.get('user')}


def load_quiz(quiz_id: str):
    f = QUIZZES_DIR / f'{quiz_id}.json'
    if not f.exists():
        return None
    with f.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def save_quiz(quiz: dict):
    quiz_id = quiz['id']
    f = QUIZZES_DIR / f'{quiz_id}.json'
    with f.open('w', encoding='utf-8') as fh:
        json.dump(quiz, fh, indent=2, ensure_ascii=False)


def list_quizzes():
    quizzes = []
    for f in sorted(QUIZZES_DIR.glob('*.json')):
        try:
            with f.open('r', encoding='utf-8') as fh:
                q = json.load(fh)
                quizzes.append({
                    'id': q.get('id'),
                    'title': q.get('title', q.get('id')),
                    'created_at': q.get('created_at'),
                    'available_from': q.get('available_from'),
                    'available_until': q.get('available_until'),
                })
        except Exception:
            continue
    quizzes.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return quizzes


def save_response(quiz_id: str, response: dict):
    q_dir = RESPONSES_DIR / quiz_id
    q_dir.mkdir(parents=True, exist_ok=True)
    rid = response.get('id') or str(uuid.uuid4())
    with (q_dir / f'{rid}.json').open('w', encoding='utf-8') as fh:
        json.dump(response, fh, indent=2, ensure_ascii=False)


@app.route('/')
def index():
    quizzes = list_quizzes()
    # If not a teacher, filter out quizzes that are not yet available or have expired
    is_teacher = g.user and g.user.get('role') == 'teacher'
    if not is_teacher:
        now_date = datetime.now(UTC).date().isoformat()
        filtered = []
        for q in quizzes:
            start = q.get('available_from')
            end = q.get('available_until')
            if start and now_date < start:
                continue
            if end and now_date > end:
                continue
            filtered.append(q)
        quizzes = filtered
    return render_template('index.html', quizzes=quizzes)


def login_required():
    if not g.user:
        flash('Please log in to continue.', 'error')
        return redirect(url_for('login', next=request.path))


def roles_required(*roles):
    if not g.user:
        return login_required()
    if g.user['role'] not in roles:
        abort(403)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        u = get_user(username)
        if not u or not check_password_hash(u.get('password_hash', ''), password):
            flash('Invalid username or password.', 'error')
            return render_template('login.html')
        session['username'] = username
        flash(f'Logged in as {username}.', 'success')
        nxt = request.args.get('next') or url_for('index')
        return redirect(nxt)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


def _valid_username(username: str) -> bool:
    if not username:
        return False
    if len(username) > 64:
        return False
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
    return all(ch in allowed for ch in username)


@app.route('/manage/users', methods=['GET', 'POST'])
def manage_users():
    rr = roles_required('teacher')
    if rr:
        return rr
    if request.method == 'POST':
        action = request.form.get('action')
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')
        try:
            if action == 'add':
                if not _valid_username(username):
                    raise ValueError('Invalid username. Use letters, numbers, dash or underscore (max 64).')
                users = _load_users()
                if username in users:
                    raise ValueError('Username already exists.')
                set_user(username, 'student', password or 'student')
                flash(f'Added student {username}.', 'success')
            elif action == 'delete':
                delete_user(username)
                flash(f'Deleted user {username}.', 'success')
            elif action == 'reset':
                if not _valid_username(username):
                    raise ValueError('Invalid username.')
                users = _load_users()
                if username not in users:
                    raise ValueError('User not found.')
                # Keep existing role
                role = users[username].get('role', 'student')
                set_user(username, role, password or 'student')
                flash(f'Password reset for {username}.', 'success')
            else:
                flash('Unknown action.', 'error')
        except Exception as e:
            flash(str(e), 'error')

    students = sorted(list_users('student').keys())
    return render_template('manage_users.html', students=students)


@app.route('/teacher/create', methods=['GET', 'POST'])
def teacher_create():
    # Require teacher role
    rr = roles_required('teacher')
    if rr:
        return rr
    if request.method == 'GET':
        # Step 1: Ask for title, teacher email, number of questions
        return render_template('create_quiz.html', default_teacher_email=DEFAULT_TEACHER_EMAIL)

    # POST
    # already authorized above

    # Wizard step detection
    step = request.form.get('wizard_step')

    # Backward compatibility: if legacy JSON is posted, handle it
    if not step and request.form.get('questions_json'):
        title = request.form.get('title', '').strip()
        teacher_email = request.form.get('teacher_email', '').strip() or DEFAULT_TEACHER_EMAIL
        raw = request.form.get('questions_json', '').strip()

        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('teacher_create'))
        if not raw:
            flash('Questions JSON is required.', 'error')
            return redirect(url_for('teacher_create'))

        try:
            questions = json.loads(raw)
            # Validate minimal structure
            assert isinstance(questions, list) and len(questions) > 0
            for q in questions:
                assert 'text' in q and isinstance(q['text'], str) and q['text'].strip()
                assert 'options' in q and isinstance(q['options'], list) and len(q['options']) >= 2
                assert 'correct_index' in q and isinstance(q['correct_index'], int)
                assert 0 <= q['correct_index'] < len(q['options'])
        except Exception as e:
            flash(f'Invalid questions JSON: {e}', 'error')
            return redirect(url_for('teacher_create'))

        quiz_id = str(uuid.uuid4())[:8]
        quiz = {
            'id': quiz_id,
            'title': title,
            'teacher_email': teacher_email,
            'created_at': datetime.now(UTC).replace(tzinfo=None).isoformat() + 'Z',
            'questions': questions,
        }
        save_quiz(quiz)
        flash('Quiz created successfully.', 'success')
        return render_template('quiz_created.html', quiz=quiz)

    # Wizard step 1 -> render step 2 with question inputs
    if step == '1':
        title = request.form.get('title', '').strip()
        teacher_email = request.form.get('teacher_email', '').strip() or DEFAULT_TEACHER_EMAIL
        num_str = request.form.get('num_questions', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        try:
            num_questions = int(num_str)
        except ValueError:
            num_questions = 0

        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('teacher_create'))
        if num_questions <= 0 or num_questions > 50:
            flash('Please enter a valid number of questions (1-50).', 'error')
            return redirect(url_for('teacher_create'))

        idx_list = list(range(num_questions))
        return render_template(
            'create_quiz_step2.html',
            title=title,
            teacher_email=teacher_email,
            num_questions=num_questions,
            idx_list=idx_list,
            start_date=start_date,
            end_date=end_date,
        )

    # Wizard step 2 -> build questions and create quiz
    if step == '2':
        title = request.form.get('title', '').strip()
        teacher_email = request.form.get('teacher_email', '').strip() or DEFAULT_TEACHER_EMAIL
        num_str = request.form.get('num_questions', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        try:
            num_questions = int(num_str)
        except ValueError:
            num_questions = 0

        if not title or num_questions <= 0:
            flash('Invalid data. Please start over.', 'error')
            return redirect(url_for('teacher_create'))

        questions = []
        for i in range(num_questions):
            qtype = (request.form.get(f'q_type_{i}') or 'mc').strip().lower()
            text = (request.form.get(f'q_text_{i}') or '').strip()
            if not text:
                flash('Each question must have text.', 'error')
                return redirect(url_for('teacher_create'))

            if qtype == 'essay':
                reqs_raw = (request.form.get(f'q_requirements_{i}') or '').strip()
                max_pts_raw = (request.form.get(f'q_max_points_{i}') or '').strip()
                # Requirements: separated by two \n characters
                requirements = [r.strip() for r in reqs_raw.replace('\r', '').split('\n\n') if r.strip()]
                if not requirements:
                    flash('Essay questions must include at least one requirement.', 'error')
                    return redirect(url_for('teacher_create'))
                try:
                    max_points = int(max_pts_raw) if max_pts_raw else 10
                except ValueError:
                    max_points = 10
                if max_points <= 0:
                    max_points = 10
                questions.append({
                    'type': 'essay',
                    'text': text,
                    'requirements': requirements,
                    'max_points': max_points,
                })
            else:
                # Multiple choice
                options_raw = (request.form.get(f'q_options_{i}') or '').strip()
                correct_raw = (request.form.get(f'q_correct_{i}') or '').strip()
                points_raw = (request.form.get(f'q_points_{i}') or '').strip()

                if not options_raw:
                    flash('Multiple choice questions must include options.', 'error')
                    return redirect(url_for('teacher_create'))

                # Parse options: split by newlines, commas, or semicolons
                temp = options_raw.replace('\r', '\n')
                temp = temp.replace(';', '\n').replace(',', '\n')
                opts = [o.strip() for o in temp.split('\n') if o.strip()]
                if len(opts) < 2:
                    flash('Each multiple choice question must have at least two options.', 'error')
                    return redirect(url_for('teacher_create'))

                try:
                    correct_num = int(correct_raw)
                except ValueError:
                    flash('Correct option number must be a number for each multiple choice question.', 'error')
                    return redirect(url_for('teacher_create'))

                if correct_num < 1 or correct_num > len(opts):
                    flash('Correct option number must be between 1 and the number of options.', 'error')
                    return redirect(url_for('teacher_create'))

                try:
                    points = int(points_raw) if points_raw else 1
                except ValueError:
                    points = 1
                if points <= 0:
                    points = 1

                questions.append({
                    'type': 'mc',
                    'text': text,
                    'options': opts,
                    'correct_index': correct_num - 1,
                    'points': points,
                })

        quiz_id = str(uuid.uuid4())[:8]
        quiz = {
            'id': quiz_id,
            'title': title,
            'teacher_email': teacher_email,
            'created_at': datetime.now(UTC).replace(tzinfo=None).isoformat() + 'Z',
            'available_from': start_date if start_date else None,
            'available_until': end_date if end_date else None,
            'questions': questions,
        }
        save_quiz(quiz)
        flash('Quiz created successfully.', 'success')
        return render_template('quiz_created.html', quiz=quiz)

    # If we fall through, redirect back to start
    flash('Invalid request.', 'error')
    return redirect(url_for('teacher_create'))


@app.route('/quiz/<quiz_id>', methods=['GET'])
def take_quiz(quiz_id):
    quiz = load_quiz(quiz_id)
    if not quiz:
        abort(404)

    # Check date availability
    now_date = datetime.now(UTC).date().isoformat()
    if quiz.get('available_from') and now_date < quiz['available_from']:
        flash(f"This quiz is not available until {quiz['available_from']}.", 'error')
        return redirect(url_for('index'))
    if quiz.get('available_until') and now_date > quiz['available_until']:
        flash(f"This quiz expired on {quiz['available_until']}.", 'error')
        return redirect(url_for('index'))

    return render_template('take_quiz.html', quiz=quiz)


@app.route('/quiz/<quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    quiz = load_quiz(quiz_id)
    if not quiz:
        abort(404)

    student_name = request.form.get('student_name', '').strip()
    student_email = request.form.get('student_email', '').strip()

    answers = []
    for idx, q in enumerate(quiz['questions']):
        qtype = (q.get('type') or 'mc').lower()
        a = request.form.get(f'q_{idx}')
        if qtype == 'essay':
            answers.append((a or '').strip())
        else:
            try:
                answers.append(int(a) if a is not None else None)
            except ValueError:
                answers.append(None)

    result = grade_quiz(quiz, answers)

    response = {
        'id': str(uuid.uuid4()),
        'quiz_id': quiz_id,
        'student_name': student_name,
        'student_email': student_email,
        'submitted_at': datetime.now(UTC).replace(tzinfo=None).isoformat() + 'Z',
        'answers': answers,
        'result': result,
    }
    save_response(quiz_id, response)

    # Email teacher
    teacher_email = quiz.get('teacher_email') or DEFAULT_TEACHER_EMAIL
    if teacher_email:
        subject = f"Quiz Submission: {quiz.get('title')} - {student_name or 'Anonymous'} ({result['score']}/{result['total']})"
        lines = [
            f"Quiz: {quiz.get('title')} ({quiz_id})",
            f"Student: {student_name or 'Anonymous'} <{student_email or 'n/a'}>",
            f"Submitted: {response['submitted_at']}",
            f"Score: {result['score']} / {result['total']} ({result['percent']}%)",
            "",
            "Breakdown:",
        ]
        for i, (q, pq) in enumerate(zip(quiz['questions'], result.get('per_question', []))):
            qtype = (q.get('type') or 'mc').lower()
            lines.append(f"Q{i+1}. [{qtype.upper()}] {q.get('text')}")
            lines.append(f" - Awarded: {pq.get('awarded')}/{pq.get('max_points')}")
            if qtype == 'mc':
                ai = pq.get('details', {}).get('selected_index')
                ci = pq.get('details', {}).get('correct_index')
                opts = q.get('options', [])
                selected_txt = opts[ai] if isinstance(ai, int) and 0 <= ai < len(opts) else 'No answer'
                correct_txt = opts[ci] if isinstance(ci, int) and 0 <= ci < len(opts) else 'N/A'
                lines.append(f" - Selected: {selected_txt}")
                lines.append(f" - Correct: {correct_txt}")
            else:
                eg = pq.get('details', {}).get('essaygrader', {})
                backend = eg.get('backend')
                reason = (eg.get('reasons') or [''])[0]
                lines.append(f" - Essay graded via {backend}; reason: {reason}")
                # Include top deductions if available
                deds = eg.get('deductions') or []
                if deds:
                    total_ded = eg.get('total_deductions')
                    max_pts = eg.get('max_points')
                    lines.append(f" - Deductions (total {total_ded} of {max_pts}):")
                    for d in deds[:5]:  # cap to first 5 for brevity
                        cat = d.get('category')
                        cat_txt = f" [{cat}]" if cat else ""
                        lines.append(f"    • -{d.get('points', 0)}: {d.get('reason', '')}{cat_txt}")
            lines.append("")
        body = "\n".join(lines)
        send_email(teacher_email, subject, body)

    return render_template('submission_success.html', quiz=quiz, result=result, student_name=student_name)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=True)
