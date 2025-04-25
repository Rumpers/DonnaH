// Main JavaScript file for OpenManus Assistant

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Setup any tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Setup any popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add form validation for login and registration
    setupFormValidation();
    
    // Add event listeners for dashboard actions
    setupDashboardActions();
});

/**
 * Setup form validation for login and registration forms
 */
function setupFormValidation() {
    // Login form validation
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Perform login validation here
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            // Simple validation example
            if (!email || !password) {
                showAlert('Please fill in all fields', 'danger');
                return;
            }
            
            // Here you would typically send the login request to the server
            // For demonstration, we're just showing a success message
            showAlert('Login successful!', 'success');
            
            // Redirect to dashboard after short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        });
    }
    
    // Registration form validation
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Perform registration validation here
            const username = document.getElementById('register-username').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const confirmPassword = document.getElementById('register-confirm-password').value;
            const termsChecked = document.getElementById('terms').checked;
            
            // Simple validation
            if (!username || !email || !password || !confirmPassword) {
                showAlert('Please fill in all fields', 'danger');
                return;
            }
            
            if (password !== confirmPassword) {
                showAlert('Passwords do not match', 'danger');
                return;
            }
            
            if (!termsChecked) {
                showAlert('You must agree to the Terms of Service', 'danger');
                return;
            }
            
            // Here you would typically send the registration request to the server
            // For demonstration, we're just showing a success message
            showAlert('Registration successful!', 'success');
            
            // Redirect to dashboard after short delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        });
    }
}

/**
 * Setup event listeners for dashboard actions
 */
function setupDashboardActions() {
    // Example: Toggle assistant status
    const startAssistantBtn = document.querySelector('.assistant-status');
    if (startAssistantBtn) {
        startAssistantBtn.addEventListener('click', function() {
            const statusIndicator = document.querySelector('.status-indicator');
            const statusText = document.querySelector('.badge');
            
            if (statusIndicator.classList.contains('offline')) {
                statusIndicator.classList.remove('offline');
                statusIndicator.classList.add('online');
                statusText.classList.remove('bg-danger');
                statusText.classList.add('bg-success');
                statusText.textContent = 'Online';
                showAlert('Assistant is now online!', 'success');
            } else {
                statusIndicator.classList.remove('online');
                statusIndicator.classList.add('offline');
                statusText.classList.remove('bg-success');
                statusText.classList.add('bg-danger');
                statusText.textContent = 'Offline';
                showAlert('Assistant is now offline', 'warning');
            }
        });
    }
}

/**
 * Display an alert message
 * @param {string} message - The message to display
 * @param {string} type - The type of alert (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.classList.add('alert', `alert-${type}`, 'alert-dismissible', 'fade', 'show');
    alertDiv.setAttribute('role', 'alert');
    
    // Add message and close button
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Find a good place to insert the alert
    const container = document.querySelector('.container') || document.querySelector('.container-fluid');
    if (container) {
        // Insert at the top of the container
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => {
                alertDiv.remove();
            }, 150);
        }, 5000);
    }
}
