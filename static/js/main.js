// Main JavaScript file for OpenManus Executive Assistant

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup form validation
    setupFormValidation();
    
    // Setup dashboard actions if on dashboard page
    if (document.querySelector('.list-group-item-action[data-bs-toggle="list"]')) {
        setupDashboardActions();
    }
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

/**
 * Setup form validation for login and registration forms
 */
function setupFormValidation() {
    // Get all forms with the 'needs-validation' class
    var forms = document.querySelectorAll('.needs-validation');
    
    // Loop over forms and prevent submission if fields are invalid
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password confirmation validation
    var password = document.getElementById('register-password');
    var confirmPassword = document.getElementById('register-confirm-password');
    
    if (password && confirmPassword) {
        function validatePassword() {
            if (password.value != confirmPassword.value) {
                confirmPassword.setCustomValidity("Passwords don't match");
            } else {
                confirmPassword.setCustomValidity('');
            }
        }
        
        password.addEventListener('change', validatePassword);
        confirmPassword.addEventListener('keyup', validatePassword);
    }
}

/**
 * Setup event listeners for dashboard actions
 */
function setupDashboardActions() {
    // Handle tab navigation
    var tabs = document.querySelectorAll('.list-group-item-action[data-bs-toggle="list"]');
    tabs.forEach(function(tab) {
        tab.addEventListener('click', function(event) {
            tabs.forEach(function(t) {
                t.classList.remove('active');
            });
            event.target.classList.add('active');
        });
    });
    
    // Handle service connection buttons
    var connectButtons = document.querySelectorAll('.btn[data-connect]');
    connectButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            var service = event.target.getAttribute('data-connect');
            showAlert(`Connecting to ${service}...`, 'info');
        });
    });
}

/**
 * Display an alert message
 * @param {string} message - The message to display
 * @param {string} type - The type of alert (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    var alertContainer = document.querySelector('.container.mt-3');
    if (!alertContainer) return;
    
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertContainer.innerHTML += alertHtml;
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        var newAlert = alertContainer.querySelector('.alert:last-child');
        if (newAlert) {
            var bsAlert = new bootstrap.Alert(newAlert);
            bsAlert.close();
        }
    }, 5000);
}