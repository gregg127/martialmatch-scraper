document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('tournamentForm');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const error = document.getElementById('error');
    const scheduleContainer = document.getElementById('scheduleContainer');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const url = document.getElementById('tournamentUrl').value;

        // Show loading, hide other containers
        loading.style.display = 'block';
        results.style.display = 'none';
        error.style.display = 'none';

        try {
            const response = await fetch(`/api/bjj-participants?url=${encodeURIComponent(url)}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred');
            }

            // Display schedule grouped by day
            let scheduleHtml = '';

            if (Object.keys(data.schedule).length === 0) {
                scheduleHtml = '<div class="error">No schedule data available for this tournament.</div>';
            } else {
                for (const [day, scheduleItems] of Object.entries(data.schedule)) {
                    if (!scheduleItems || scheduleItems.length === 0) continue;

                    scheduleHtml += `
                        <h3>${day}</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Category</th>
                                    <th>Mat</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${scheduleItems.map(item => {
                        const timeStr = item["Szacowany czas"] || '';
                        const startTime = timeStr.split(' - ')[0];
                        const [hours, minutes] = startTime.split(':').map(Number);

                        const now = new Date();
                        const eventTime = new Date();
                        eventTime.setHours(hours, minutes, 0);

                        const isPast = now > eventTime;

                        return `
                                    <tr class="${isPast ? 'past-event' : ''}">
                                        <td>${escapeHtml(item["Imię i nazwisko"] || '-')}</td>
                                        <td>${escapeHtml(item.Kategoria || '-')}</td>
                                        <td>${escapeHtml(item.Mata || '-')}</td>
                                        <td>${escapeHtml(timeStr || '-')}</td>
                                    </tr>
                                    `;
                    }).join('')}
                            </tbody>
                        </table>
                    `;
                }
            }
            scheduleContainer.innerHTML = scheduleHtml;

            // Show results
            results.style.display = 'block';
            loading.style.display = 'none';

        } catch (err) {
            error.textContent = err.message;
            error.style.display = 'block';
            loading.style.display = 'none';
        }
    });

    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '-';
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
