# Quizem (Flask)

A modern Python/Flask application that empowers teachers to create and deploy online quizzes with multiple-choice and essay questions. Quizem features advanced AI-driven essay grading, automated scoring, and integrated email reporting.

## Features
- **User Authentication**: Secure role-based access for teachers and students.
- **Intuitive Quiz Creation**: Build quizzes with multiple-choice and essay questions via a streamlined two-step process.
- **Teacher Dashboard**: Centralized management for student accounts, including creation, deletion, and password resets.
- **Advanced AI Essay Grading**:
  - **Semantic Similarity**: Uses vector embeddings to evaluate how well the student's answer matches the intent of the rubric.
  - **Domain Analysis**: AI acts as a subject matter expert to provide nuanced feedback.
  - **Detailed Deductions**: Transparent grading with specific reasons and point deductions for missed requirements.
  - **Local-First AI**: Powered by Ollama for privacy and speed, with a robust heuristic fallback.
- **Automated MCQ Grading**: Instant results for multiple-choice questions.
- **Email Integration**: Automatically sends student results to the teacher (SMTP) with console fallback for development.
- **File-Based Storage**: No database required; quizzes, responses, and users are stored as JSON on disk.

## Requirements
- Python 3.10+
- [Ollama](https://ollama.com) (for AI grading)
- pip

## Setup
1. **Clone and Navigate**:
   ```bash
   cd Quizem
   ```

2. **Environment Setup**:
   Create and activate a virtual environment:
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**:
   Copy the environment example and configure your settings (SMTP, Secret Key, etc.):
   ```bash
   cp .env.example .env
   # Edit .env with your favorite editor
   ```

5. **AI Model Setup**:
   Ensure Ollama is running and pull the default model:
   ```bash
   ollama pull qwen2.5:14b-instruct
   ```

## Running the Application
```bash
python app.py
```
Visit http://localhost:5000 in your browser.

### Authentication
Default accounts (pre-configured):
- **Teacher**: `teacher` / `teacher`
- **Student**: `student` / `student`

### Teacher Workflow
1. **Create Quiz**: Navigate to `Create Quiz` in the header.
   - **Step 1**: Define quiz title, teacher email, and question count.
   - **Step 2**: Enter questions. For essays, provide a specific grading rubric (one requirement per line or separated by double newlines).
2. **Manage Users**: Access the user management dashboard to add students or reset passwords.

### Student Workflow
1. Log in as a student.
2. Navigate to the shared quiz URL: `/quiz/<quiz_id>`.
3. Submit responses and receive instant confirmation.

## Configuration (.env)
| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for sessions | (Required) |
| `SMTP_HOST` | SMTP server address | |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | |
| `SMTP_PASS` | SMTP password | |
| `ESSAYGRADER_MODEL` | Ollama model name | `qwen2.5:14b-instruct` |
| `ESSAYGRADER_OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |

## Documentation
- [EssayGrader Workflow](DOCS/ESSAYGRADER_WORKFLOW.md): Detailed technical explanation of the AI grading logic.

## Data Structure
- **Quizzes**: `data/quizzes/`
- **Submissions**: `data/responses/`
- **Users**: `data/users.json`

