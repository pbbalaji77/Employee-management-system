// Theme Management (Light / Dark Mode)
document.addEventListener("DOMContentLoaded", () => {
    const currentTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeIcon(currentTheme);

    const themeToggle = document.getElementById("themeToggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const activeTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = activeTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            updateThemeIcon(newTheme);
        });
    }

    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarContainer = document.querySelector(".sidebar-container");
    if (sidebarToggle && sidebarContainer) {
        sidebarToggle.addEventListener("click", () => {
            sidebarContainer.classList.toggle("active");
        });
    }

    // Initialize check-in / check-out button handlers
    initAttendanceButtons();

    // Fetch notifications in background
    if (isAuthenticated()) {
        fetchNotifications();
        setInterval(fetchNotifications, 15000); // Poll notifications every 15s
    }
});

function updateThemeIcon(theme) {
    const icon = document.querySelector("#themeToggle i");
    if (!icon) return;
    if (theme === "dark") {
        icon.className = "bi bi-sun-fill text-warning";
    } else {
        icon.className = "bi bi-moon-fill text-primary";
    }
}

// Check if user has token stored (used to authenticate REST APIs)
function isAuthenticated() {
    return localStorage.getItem("jwt_token") !== null;
}

// General API request helper that injects JWT token automatically
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem("jwt_token");
    const headers = options.headers || {};
    
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    
    // Set content-type to JSON by default unless it is FormData
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    
    options.headers = headers;
    const response = await fetch(url, options);
    
    if (response.status === 401) {
        // Token might have expired, but session remains
        console.warn("API returned 401. Unauthorized.");
    }
    
    return response;
}

// ----------------- Notification Fetcher & UI updates -----------------

async function fetchNotifications() {
    try {
        const res = await apiRequest("/api/notifications");
        if (!res.ok) return;
        const notifications = await res.json();
        
        // Count unread
        const unreadCount = notifications.filter(n => !n.is_read).length;
        const badges = document.querySelectorAll(".notif-count-badge");
        badges.forEach(badge => {
            badge.innerText = unreadCount;
            badge.style.display = unreadCount > 0 ? "block" : "none";
        });
        
        // Render dropdown items
        const container = document.getElementById("notifDropdownMenu");
        if (container) {
            if (notifications.length === 0) {
                container.innerHTML = '<li><a class="dropdown-item text-muted text-center py-2" href="#">No notifications</a></li>';
                return;
            }
            
            let html = "";
            notifications.slice(0, 5).forEach(n => {
                const readStyle = n.is_read ? "" : "font-weight-bold bg-light";
                html += `
                    <li>
                        <div class="dropdown-item py-2 border-bottom ${readStyle}" onclick="markNotificationRead(${n.id}, this)">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="small font-weight-bold text-primary">${n.title}</span>
                                <span class="text-muted" style="font-size: 0.7rem;">${formatTime(n.created_at)}</span>
                            </div>
                            <p class="mb-0 text-truncate" style="font-size: 0.8rem; max-width: 250px;">${n.message}</p>
                        </div>
                    </li>
                `;
            });
            container.innerHTML = html;
        }
    } catch (e) {
        console.error("Failed to fetch notifications:", e);
    }
}

async function markNotificationRead(id, element) {
    try {
        const res = await apiRequest(`/api/notifications/${id}/read`, { method: "PUT" });
        if (res.ok) {
            element.classList.remove("font-weight-bold", "bg-light");
            fetchNotifications(); // Refresh badge counts
        }
    } catch (e) {
        console.error(e);
    }
}

// ----------------- Attendance Buttons handlers -----------------

function initAttendanceButtons() {
    const btnCheckIn = document.getElementById("btnCheckIn");
    const btnCheckOut = document.getElementById("btnCheckOut");
    
    if (btnCheckIn) {
        btnCheckIn.addEventListener("click", async () => {
            try {
                const res = await apiRequest("/api/attendance/check-in", { method: "POST" });
                const data = await res.json();
                if (res.ok) {
                    showToast("Checked in successfully!", "success");
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast(data.message || "Failed to check in.", "danger");
                }
            } catch (e) {
                showToast("Network error occurred.", "danger");
            }
        });
    }
    
    if (btnCheckOut) {
        btnCheckOut.addEventListener("click", async () => {
            try {
                const res = await apiRequest("/api/attendance/check-out", { method: "POST" });
                const data = await res.json();
                if (res.ok) {
                    showToast("Checked out successfully!", "success");
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast(data.message || "Failed to check out.", "danger");
                }
            } catch (e) {
                showToast("Network error occurred.", "danger");
            }
        });
    }
}

// ----------------- Helpers -----------------

function showToast(message, type = "success") {
    // Check if bootstrap toast element exists, otherwise alert
    const toastContainer = document.getElementById("toastContainer");
    if (!toastContainer) {
        alert(message);
        return;
    }
    
    const toastId = "toast_" + Date.now();
    const bgClass = type === "success" ? "bg-success text-white" : "bg-danger text-white";
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML("beforeend", toastHtml);
    const toastElem = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastElem, { delay: 3000 });
    bsToast.show();
    
    // Remove toast from DOM after hidden
    toastElem.addEventListener("hidden.bs.toast", () => {
        toastElem.remove();
    });
}

function formatTime(isoStr) {
    if (!isoStr) return "";
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
