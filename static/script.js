const code = document.getElementById("code");
const analyze = document.getElementById("analyze");
const clear = document.getElementById("clear");
const sampleButton = document.getElementById("sampleButton");
const themeButton = document.getElementById("themeButton");

const loading = document.getElementById("loading");

const status = document.getElementById("status");
const time = document.getElementById("time");
const space = document.getElementById("space");
const quality = document.getElementById("quality");
const functions = document.getElementById("functions");

const errors = document.getElementById("errors");
const explanation = document.getElementById("explanation");
const aiExplanation = document.getElementById("aiExplanation");
const corrected = document.getElementById("corrected");

const tests = document.getElementById("tests");
const suggestions = document.getElementById("suggestions");
const historyList = document.getElementById("historyList");

const copyButton = document.getElementById("copyButton");
const clearHistory = document.getElementById("clearHistory");


/* ==============================
   LOAD EXAMPLE
================================ */

sampleButton.addEventListener("click", () => {

    code.value = `def find_max(numbers):
    maximum = numbers[0]

    for number in numbers:
        if number > maximum:
            maximum = number

    return maximum

numbers = [10, 25, 7, 42, 18]
print(find_max(numbers))`;

});


/* ==============================
   CLEAR CODE
================================ */

clear.addEventListener("click", () => {

    code.value = "";

    status.textContent = "Waiting for code...";

});


/* ==============================
   ANALYZE
================================ */

analyze.addEventListener("click", async () => {

    const program = code.value.trim();

    if (!program) {
        alert("Please enter Python code.");
        return;
    }

    loading.classList.remove("hidden");

    try {

        const response = await fetch("/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                code: program
            })

        });

        const data = await response.json();

        displayResults(data);

        loadHistory();

    }

    catch (error) {

        alert(
            "Unable to connect to CodeMentor AI. " +
            "Make sure the Flask server is running."
        );

    }

    finally {

        loading.classList.add("hidden");

    }

});


/* ==============================
   DISPLAY RESULTS
================================ */

function displayResults(data) {

    status.textContent =
        data.status || "Analysis complete";

    time.textContent =
        data.time_complexity || "Unavailable";

    space.textContent =
        data.space_complexity || "Unavailable";

    quality.textContent =
        data.quality ?? 0;

    functions.textContent =
        data.metrics?.functions ?? 0;

    errors.textContent =
        data.errors || "No errors detected.";

    explanation.textContent =
        data.explanation || "No explanation available.";

    aiExplanation.textContent =
        data.ai_explanation ||
        "AI explanation unavailable.";

    corrected.textContent =
        data.corrected || "";

    displayTests(data.test_cases || []);

    displaySuggestions(data.suggestions || []);

}


/* ==============================
   TEST CASES
================================ */

function displayTests(items) {

    tests.innerHTML = "";

    if (items.length === 0) {

        tests.innerHTML =
            "<p>No test cases generated.</p>";

        return;
    }

    items.forEach(item => {

        const div = document.createElement("div");

        div.className = "test";

        div.innerHTML = `
            <strong>${escapeHtml(item.name)}</strong>
            <br>
            <b>Input:</b> ${escapeHtml(item.input)}
            <br>
            <b>Expected:</b> ${escapeHtml(item.expected)}
        `;

        tests.appendChild(div);

    });

}


/* ==============================
   SUGGESTIONS
================================ */

function displaySuggestions(items) {

    suggestions.innerHTML = "";

    if (items.length === 0) {

        suggestions.innerHTML =
            "<li>No major suggestions.</li>";

        return;
    }

    items.forEach(item => {

        const li = document.createElement("li");

        li.textContent = item;

        suggestions.appendChild(li);

    });

}


/* ==============================
   COPY CODE
================================ */

copyButton.addEventListener("click", async () => {

    try {

        await navigator.clipboard.writeText(
            corrected.textContent
        );

        copyButton.textContent = "Copied!";

        setTimeout(() => {

            copyButton.textContent = "📋 Copy";

        }, 1500);

    }

    catch (error) {

        alert("Unable to copy the code.");

    }

});


/* ==============================
   HISTORY
================================ */

async function loadHistory() {

    try {

        const response = await fetch("/history");

        const data = await response.json();

        historyList.innerHTML = "";

        if (data.length === 0) {

            historyList.innerHTML =
                "<p>No analyses yet.</p>";

            return;
        }

        data.forEach(item => {

            const div = document.createElement("div");

            div.className = "history-item";

            div.innerHTML = `
                <strong>Analysis #${item.id}</strong>
                <br>
                Status: ${escapeHtml(item.status)}
                <br>
                Time: ${escapeHtml(item.time_complexity || "-")}
                <br>
                Space: ${escapeHtml(item.space_complexity || "-")}
                <br>
                Quality: ${item.quality}/100
                <br>
                <small>${escapeHtml(item.created_at)}</small>
            `;

            historyList.appendChild(div);

        });

    }

    catch (error) {

        historyList.innerHTML =
            "<p>Unable to load history.</p>";

    }

}


/* ==============================
   CLEAR HISTORY
================================ */

clearHistory.addEventListener("click", async () => {

    if (!confirm(
        "Are you sure you want to clear analysis history?"
    )) {
        return;
    }

    try {

        await fetch("/clear-history", {
            method: "POST"
        });

        loadHistory();

    }

    catch (error) {

        alert("Unable to clear history.");

    }

});


/* ==============================
   DARK MODE
================================ */

themeButton.addEventListener("click", () => {

    document.body.classList.toggle("dark");

    if (document.body.classList.contains("dark")) {

        themeButton.textContent = "☀️";

        localStorage.setItem(
            "codementor-theme",
            "dark"
        );

    }

    else {

        themeButton.textContent = "🌙";

        localStorage.setItem(
            "codementor-theme",
            "light"
        );

    }

});


/* ==============================
   REMEMBER THEME
================================ */

if (
    localStorage.getItem("codementor-theme") === "dark"
) {

    document.body.classList.add("dark");

    themeButton.textContent = "☀️";

}


/* ==============================
   SECURITY
================================ */

function escapeHtml(value) {

    const div = document.createElement("div");

    div.textContent = value ?? "";

    return div.innerHTML;

}


/* ==============================
   START
================================ */

loadHistory();