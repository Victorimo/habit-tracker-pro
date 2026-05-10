let habits = [];
let completionChart = null;
let breakdownChart = null;

// ========== Initialisation ==========

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("current-date").textContent =
        new Date().toLocaleDateString("en-IE", {
            weekday: "long", year: "numeric", month: "long", day: "numeric"
        });
    loadHabits();
});

// ========== View Switching ==========

function switchView(viewName) {
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

    document.getElementById(`view-${viewName}`).classList.add("active");
    document.querySelector(`[data-view="${viewName}"]`).classList.add("active");

    if (viewName === "analytics") loadAnalytics();
    if (viewName === "dashboard" || viewName === "habits") loadHabits();
}

// ========== API Helpers ==========

async function apiCall(url, method = "GET", body = null) {
    const options = { method, headers: { "Content-Type": "application/json" } };
    if (body) options.body = JSON.stringify(body);
    const res = await fetch(url, options);
    return res.json();
}

// ========== Habit CRUD ==========

async function loadHabits() {
    habits = await apiCall("/api/habits");
    renderDashboard();
    renderHabitsList();
}

async function saveHabit(e) {
    e.preventDefault();
    const id = document.getElementById("habit-id").value;
    const payload = {
        name: document.getElementById("habit-name").value,
        category: document.getElementById("habit-category").value,
        description: document.getElementById("habit-description").value,
        frequency: document.getElementById("habit-frequency").value,
    };

    if (id) {
        await apiCall(`/api/habits/${id}`, "PUT", payload);
    } else {
        await apiCall("/api/habits", "POST", payload);
    }
    closeModal();
    loadHabits();
}

async function deleteHabit(id) {
    if (!confirm("Delete this habit? This cannot be undone.")) return;
    await apiCall(`/api/habits/${id}`, "DELETE");
    loadHabits();
}

async function toggleComplete(habitId) {
    const today = new Date().toISOString().split("T")[0];
    const habit = habits.find(h => h.id === habitId);
    const isCompleted = habit && habit.completions.includes(today);

    if (isCompleted) {
        await apiCall(`/api/habits/${habitId}/uncomplete`, "POST", { date: today });
    } else {
        await apiCall(`/api/habits/${habitId}/complete`, "POST", { date: today });
    }
    loadHabits();
}

// ========== Modal ==========

function openModal(habit = null) {
    document.getElementById("habit-modal").style.display = "flex";
    document.getElementById("modal-title").textContent = habit ? "Edit Habit" : "New Habit";
    document.getElementById("habit-id").value = habit ? habit.id : "";
    document.getElementById("habit-name").value = habit ? habit.name : "";
    document.getElementById("habit-category").value = habit ? habit.category : "General";
    document.getElementById("habit-description").value = habit ? habit.description : "";
    document.getElementById("habit-frequency").value = habit ? habit.frequency : "daily";
}

function closeModal() {
    document.getElementById("habit-modal").style.display = "none";
    document.getElementById("habit-form").reset();
}

// ========== Rendering ==========

function renderDashboard() {
    const today = new Date().toISOString().split("T")[0];
    const completedToday = habits.filter(h => h.completions.includes(today)).length;
    const bestStreak = habits.length > 0 ? Math.max(...habits.map(h => h.current_streak || 0)) : 0;
    const avgRate = habits.length > 0
        ? Math.round((habits.reduce((s, h) => s + (h.completion_rate || 0), 0) / habits.length) * 100)
        : 0;

    document.getElementById("stat-total").textContent = habits.length;
    document.getElementById("stat-completed").textContent = completedToday;
    document.getElementById("stat-best-streak").textContent = bestStreak;
    document.getElementById("stat-rate").textContent = avgRate + "%";

    const container = document.getElementById("today-habits");
    const noMsg = document.getElementById("no-habits-msg");

    if (habits.length === 0) {
        container.innerHTML = "";
        noMsg.style.display = "block";
        return;
    }
    noMsg.style.display = "none";

    container.innerHTML = habits.map(h => {
        const done = h.completions.includes(today);
        return `
            <div class="checklist-item ${done ? 'completed' : ''}" onclick="toggleComplete('${h.id}')">
                <div class="check-circle">${done ? '✓' : ''}</div>
                <div class="checklist-info">
                    <div class="habit-name">${escapeHtml(h.name)}</div>
                    <div class="habit-meta">${h.category} · ${h.frequency}</div>
                </div>
                ${h.current_streak > 0 ? `<span class="streak-badge">🔥 ${h.current_streak} day streak</span>` : ''}
            </div>
        `;
    }).join("");
}

function renderHabitsList() {
    const container = document.getElementById("habits-list");
    if (habits.length === 0) {
        container.innerHTML = '<p class="empty-msg">No habits created yet.</p>';
        return;
    }

    container.innerHTML = habits.map(h => `
        <div class="habit-card">
            <div class="habit-card-info">
                <h4>${escapeHtml(h.name)} <span class="category-badge">${h.category}</span></h4>
                <p>${escapeHtml(h.description || 'No description')} · ${h.frequency}</p>
            </div>
            <div class="habit-card-stats">
                <div class="mini-stat">
                    <div class="mini-stat-value">${h.current_streak || 0}</div>
                    <div class="mini-stat-label">Streak</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value">${h.longest_streak || 0}</div>
                    <div class="mini-stat-label">Best</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value">${Math.round((h.completion_rate || 0) * 100)}%</div>
                    <div class="mini-stat-label">Rate</div>
                </div>
            </div>
            <div class="habit-card-actions">
                <button class="btn btn-sm btn-edit" onclick='openModal(${JSON.stringify(h).replace(/'/g, "\\'")})'>Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteHabit('${h.id}')">Delete</button>
            </div>
        </div>
    `).join("");
}

// ========== Analytics ==========

async function loadAnalytics() {
    const days = document.getElementById("analytics-period").value;
    const data = await apiCall(`/api/analytics?days=${days}`);
    renderCharts(data);
    renderAnalyticsTable(data);
}

function renderCharts(data) {
    const labels = data.date_range.map(d => {
        const date = new Date(d + "T00:00:00");
        return date.toLocaleDateString("en-IE", { weekday: "short", day: "numeric" });
    });

    // Completion Chart
    if (completionChart) completionChart.destroy();
    const ctx1 = document.getElementById("completionChart").getContext("2d");
    completionChart = new Chart(ctx1, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Completions",
                data: data.daily_totals.map(d => d.count),
                backgroundColor: "rgba(108, 92, 231, 0.6)",
                borderColor: "#6c5ce7",
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                title: { display: true, text: "Daily Completions", color: "#e8eaed", font: { size: 16 } }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: "#9aa0b0" },
                    grid: { color: "rgba(45, 50, 80, 0.5)" }
                },
                x: {
                    ticks: { color: "#9aa0b0" },
                    grid: { display: false }
                }
            }
        }
    });

    // Habit Breakdown Chart
    if (breakdownChart) breakdownChart.destroy();
    if (data.habits.length === 0) return;

    const colors = ["#6c5ce7", "#00cec9", "#fdcb6e", "#ff7675", "#74b9ff", "#a29bfe", "#55efc4"];
    const ctx2 = document.getElementById("habitBreakdownChart").getContext("2d");
    breakdownChart = new Chart(ctx2, {
        type: "doughnut",
        data: {
            labels: data.habits.map(h => h.name),
            datasets: [{
                data: data.habits.map(h => h.completions_in_period),
                backgroundColor: data.habits.map((_, i) => colors[i % colors.length]),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: "Completions by Habit", color: "#e8eaed", font: { size: 16 } },
                legend: { position: "bottom", labels: { color: "#e8eaed", padding: 16 } }
            }
        }
    });
}

function renderAnalyticsTable(data) {
    if (data.habits.length === 0) {
        document.getElementById("analytics-table").innerHTML = '<p class="empty-msg">No data to display.</p>';
        return;
    }

    let html = `<table>
        <thead><tr>
            <th>Habit</th><th>Category</th><th>Completions</th><th>Rate</th>
        </tr></thead><tbody>`;

    data.habits.forEach(h => {
        html += `<tr>
            <td>${escapeHtml(h.name)}</td>
            <td>${h.category}</td>
            <td>${h.completions_in_period} / ${h.total_possible}</td>
            <td>${Math.round(h.rate * 100)}%</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    document.getElementById("analytics-table").innerHTML = html;
}

// ========== Utilities ==========

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
