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
- **PostgreSQL Storage**: Secure and scalable storage for quizzes, responses, and users using a PostgreSQL database.

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

5. **Database Setup**:
   (Optional) Ensure you have a PostgreSQL server running and create a database named `quizem`.
   Set the `DATABASE_URL` in your `.env` file if using PostgreSQL:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/quizem
   ```
   If `DATABASE_URL` is not provided, the application will use a local SQLite database (`instance/quizem.db`) by default.
   Run the migration script to initialize the database and migrate any existing JSON data:
   ```bash
   python migrate_to_db.py
   ```

6. **AI Model Setup**:
   Ensure Ollama is running and pull the default model:
   ```bash
   ollama pull llama3.1:8b
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
| `ESSAYGRADER_MODEL` | Ollama model name | `llama3.1:8b` |
| `ESSAYGRADER_OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API Key (Optional) | |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |
| `DATABASE_URL` | Database connection string (Postgres, etc.) | `sqlite:///quizem.db` |

## Documentation
- [EssayGrader Workflow](DOCS/ESSAYGRADER_WORKFLOW.md): Detailed technical explanation of the AI grading logic.

## Data Structure
Data is stored in a PostgreSQL database with the following tables:
- **users**: User accounts and roles.
- **courses**: Course definitions and student enrollments.
- **quizzes**: Quiz definitions and questions (stored as JSON/JSONB).
- **responses**: Student submissions and grading results (stored as JSON/JSONB).

