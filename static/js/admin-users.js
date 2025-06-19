// User Management Functions
function viewUser(userId) {
    fetch(`/admin/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            if (user.error) {
                showError(user.error);
                return;
            }
            
            const details = document.getElementById('userDetails');
            details.innerHTML = `
                <dl class="row">
                    <dt class="col-sm-3">Email</dt>
                    <dd class="col-sm-9">${user.email}</dd>
                    
                    <dt class="col-sm-3">Name</dt>
                    <dd class="col-sm-9">${user.first_name || ''} ${user.last_name || ''}</dd>
                    
                    <dt class="col-sm-3">Subscription</dt>
                    <dd class="col-sm-9">
                        <span class="badge bg-${user.subscription_plan === 'free' ? 'secondary' : 'primary'}">
                            ${user.subscription_plan}
                        </span>
                        (${user.subscription_status})
                    </dd>
                    
                    <dt class="col-sm-3">Status</dt>
                    <dd class="col-sm-9">
                        <span class="badge bg-${user.is_active ? 'success' : 'danger'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </dd>
                    
                    <dt class="col-sm-3">Created</dt>
                    <dd class="col-sm-9">${new Date(user.created_at).toLocaleString()}</dd>
                    
                    <dt class="col-sm-3">Last Login</dt>
                    <dd class="col-sm-9">${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</dd>
                </dl>
            `;
            
            const viewModal = new bootstrap.Modal(document.getElementById('viewUserModal'));
            viewModal.show();
        })
        .catch(error => showError('Failed to load user details'));
}

function editUser(userId) {
    fetch(`/admin/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            if (user.error) {
                showError(user.error);
                return;
            }
            
            // Populate form fields
            document.getElementById('editUserId').value = user.id;
            document.getElementById('editUserEmail').value = user.email;
            document.getElementById('editUserFirstName').value = user.first_name || '';
            document.getElementById('editUserLastName').value = user.last_name || '';
            document.getElementById('editUserPlan').value = user.subscription_plan;
            document.getElementById('editUserActive').checked = user.is_active;
            
            const editModal = new bootstrap.Modal(document.getElementById('editUserModal'));
            editModal.show();
        })
        .catch(error => showError('Failed to load user details'));
}

function saveUser() {
    const userId = document.getElementById('editUserId').value;
    const data = {
        email: document.getElementById('editUserEmail').value,
        first_name: document.getElementById('editUserFirstName').value,
        last_name: document.getElementById('editUserLastName').value,
        subscription_plan: document.getElementById('editUserPlan').value,
        is_active: document.getElementById('editUserActive').checked
    };
    
    fetch(`/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.error) {
            showError(result.error);
            return;
        }
        
        // Close modal and refresh page
        const editModal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
        editModal.hide();
        window.location.reload();
    })
    .catch(error => showError('Failed to update user'));
}

function deleteUser(userId) {
    document.getElementById('deleteUserId').value = userId;
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteUserModal'));
    deleteModal.show();
}

function confirmDelete() {
    const userId = document.getElementById('deleteUserId').value;
    
    fetch(`/admin/users/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(result => {
        if (result.error) {
            showError(result.error);
            return;
        }
        
        // Close modal and refresh page
        const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
        deleteModal.hide();
        window.location.reload();
    })
    .catch(error => showError('Failed to delete user'));
}

function searchUsers() {
    const query = document.getElementById('userSearch').value.trim();
    if (!query) {
        showError('Please enter a search term');
        return;
    }
    
    window.location.href = `/admin/users/search?q=${encodeURIComponent(query)}`;
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
        alert.close();
    }, 5000);
} 