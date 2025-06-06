// CommunicationX Main JavaScript

class CommunicationX {
    constructor() {
        this.init();
        this.bindEvents();
        this.initSocket();
    }

    init() {
        // Initialize tooltips if using Bootstrap
        if (typeof bootstrap !== 'undefined') {
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        // Auto-redirect from splash screen
        if (window.location.pathname === '/' && document.querySelector('.splash-screen')) {
            setTimeout(() => {
                window.location.href = '/landing';
            }, 3000);
        }

        // Auto-focus message inputs
        const messageInput = document.querySelector('.message-input');
        if (messageInput) {
            messageInput.focus();
        }
    }

    bindEvents() {
        // Modal controls
        this.bindModalEvents();

        // Form submissions
        this.bindFormEvents();

        // Message input events
        this.bindMessageEvents();

        // Call events
        this.bindCallEvents();
    }

    bindCallEvents() {
        // Call control buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="start-call"]')) {
                const userId = e.target.dataset.userId;
                const callType = e.target.dataset.callType || 'audio';
                this.initiateCall(userId, callType);
            }
        });
    }

    bindModalEvents() {
        // Handle modal opening/closing
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-modal]')) {
                const modalId = e.target.dataset.modal;
                this.openModal(modalId);
            }

            if (e.target.matches('.modal-close')) {
                this.closeModal(e.target.closest('.modal'));
            }
        });
    }

    bindFormEvents() {
        // Handle form submissions with loading states
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.classList.contains('needs-validation')) {
                e.preventDefault();
                e.stopPropagation();

                if (form.checkValidity()) {
                    this.showLoadingState(form);
                    // Add timeout to prevent infinite loading
                    setTimeout(() => {
                        this.hideLoadingState(form);
                    }, 10000);
                    form.submit();
                }

                form.classList.add('was-validated');
            }
        });

        // Add character counters to text inputs
        document.querySelectorAll('textarea[maxlength], input[maxlength]').forEach(input => {
            this.addCharacterCounter(input);
        });
    }

    addCharacterCounter(input) {
        const maxLength = input.getAttribute('maxlength');
        if (!maxLength) return;

        const counter = document.createElement('small');
        counter.className = 'form-text text-muted character-counter';
        input.parentNode.appendChild(counter);

        const updateCounter = () => {
            const remaining = maxLength - input.value.length;
            counter.textContent = `${remaining} characters remaining`;
            counter.style.color = remaining < 50 ? '#dc3545' : '#6c757d';
        };

        input.addEventListener('input', updateCounter);
        updateCounter();
    }

    bindMessageEvents() {
        // Enter key to send message
        document.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('message-input')) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    const form = e.target.closest('form');
                    if (form && e.target.value.trim()) {
                        form.submit();
                    }
                }
            }
        });

        // Auto-resize textarea
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('message-input')) {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }
        });
    }

    initSocket() {
        if (typeof io !== 'undefined') {
            // Initialize Socket.IO with better connection handling
            this.socket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true,
                timeout: 20000,
                forceNew: false,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: 5,
                maxReconnectionAttempts: 5
            });

            this.socket.on('connect', () => {
                console.log('Connected to server');
            });

            this.socket.on('disconnect', (reason) => {
                console.log('Disconnected from server:', reason);
                if (reason === 'io server disconnect') {
                    // Server disconnected, reconnect manually
                    this.socket.connect();
                }
            });

            this.socket.on('connect_error', (error) => {
                console.log('Connection error:', error);
            });

            // Call events
            this.socket.on('incoming_call', (data) => {
                this.handleIncomingCall(data);
            });

            this.socket.on('call_ended', (data) => {
                this.handleCallEnded(data);
            });
        }
    }

    showModal(modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hideModal(modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    initiateCall(userId, callType) {
        window.location.href = `/call/${userId}/${callType}`;
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
        }
    }

    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    handleIncomingCall(data) {
        const accept = confirm(`Incoming ${data.call_type} call from ${data.caller_name}. Accept?`);
        if (accept) {
            window.location.href = `/join_call/${data.call_id}`;
        } else {
            // Decline call
            fetch(`/decline_call/${data.call_id}`, { method: 'POST' });
        }
    }

    handleCallEnded(data) {
        this.showNotification('Call ended', 'info');
        if (window.location.pathname.includes('/call/')) {
            window.location.href = '/home';
        }
    }

    // Utility functions
    formatTime(date) {
        return new Intl.DateTimeFormat('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    showLoadingState(form) {
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        }
    }

    hideLoadingState(form) {
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            const originalText = submitBtn.getAttribute('data-original-text');
            if (originalText) {
                submitBtn.innerHTML = originalText;
            }
        }
    }
}

// Initialize the application
window.addEventListener('DOMContentLoaded', () => {
    window.communicationX = new CommunicationX();
});

// Service Worker registration for PWA capabilities
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Handle online/offline status
window.addEventListener('online', () => {
    document.body.classList.remove('offline');
    window.communicationX?.showNotification('Connection restored', 'success');
});

window.addEventListener('offline', () => {
    document.body.classList.add('offline');
    window.communicationX?.showNotification('Connection lost', 'warning');
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K for quick search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('#quick-search');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Ctrl/Cmd + Enter to send message
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const messageInput = document.querySelector('.message-input:focus');
        if (messageInput) {
            const form = messageInput.closest('form');
            if (form && messageInput.value.trim()) {
                form.submit();
            }
        }
    }
});

// Modal functionality
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Enhanced modal handling
document.addEventListener('DOMContentLoaded', function() {
    // Handle modal triggers
    document.querySelectorAll('[data-modal-target]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal-target');
            openModal(modalId);
        });
    });

    // Handle modal close buttons
    document.querySelectorAll('.modal-close').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Close modal when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        });
    });

    // Form validation for server creation
    const createServerForm = document.querySelector('#createServerModal form');
    if (createServerForm) {
        createServerForm.addEventListener('submit', function(e) {
            const serverName = this.querySelector('input[name="server_name"]').value.trim();
            if (serverName.length < 3) {
                e.preventDefault();
                alert('Server name must be at least 3 characters long.');
                return false;
            }
            if (serverName.length > 100) {
                e.preventDefault();
                alert('Server name is too long. Maximum 100 characters allowed.');
                return false;
            }
        });
    }
});

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
}

// Invitation functionality
async function createInvitation(event) {
    event.preventDefault();

    const formData = new FormData(event.target);

    try {
        const response = await fetch('/create_invitation', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('invitationUrl').textContent = data.invite_url;
            document.getElementById('invitationResult').style.display = 'block';
        } else {
            alert('Error creating invitation: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error creating invitation: ' + error.message);
    }
}

function copyInvitationUrl() {
    const urlElement = document.getElementById('invitationUrl');
    const url = urlElement.textContent;

    navigator.clipboard.writeText(url).then(function() {
        // Change button text temporarily
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.backgroundColor = '#28a745';

        setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = '';
        }, 2000);
    }).catch(function(err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        alert('Invitation URL copied to clipboard!');
    });
}