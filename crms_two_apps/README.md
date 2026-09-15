# CRMS — Django Two-App Communication Tutorial

A complete beginner-friendly Django project demonstrating communication and screen transitions between exactly two Django apps:

- `students`
- `classes`

The architecture follows:

```text
crms/
├── config/
├── students/
├── classes/
├── templates/
│   ├── base.html
│   ├── students/
│   └── classes/
└── static/
    └── js/
        ├── students/
        └── classes/
```

## What this project demonstrates

1. Project-level URL routing with `include()`
2. App-level URL routing
3. URL namespaces and URL reversing
4. Normal screen transitions:
   - Students → Classes
   - Classes → Students
5. Dynamic URL parameters:
   - `student_id`
   - `class_id`
6. Cross-app model relationships:
   - `Student`
   - `ClassRecord`
   - `Enrollment`
7. View → context → template
8. GET and POST
9. POST → Redirect → GET
10. JavaScript `fetch()`
11. `JsonResponse`
12. Cross-app asynchronous communication
13. CSRF protection for JavaScript POST
14. Browser Network-tab debugging

## Setup

### 1. Create and activate a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Apply migrations

```bash
python manage.py migrate
```

### 4. Create sample data

```bash
python manage.py seed_demo
```

The command creates sample students, classes, and enrollments.

### 5. Run the server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Main routes

```text
/                       Home
/students/              Student list
/students/<id>/         Student detail
/students/create/       Create student
/students/class/<id>/   Students enrolled in a class

/classes/               Class list
/classes/<id>/          Class detail
/classes/<id>/enroll/   Enroll a student
/classes/<id>/students/json/  JSON endpoint
```

## Important learning flow

Normal navigation:

```text
Browser
   ↓
URL
   ↓
App URL
   ↓
View
   ↓
Database
   ↓
Template
   ↓
Browser
```

JavaScript communication:

```text
JavaScript
   ↓ fetch()
Django URL
   ↓
View
   ↓
Database
   ↓
JsonResponse
   ↓
JavaScript
   ↓
DOM
```

## Cross-app examples

From a Students page:

```django
{% url 'classes:list' %}
```

navigates to the Classes app.

From a Classes page:

```django
{% url 'students:list' %}
```

navigates to the Students app.

From a Classes detail page:

```django
{% url 'students:by_class' class_record.id %}
```

creates a URL owned by the Students app, passing the class ID.

## Notes for students

A Django app does not directly "open" another app's screen.

The browser requests a URL. Django resolves that URL to the receiving app's view.

For example:

```text
Classes template
    ↓
/students/class/5/
    ↓
students.urls
    ↓
students_by_class()
    ↓
HTML response
    ↓
Browser
```

That is the core concept this project is designed to teach.
