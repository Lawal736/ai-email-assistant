function analyzeEmailsOnDemand() {
    const btn = document.getElementById('analyzeEmailsBtn');
    const status = document.getElementById('analyzeEmailsStatus');
    btn.disabled = true;
    status.textContent = 'Analyzing...';

    // Collect emails from the page (from a JS variable if available)
    let emails = window.dashboardEmails || [];
    if (!emails.length && window.groupedEmails) {
        // Flatten grouped emails
        emails = Object.values(window.groupedEmails).flat();
    }
    if (!emails.length) {
        status.textContent = 'No emails to analyze.';
        btn.disabled = false;
        return;
    }

    fetch('/api/analyze-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails })
    })
    .then(res => res.json())
    .then(data => {
        // Update Action Items
        const actionItemsContent = document.getElementById('actionItemsContent');
        if (data.action_items && data.action_items.length) {
            actionItemsContent.innerHTML = data.action_items.map(item => `
                <div class="action-item">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-1">${item.subject}</h6>
                        <span class="badge priority-${item.priority}">${item.priority.charAt(0).toUpperCase() + item.priority.slice(1)}</span>
                    </div>
                    <p class="text-muted small mb-2">From: ${item.email_sender}</p>
                    <div class="action-content">${item.action_items}</div>
                </div>
            `).join('');
        } else {
            actionItemsContent.innerHTML = `<p class="text-muted text-center py-3"><i class="fas fa-check-circle fa-2x mb-2"></i><br>No action items found!</p>`;
        }
        // Update Recommendations
        const recommendationsContent = document.getElementById('recommendationsContent');
        if (data.recommendations && data.recommendations.length) {
            recommendationsContent.innerHTML = data.recommendations.map(rec => `
                <div class="recommendation">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-1">${rec.subject}</h6>
                        <span class="badge priority-${rec.priority}">${rec.priority.charAt(0).toUpperCase() + rec.priority.slice(1)}</span>
                    </div>
                    <p class="text-muted small mb-2">From: ${rec.email_sender}</p>
                    <div class="recommendation-content">${rec.recommendations}</div>
                    <button class="btn btn-sm btn-primary mt-2" onclick="generateResponse('${rec.email_id}')">
                        <i class="fas fa-magic me-1"></i>Generate Response
                    </button>
                </div>
            `).join('');
        } else {
            recommendationsContent.innerHTML = `<p class="text-muted text-center py-3"><i class="fas fa-comments fa-2x mb-2"></i><br>No recommendations found!</p>`;
        }
        status.textContent = 'Analysis complete!';
        btn.disabled = false;
    })
    .catch(err => {
        status.textContent = 'Error analyzing emails.';
        btn.disabled = false;
    });
} 