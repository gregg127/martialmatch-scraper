document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const elements = {
        form: document.getElementById('tournamentForm'),
        loading: document.getElementById('loading'),
        results: document.getElementById('results'),
        error: document.getElementById('error'),
        scheduleContainer: document.getElementById('scheduleContainer'),
        tournamentSelect: document.getElementById('tournamentUrl'),
        tournamentTypeRadios: document.getElementsByName('tournamentType')
    };

    // Store tournament data
    let tournamentData = { active: [], archived: [] };

    // Initialize tournaments dropdown
    async function initializeTournaments() {
        elements.tournamentSelect.disabled = true;
        elements.tournamentSelect.innerHTML = '<option value="">Loading tournaments...</option>';

        try {
            const response = await fetch('/api/tournaments');
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to fetch tournaments');
            }

            tournamentData = data.tournaments;
            updateTournamentList(false); // Show active tournaments by default
            
            // Add radio buttons event listeners
            elements.tournamentTypeRadios.forEach(radio => {
                radio.addEventListener('change', (e) => {
                    updateTournamentList(e.target.value === 'archived');
                });
            });

        } catch (err) {
            elements.tournamentSelect.innerHTML = '<option value="">Error loading tournaments</option>';
            console.error('Error fetching tournaments:', err);
        } finally {
            elements.tournamentSelect.disabled = false;
        }
    }

    function updateTournamentList(showArchived) {
        let tournaments = showArchived ? tournamentData.archived : tournamentData.active;
        if (!showArchived) {
            tournaments = tournaments.slice(0, 5);
        }
        elements.tournamentSelect.innerHTML = tournaments.length 
            ? tournaments.map(tournament => 
                `<option value="${tournament.id}">${tournament.name}</option>`
              ).join('')
            : '<option value="">No tournaments available</option>';
    }

    // Form submit handler
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        elements.loading.style.display = 'block';
        elements.results.style.display = 'none';
        elements.error.style.display = 'none';

        try {
            const eventId = elements.tournamentSelect.value;
            const response = await fetch(`/api/bjj-participants/${eventId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred');
            }

            // Display schedule
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
                                    <th data-column="name">Name</th>
                                    <th data-column="category" class="category-header">Category</th>
                                    <th data-column="mat">Mat</th>
                                    <th data-column="time">Time</th>
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

                                    return `
                                        <tr class="${now > eventTime ? 'past-event' : ''}">
                                            <td data-column="name">${escapeHtml(item["Imię i nazwisko"] || '-')}</td>
                                            <td data-column="category" class="category-cell">${escapeHtml(item.Kategoria || '-')}</td>
                                            <td data-column="mat">${escapeHtml(item.Mata || '-')}</td>
                                            <td data-column="time">${escapeHtml(timeStr || '-')}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    `;
                }
            }
            elements.scheduleContainer.innerHTML = scheduleHtml;
            elements.results.style.display = 'block';
            elements.loading.style.display = 'none';

        } catch (err) {
            elements.error.textContent = err.message;
            elements.error.style.display = 'block';
            elements.loading.style.display = 'none';
        }
    }

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

    // Initialize tournaments on page load
    initializeTournaments();

    // Event listeners
    elements.form.addEventListener('submit', handleFormSubmit);
});
