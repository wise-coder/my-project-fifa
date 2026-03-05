/**
 * FIFA Stats Platform - Main JavaScript
 * ============================================
 * This file handles all frontend functionality for the dashboard.
 * Now integrated with Flask backend API.
 */

// ============================================
// CONFIGURATION
// ============================================

const API_BASE_URL = 'http://127.0.0.1:5000/api';

// ============================================
// GLOBAL VARIABLES
// ============================================

// Store user data from localStorage
let currentUser = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    checkAuthentication();
    
    // Initialize components
    initializeSidebar();
    initializeUpload();
    initializeLogout();
    
    // Load user data
    loadUserData();
    
    // Load dashboard data
    loadProgressData();
    loadLeaderboardData();
    loadNotifications();
});

/**
 * Check if user is authenticated
 */
function checkAuthentication() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');
    
    if (!token || !user) {
        // Not logged in, redirect to login
        window.location.href = 'login.html';
        return;
    }
    
    try {
        currentUser = JSON.parse(user);
    } catch (e) {
        console.error('Error parsing user data:', e);
        window.location.href = 'login.html';
    }
}

/**
 * Load user data and update UI
 */
function loadUserData() {
    if (currentUser) {
        const usernameElements = document.querySelectorAll('#displayUsername');
        usernameElements.forEach(el => {
            el.textContent = currentUser.username || 'User';
        });
    }
}

// ============================================
// API FUNCTIONS
// ============================================

/**
 * Make API request with authentication
 */
async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('authToken');
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        },
        credentials: 'include'  // Important: Send cookies with requests
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Load progress data from API
 */
async function loadProgressData() {
    try {
        // Show loading state
        document.getElementById('matchesPlayed').textContent = '-';
        document.getElementById('totalWins').textContent = '-';
        document.getElementById('totalLosses').textContent = '-';
        document.getElementById('totalPoints').textContent = '-';
        
        // Call API
        const response = await apiRequest('/progress');
        
        if (response.success && response.data) {
            const stats = response.data;
            
            // Update stats with real dynamic data from database
            document.getElementById('matchesPlayed').textContent = stats.matches_played || 0;
            document.getElementById('totalWins').textContent = stats.wins || 0;
            document.getElementById('totalLosses').textContent = stats.losses || 0;
            document.getElementById('totalPoints').textContent = (stats.total_points || 0).toLocaleString();
            
            // Update progress bars with animation using real data from API
            animateProgressBar('winRateBar', 'winRateBarText', stats.win_rate || 0);
            animateProgressBar('seasonProgressBar', 'seasonProgressBarText', stats.season_progress || 0);
            animateGoalsBar(stats.total_goals || 0);
        }
    } catch (error) {
        console.error('Error loading progress:', error);
        // Use demo data as fallback
        loadDemoProgressData();
    }
}

/**
 * Load demo progress data (fallback)
 */
function loadDemoProgressData() {
    const progressData = {
        matchesPlayed: 47,
        wins: 28,
        losses: 19,
        points: 2850,
        winRate: 60,
        seasonProgress: 75,
        goals: 82
    };
    
    document.getElementById('matchesPlayed').textContent = progressData.matchesPlayed;
    document.getElementById('totalWins').textContent = progressData.wins;
    document.getElementById('totalLosses').textContent = progressData.losses;
    document.getElementById('totalPoints').textContent = progressData.points.toLocaleString();
    
    animateProgressBar('winRateBar', 'winRateBarText', progressData.winRate);
    animateProgressBar('seasonProgressBar', 'seasonProgressBarText', progressData.seasonProgress);
    animateGoalsBar(progressData.goals);
}

/**
 * Load leaderboard data from API
 */
async function loadLeaderboardData() {
    try {
        // Call API
        const response = await apiRequest('/leaderboard?limit=10');
        
        if (response.success && response.data) {
            renderLeaderboard(response.data.leaderboard);
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        // Use demo data as fallback
        loadDemoLeaderboardData();
    }
}

/**
 * Render leaderboard table
 */
function renderLeaderboard(leaderboard) {
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';
    
    leaderboard.forEach((player) => {
        const rankClass = player.rank === 1 ? 'gold' : 
                        player.rank === 2 ? 'silver' : 
                        player.rank === 3 ? 'bronze' : '';
        
        const row = `
            <tr>
                <td class="rank-cell ${rankClass}">${player.rank}</td>
                <td>
                    <div class="player-cell">
                        <div class="player-avatar">
                            <i class="fas fa-user"></i>
                        </div>
                        <span>${player.username}</span>
                    </div>
                </td>
                <td class="score-cell">${player.total_score.toLocaleString()}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

/**
 * Load demo leaderboard data (fallback)
 */
function loadDemoLeaderboardData() {
    const leaderboardData = [
        { rank: 1, username: 'ProGamer_99', total_score: 2450 },
        { rank: 2, username: 'FIFA_Legend', total_score: 2380 },
        { rank: 3, username: 'Champion_2024', total_score: 2290 },
        { rank: 4, username: 'ElitePlayer', total_score: 2150 },
        { rank: 5, username: 'MasterChief', total_score: 2080 }
    ];
    
    renderLeaderboard(leaderboardData);
}

/**
 * Load notifications from API
 */
async function loadNotifications() {
    try {
        // Call API
        const response = await apiRequest('/notifications?limit=20');
        
        if (response.success && response.data) {
            renderNotifications(response.data.notifications);
            
            // Update badge
            const unreadCount = response.data.unread_count || 0;
            document.getElementById('notificationBadge').textContent = unreadCount;
            document.getElementById('notificationBadge').style.display = unreadCount > 0 ? 'flex' : 'none';
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        // Use demo data as fallback
        loadDemoNotifications();
    }
}

/**
 * Render notifications list
 */
function renderNotifications(notifications) {
    const list = document.getElementById('notificationList');
    list.innerHTML = '';
    
    notifications.forEach(notification => {
        // Derive type from message content if not provided
        let notificationType = notification.type || 'info';
        if (!notification.type) {
            const msg = notification.message.toLowerCase();
            if (msg.includes('welcome') || msg.includes('congratulations') || msg.includes('trophy') || msg.includes('score')) {
                notificationType = 'success';
            } else if (msg.includes('review') || msg.includes('warning') || msg.includes('failed')) {
                notificationType = 'warning';
            } else {
                notificationType = 'info';
            }
        }
        
        // Derive title from message if not provided
        let title = notification.title || 'Notification';
        if (!notification.title) {
            const msg = notification.message.toLowerCase();
            if (msg.includes('welcome')) title = 'Welcome!';
            else if (msg.includes('score') || msg.includes('points')) title = 'Match Score';
            else if (msg.includes('uploaded')) title = 'Upload Complete';
            else if (msg.includes('leaderboard')) title = 'Leaderboard Update';
            else if (msg.includes('congratulations')) title = 'Congratulations!';
            else title = 'Notification';
        }
        
        const iconClass = notificationType === 'success' ? 'success' :
                         notificationType === 'warning' ? 'warning' : 'info';
        
        const icon = notificationType === 'success' ? 'fa-trophy' :
                    notificationType === 'warning' ? 'fa-exclamation-triangle' : 'fa-bell';
        
        const item = `
            <li class="notification-item ${notification.is_read ? '' : 'unread'}" data-id="${notification.id}">
                <div class="notification-icon ${iconClass}">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="notification-content">
                    <h4>${title}</h4>
                    <p>${notification.message}</p>
                    <span class="notification-time">${notification.date ? new Date(notification.date).toLocaleDateString() : 'Just now'}</span>
                </div>
            </li>
        `;
        list.innerHTML += item;
    });
    
    // Add click handlers to mark as read
    document.querySelectorAll('.notification-item').forEach(item => {
        item.addEventListener('click', function() {
            markNotificationAsRead(this.dataset.id);
        });
    });
}

/**
 * Load demo notifications (fallback)
 */
function loadDemoNotifications() {
    const notificationsData = [
        { id: 1, type: 'success', title: 'Congratulations!', message: 'You moved up to rank #15 on the leaderboard!', date: new Date(Date.now() - 2*60*60*1000).toISOString(), is_read: false },
        { id: 2, type: 'info', title: 'Match Result', message: 'Your match has been processed. You won!', date: new Date(Date.now() - 5*60*60*1000).toISOString(), is_read: false },
        { id: 3, type: 'warning', title: 'Screenshot Review', message: 'One of your screenshots is under review.', date: new Date(Date.now() - 24*60*60*1000).toISOString(), is_read: false },
        { id: 4, type: 'info', title: 'Welcome to FIFA Stats!', message: 'Start uploading your match screenshots.', date: new Date(Date.now() - 3*24*60*60*1000).toISOString(), is_read: true }
    ];
    
    renderNotifications(notificationsData);
}

/**
 * Mark notification as read
 */
async function markNotificationAsRead(id) {
    try {
        await apiRequest(`/notifications/${id}/read`, 'PUT');
        
        // Update UI
        const item = document.querySelector(`.notification-item[data-id="${id}"]`);
        if (item) {
            item.classList.remove('unread');
        }
        
        // Update badge
        const unreadItems = document.querySelectorAll('.notification-item.unread');
        const unreadCount = unreadItems.length;
        document.getElementById('notificationBadge').textContent = unreadCount;
        document.getElementById('notificationBadge').style.display = unreadCount > 0 ? 'flex' : 'none';
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

// ============================================
// UI ANIMATIONS
// ============================================

/**
 * Animate progress bar
 */
function animateProgressBar(barId, textId, targetValue) {
    const bar = document.getElementById(barId);
    const text = document.getElementById(textId);
    let current = 0;
    const duration = 1000;
    const increment = targetValue / (duration / 16);
    
    const animate = () => {
        current += increment;
        if (current >= targetValue) {
            current = targetValue;
            bar.style.width = current + '%';
            text.textContent = current + '%';
            return;
        }
        bar.style.width = current + '%';
        text.textContent = Math.round(current) + '%';
        requestAnimationFrame(animate);
    };
    
    setTimeout(animate, 100);
}

/**
 * Animate goals bar
 */
function animateGoalsBar(goals) {
    const targetValue = Math.min((goals / 100) * 100, 100);
    const bar = document.getElementById('goalsBar');
    const text = document.getElementById('goalsBarText');
    const valueText = document.getElementById('goalsValue');
    let current = 0;
    const duration = 1000;
    const increment = targetValue / (duration / 16);
    
    const animate = () => {
        current += increment;
        if (current >= targetValue) {
            current = targetValue;
            bar.style.width = current + '%';
            text.textContent = Math.round(current) + '%';
            valueText.textContent = goals + ' / 100';
            return;
        }
        bar.style.width = current + '%';
        text.textContent = Math.round(current) + '%';
        valueText.textContent = Math.round((current / 100) * 100) + ' / 100';
        requestAnimationFrame(animate);
    };
    
    setTimeout(animate, 100);
}

// ============================================
// SIDEBAR NAVIGATION
// ============================================

/**
 * Initialize sidebar functionality
 */
function initializeSidebar() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    // Toggle sidebar on mobile
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('show');
    });
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 992) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        }
    });
}

/**
 * Switch between dashboard sections
 */
function switchSection(section) {
    // Hide all sections
    document.querySelectorAll('.dashboard-section').forEach(sec => {
        sec.classList.remove('active');
    });
    
    // Show selected section
    const targetSection = document.getElementById('section-' + section);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Update sidebar active state
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === section) {
            item.classList.add('active');
        }
    });
    
    // Close sidebar on mobile after selection
    if (window.innerWidth <= 992) {
        document.getElementById('sidebar').classList.remove('show');
    }
    
    // Refresh data when switching sections
    if (section === 'progress') {
        loadProgressData();
    } else if (section === 'leaderboard') {
        loadLeaderboardData();
    } else if (section === 'notifications') {
        loadNotifications();
    }
}

// ============================================
// IMAGE UPLOAD FUNCTIONALITY
// ============================================

/**
 * Initialize upload functionality
 */
function initializeUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const uploadBtn = document.getElementById('uploadBtn');
    
    // Click to browse
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function() {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFileSelect(this.files[0]);
        }
    });
    
    // Upload button click
    uploadBtn.addEventListener('click', function() {
        uploadFile();
    });
    
    /**
     * Handle file selection
     */
    function handleFileSelect(file) {
        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
        if (!validTypes.includes(file.type)) {
            showAlert('Please select a valid image file (JPG, JPEG, or PNG)', 'error');
            return;
        }
        
        // Validate file size (max 16MB for backend)
        if (file.size > 16 * 1024 * 1024) {
            showAlert('File size must be less than 16MB', 'error');
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            previewContainer.classList.add('has-image');
            uploadBtn.style.display = 'inline-block';
        };
        reader.readAsDataURL(file);
        
        // Store file for upload
        window.selectedFile = file;
    }
    
    /**
     * Upload file to backend API
     */
    async function uploadFile() {
        if (!window.selectedFile) {
            showAlert('Please select a file first', 'error');
            return;
        }
        
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        try {
            const formData = new FormData();
            formData.append('file', window.selectedFile);
            
            const token = localStorage.getItem('authToken');
            
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: formData,
                credentials: 'include'
            });
            
            const data = await response.json();
            
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Screenshot';
            
            if (data.success) {
                // Get the score - handle both possible response formats
                const score = data.data?.match_score ?? data.match_score ?? 'N/A';
                showAlert(`Screenshot uploaded! Score: ${score} points`, 'success');
                
                // Reset upload area
                setTimeout(() => {
                    resetUpload();
                    // Refresh progress data
                    loadProgressData();
                    loadLeaderboardData();
                }, 1500);
            } else {
                showAlert(data.message || 'Upload failed', 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Screenshot';
            
            // Fallback demo behavior
            showAlert('Upload simulated (demo mode)', 'success');
            setTimeout(() => {
                resetUpload();
                loadProgressData();
            }, 1500);
        }
    }
    
    /**
     * Reset upload area
     */
    function resetUpload() {
        const fileInput = document.getElementById('fileInput');
        const previewContainer = document.getElementById('previewContainer');
        const uploadBtn = document.getElementById('uploadBtn');
        
        fileInput.value = '';
        window.selectedFile = null;
        previewContainer.classList.remove('has-image');
        document.getElementById('imagePreview').src = '';
        uploadBtn.style.display = 'none';
    }
}

// ============================================
// LOGOUT FUNCTIONALITY
// ============================================

/**
 * Initialize logout functionality
 */
function initializeLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    
    logoutBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        
        try {
            // Call logout API
            await apiRequest('/logout', 'POST');
        } catch (error) {
            console.log('Logout API error (ignoring):', error);
        } finally {
            // Clear localStorage regardless of API result
            localStorage.removeItem('authToken');
            localStorage.removeItem('user');
            
            // Redirect to landing page
            window.location.href = 'landing.html';
        }
    });
}

// ============================================
// ALERT NOTIFICATIONS
// ============================================

/**
 * Show alert notification
 */
function showAlert(message, type) {
    const alertToast = document.getElementById('alertToast');
    const alertMessage = document.getElementById('alertToastMessage');
    const alertIcon = alertToast.querySelector('.alert-toast-icon');
    
    // Set message and type
    alertMessage.textContent = message;
    alertToast.className = 'alert-toast ' + type;
    alertIcon.className = 'fas fa-' + (type === 'success' ? 'check-circle' : 'exclamation-circle') + ' alert-toast-icon';
    
    // Show alert
    alertToast.classList.add('show');
    
    // Hide after 3 seconds
    setTimeout(() => {
        alertToast.classList.remove('show');
    }, 3000);
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Format number with commas
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Export functions for use in HTML
window.switchSection = switchSection;
window.showAlert = showAlert;


