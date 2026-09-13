from flask import Flask, render_template, request, jsonify, send_file
import ast
import sqlite3
import os
import io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), "data", "codementor.db")
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)


# ==============================
# DATABASE
# ==============================

def init_database():
    os.makedirs("data", exist_ok=True)

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            status TEXT NOT NULL,
            time_complexity TEXT,
            space_complexity TEXT,
            quality INTEGER,
            created_at TEXT
        )
    """)

    connection.commit()
    connection.close()

init_database()


def save_analysis(code, status, time, space, quality):
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO analyses
        (code, status, time_complexity, space_complexity,
         quality, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        code,
        status,
        time,
        space,
        quality,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    connection.commit()
    connection.close()


# ==============================
# AST CODE ANALYZER
# ==============================

class CodeAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.functions = 0
        self.classes = 0
        self.loops = 0
        self.conditions = 0
        self.imports = 0
        self.assignments = 0
        self.returns = 0
        self.calls = 0

        self.loop_depth = 0
        self.max_loop_depth = 0

        self.current_function = None
        self.recursive_functions = 0

    def visit_FunctionDef(self, node):
        previous = self.current_function
        self.current_function = node.name

        self.functions += 1

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == node.name:
                        self.recursive_functions += 1

        self.generic_visit(node)

        self.current_function = previous

    def visit_AsyncFunctionDef(self, node):
        self.functions += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.loops += 1
        self.loop_depth += 1

        self.max_loop_depth = max(
            self.max_loop_depth,
            self.loop_depth
        )

        self.generic_visit(node)

        self.loop_depth -= 1

    def visit_While(self, node):
        self.loops += 1
        self.loop_depth += 1

        self.max_loop_depth = max(
            self.max_loop_depth,
            self.loop_depth
        )

        self.generic_visit(node)

        self.loop_depth -= 1

    def visit_If(self, node):
        self.conditions += 1
        self.generic_visit(node)

    def visit_Import(self, node):
        self.imports += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imports += 1
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.assignments += 1
        self.generic_visit(node)

    def visit_Return(self, node):
        self.returns += 1
        self.generic_visit(node)

    def visit_Call(self, node):
        self.calls += 1
        self.generic_visit(node)


# ==============================
# COMPLEXITY ANALYSIS
# ==============================

def calculate_complexity(analyzer, code):

    if analyzer.recursive_functions > 0:
        time = "O(2^n) approximately"

    elif analyzer.max_loop_depth >= 3:
        time = "O(n^3) approximately"

    elif analyzer.max_loop_depth == 2:
        time = "O(n^2) approximately"

    elif "sorted(" in code or ".sort(" in code:
        time = "O(n log n) approximately"

    elif analyzer.loops == 1:
        time = "O(n) approximately"

    else:
        time = "O(1) approximately"


    if analyzer.loops > 0:
        space = "O(n) approximately"

    elif any(
        item in code
        for item in [
            "[x for x in",
            "[i for i in",
            "list(",
            "set(",
            "dict("
        ]
    ):
        space = "O(n) approximately"

    else:
        space = "O(1) approximately"


    return time, space


# ==============================
# CODE QUALITY
# ==============================

def calculate_quality(code, analyzer):

    score = 100

    lines = code.splitlines()

    if len(lines) > 100:
        score -= 15

    elif len(lines) > 50:
        score -= 8


    if analyzer.max_loop_depth >= 3:
        score -= 10

    elif analyzer.max_loop_depth == 2:
        score -= 5


    if analyzer.functions == 0 and len(lines) > 30:
        score -= 8


    if "except:" in code:
        score -= 10


    if "global " in code:
        score -= 5


    long_lines = sum(
        1 for line in lines
        if len(line) > 100
    )

    if long_lines > 3:
        score -= 5


    if len(code.strip()) < 10:
        score -= 10


    return max(0, min(score, 100))


# ==============================
# SUGGESTIONS
# ==============================

def generate_suggestions(code, analyzer, quality):

    suggestions = []


    if analyzer.max_loop_depth >= 2:
        suggestions.append(
            "Nested loops were detected. Consider using "
            "sets, dictionaries, sorting, or a more efficient "
            "algorithm where possible."
        )


    if analyzer.recursive_functions > 0:
        suggestions.append(
            "Recursive logic was detected. Consider "
            "memoization or dynamic programming when "
            "the same subproblems are calculated repeatedly."
        )


    if analyzer.conditions >= 5:
        suggestions.append(
            "Many conditional branches were detected. "
            "Consider simplifying the decision logic."
        )


    if "except:" in code:
        suggestions.append(
            "Avoid bare except blocks. Catch specific "
            "exception types instead."
        )


    if "global " in code:
        suggestions.append(
            "Avoid unnecessary global variables. "
            "Prefer function parameters and return values."
        )


    if "input(" in code:
        suggestions.append(
            "Keep input handling separate from core logic "
            "to make your functions easier to test."
        )


    if "print(" in code:
        suggestions.append(
            "For larger applications, consider using "
            "logging instead of print statements."
        )


    if analyzer.functions == 0 and len(code.splitlines()) > 25:
        suggestions.append(
            "Break the program into smaller reusable functions."
        )


    if quality >= 90:
        suggestions.append(
            "The code has a strong basic structure. "
            "Continue improving edge-case handling, "
            "documentation and algorithm efficiency."
        )


    if not suggestions:
        suggestions.append(
            "No major structural issues were detected."
        )


    return suggestions


# ==============================
# CODE EXPLANATION
# ==============================

def generate_explanation(analyzer):

    explanation = []


    if analyzer.functions > 0:
        explanation.append(
            f"The program contains {analyzer.functions} function(s)."
        )


    if analyzer.classes > 0:
        explanation.append(
            f"It contains {analyzer.classes} class(es)."
        )


    if analyzer.loops > 0:
        explanation.append(
            f"The program contains {analyzer.loops} loop(s)."
        )


    if analyzer.conditions > 0:
        explanation.append(
            f"It contains {analyzer.conditions} conditional statement(s)."
        )


    if analyzer.imports > 0:
        explanation.append(
            f"It uses {analyzer.imports} import statement(s)."
        )


    if analyzer.recursive_functions > 0:
        explanation.append(
            "Recursive function calls were detected."
        )


    if not explanation:
        explanation.append(
            "The program mainly consists of straightforward "
            "Python statements."
        )


    return " ".join(explanation)


# ==============================
# TEST CASE GENERATION
# ==============================

def generate_test_cases(code):

    if "def " in code:

        return [
            {
                "name": "Normal Case",
                "input": "Typical valid input",
                "expected": "Correct expected result"
            },
            {
                "name": "Empty Case",
                "input": "Empty or minimal input",
                "expected": "Program handles it safely"
            },
            {
                "name": "Boundary Case",
                "input": "Minimum or maximum valid value",
                "expected": "Correct boundary result"
            },
            {
                "name": "Large Input",
                "input": "Large dataset",
                "expected": "Correct result with acceptable performance"
            }
        ]


    return [
        {
            "name": "Normal Execution",
            "input": "Normal input",
            "expected": "Program completes successfully"
        },
        {
            "name": "Edge Case",
            "input": "Unexpected or boundary input",
            "expected": "Program handles the situation safely"
        }
    ]


# ==============================
# SIMPLE CODE IMPROVEMENT
# ==============================

def generate_corrected_code(code):

    corrected = code

    corrected = corrected.replace(
        "except:",
        "except Exception:"
    )

    return corrected


# ==============================
# AI MENTOR
# ==============================

def get_ai_analysis(code):

    api_key = os.getenv("OPENAI_API_KEY")


    if not api_key:
        return (
            "AI Mentor is available but no API key has been "
            "configured. Add OPENAI_API_KEY to your .env file "
            "to enable AI-powered explanations."
        )


    try:

        from openai import OpenAI

        client = OpenAI(api_key=api_key)


        response = client.responses.create(

            model="gpt-5.6-luna",

            input=f"""
You are CodeMentor AI, an expert Python programming mentor.

Analyze this Python code for a student.

Explain:

1. What the program does
2. How the logic works
3. Important Python concepts used
4. Possible bugs
5. Time complexity
6. Space complexity
7. Improvements
8. Important edge cases
9. What the student should learn

Use clear and simple language.

Python code:

{code}
"""
        )


        return response.output_text


    except Exception as error:

        return (
            "AI Mentor could not be reached right now. "
            "The local CodeMentor analyzer is still working."
        )


# ==============================
# HOME
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


# ==============================
# ANALYZE CODE
# ==============================

@app.route("/analyze", methods=["POST"])
def analyze():

    data = request.get_json(silent=True) or {}

    code = data.get("code", "").strip()


    if not code:

        return jsonify({
            "success": False,
            "message": "Please enter Python code."
        })


    # Syntax analysis

    try:
        tree = ast.parse(code)

    except SyntaxError as error:

        return jsonify({

            "success": True,

            "status": "SYNTAX ERROR",

            "errors": (
                f"{error.msg} at line "
                f"{error.lineno}, column "
                f"{error.offset}"
            ),

            "explanation": (
                "Python could not parse the program. "
                "Fix the syntax error before deeper analysis."
            ),

            "corrected": code,

            "time_complexity": "Unavailable",

            "space_complexity": "Unavailable",

            "quality": 0,

            "test_cases": [],

            "suggestions": [
                "Check brackets and parentheses.",
                "Check quotation marks.",
                "Check indentation.",
                "Check colons after if, for, while and def."
            ],

            "ai_explanation": "",

            "metrics": {}

        })


    # AST analysis

    analyzer = CodeAnalyzer()

    analyzer.visit(tree)


    # Complexity

    time, space = calculate_complexity(
        analyzer,
        code
    )


    # Quality

    quality = calculate_quality(
        code,
        analyzer
    )


    # Suggestions

    suggestion_list = generate_suggestions(
        code,
        analyzer,
        quality
    )


    # Explanation

    explanation = generate_explanation(
        analyzer
    )


    # Test cases

    tests = generate_test_cases(
        code
    )


    # Corrected code

    fixed_code = generate_corrected_code(
        code
    )


    # AI

    ai_explanation = get_ai_analysis(
        code
    )


    # Save

    save_analysis(
        code,
        "ANALYSIS COMPLETE",
        time,
        space,
        quality
    )


    return jsonify({

        "success": True,

        "status": "ANALYSIS COMPLETE",

        "errors":
            "No syntax errors detected.",

        "explanation":
            explanation,

        "corrected":
            fixed_code,

        "time_complexity":
            time,

        "space_complexity":
            space,

        "quality":
            quality,

        "test_cases":
            tests,

        "suggestions":
            suggestion_list,

        "ai_explanation":
            ai_explanation,

        "metrics": {

            "functions":
                analyzer.functions,

            "classes":
                analyzer.classes,

            "loops":
                analyzer.loops,

            "conditions":
                analyzer.conditions,

            "imports":
                analyzer.imports,

            "assignments":
                analyzer.assignments,

            "returns":
                analyzer.returns,

            "calls":
                analyzer.calls

        }

    })


# ==============================
# HISTORY
# ==============================

@app.route("/history")
def history():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()


    cursor.execute("""
        SELECT
            id,
            status,
            time_complexity,
            space_complexity,
            quality,
            created_at
        FROM analyses
        ORDER BY id DESC
        LIMIT 20
    """)


    rows = cursor.fetchall()

    connection.close()


    return jsonify([
        dict(row)
        for row in rows
    ])


# ==============================
# CLEAR HISTORY
# ==============================

@app.route("/clear-history", methods=["POST"])
def clear_history():

    connection = sqlite3.connect(DATABASE)

    connection.execute(
        "DELETE FROM analyses"
    )

    connection.commit()

    connection.close()


    return jsonify({
        "success": True
    })


# ==============================
# DOWNLOAD REPORT
# ==============================

@app.route("/report", methods=["POST"])
def report():

    data = request.get_json(
        silent=True
    ) or {}


    suggestions_text = "\n".join(
        "- " + item
        for item in data.get(
            "suggestions",
            []
        )
    )


    report_text = f"""
CODEMENTOR AI
PYTHON CODE ANALYSIS REPORT
========================================

Generated:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

STATUS:
{data.get("status", "")}

ERRORS:
{data.get("errors", "")}

EXPLANATION:
{data.get("explanation", "")}

TIME COMPLEXITY:
{data.get("time_complexity", "")}

SPACE COMPLEXITY:
{data.get("space_complexity", "")}

CODE QUALITY:
{data.get("quality", "")}/100

CORRECTED CODE:
----------------------------------------
{data.get("corrected", "")}

SUGGESTIONS:
----------------------------------------
{suggestions_text}
"""


    file = io.BytesIO(
        report_text.encode("utf-8")
    )

    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name="CodeMentor_Analysis_Report.txt",
        mimetype="text/plain"
    )


# ==============================
# START APPLICATION
# ==============================

if __name__ == "__main__":

    init_database()

    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    debug=True
)
