# QuizMaker (Flask)

A Python/Flask application that lets a teacher create and deploy online quizzes with multiple-choice and essay questions, automatically grades student submissions (using AI for essay grading), and emails the student's answers and grade back to the teacher.

## Features
- Create quizzes with multiple-choice and essay questions using a simple two-step form (no JSON required).
- Share a public URL for students to take the quiz.
- Automatic grading upon submission:
  - Multiple-choice questions: graded against answer key
  - Essay questions: graded using AI model  based on teacher-provided rubric
- Emails the student's answers and grade to the teacher (SMTP), with a console fallback.
- Stores quizzes and responses as JSON files on disk.

## Requirements
- Python 3.10+
- pip

## Setup
1. Create and activate a virtual environment (recommended):
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     py -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment example and edit as needed:
   ```bash
   cp .env.example .env
   # edit .env
   ```

## Running
```bash
python app.py
```
Visit http://localhost:5000

### Teacher Create Page
Navigate to:
```
/teacher/create?token=YOUR_TOKEN
```
Default token is `changeme`. You should change TEACHER_TOKEN in your .env.

Use the two-step form (no JSON required):
1. Step 1: Enter quiz Title, Teacher Email, and Number of Questions.
2. Step 2: For each question, provide:
   - Question Type: Multiple Choice or Essay
   - Question Text
   - For Multiple Choice:
     - Options: enter one option per line (you can also separate with commas or semicolons)
     - Correct Option Number (1-based, e.g., 2 for the second option)
   - For Essay:
     - Grading Rubric: instructions for the AI grader on how to evaluate the essay
     - Points: maximum points for the essay question
The app will build the JSON for you automatically.

Note: For backwards compatibility, the endpoint still accepts a questions_json payload if provided programmatically.

### Student Quiz Page
After creating a quiz, you will see a shareable link like:
```
/quiz/<quiz_id>
```
Share that link with students.

## Configuration
Set environment variables via `.env` file:

### SMTP/Email Settings
- SMTP_HOST
- SMTP_PORT (default 587)
- SMTP_USER
- SMTP_PASS
- SMTP_USE_TLS (default true)
- FROM_EMAIL (optional; defaults to SMTP_USER)
- TEACHER_EMAIL (default teacher email if not set during creation)

### Application Settings
- TEACHER_TOKEN (access token for create page)
- FLASK_SECRET_KEY (session/flash messages)

### AI Grading (for essay questions)
- ANTHROPIC_API_KEY (required for AI essay grading)

If SMTP is not configured, the app will print the email content to the console as a fallback so you can still retrieve the results.

## Data Storage
- Quizzes: `data/quizzes/<quiz_id>.json`
- Responses: `data/responses/<quiz_id>/<submission_id>.json`

## Notes
- This is a minimal educational sample; for production, consider proper authentication, a database, CSRF protection, and rate limiting.
