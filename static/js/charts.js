document.addEventListener("DOMContentLoaded", () => {
    // Check if chart canvas elements exist before initializing
    if (document.getElementById("deptChart")) {
        loadDashboardCharts();
    }
});

async function loadDashboardCharts() {
    try {
        const res = await apiRequest("/api/dashboard/charts");
        if (!res.ok) return;
        const data = await res.json();

        // 1. Department Distribution Chart
        initBarChart(
            "deptChart",
            data.department.labels,
            data.department.values,
            "Employees",
            "#3182ce"
        );

        // 2. Salary Distribution Chart
        initDoughnutChart(
            "salaryChart",
            data.salary.labels,
            data.salary.values,
            ["#E53E3E", "#DD6B20", "#D69E2E", "#3182ce", "#38A169"]
        );

        // 3. Gender Distribution Chart
        initPieChart(
            "genderChart",
            data.gender.labels,
            data.gender.values,
            ["#3182ce", "#ED64A6", "#a0aec0"]
        );

        // 4. Hiring Trends Chart
        initLineChart(
            "hiringChart",
            data.hiring.labels,
            data.hiring.values,
            "Monthly Hires",
            "#38A169"
        );

    } catch (e) {
        console.error("Error loading dashboard charts:", e);
    }
}

// ----------------- Chart.js Templates -----------------

function initBarChart(canvasId, labels, values, labelText, color) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: labelText,
                data: values,
                backgroundColor: color + "bb",
                borderColor: color,
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(200, 200, 200, 0.1)" },
                    ticks: { precision: 0 }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

function initDoughnutChart(canvasId, labels, values, bgColors) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, padding: 15 }
                }
            },
            cutout: "70%"
        }
    });
}

function initPieChart(canvasId, labels, values, bgColors) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    new Chart(ctx, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, padding: 15 }
                }
            }
        }
    });
}

function initLineChart(canvasId, labels, values, labelText, color) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    
    // Create soft gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, color + "55");
    gradient.addColorStop(1, color + "00");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: labelText,
                data: values,
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                borderWidth: 2.5,
                tension: 0.35,
                pointBackgroundColor: color,
                pointBorderColor: "#fff",
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(200, 200, 200, 0.1)" },
                    ticks: { precision: 0 }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}
