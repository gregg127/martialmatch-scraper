document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const elements = {
        form: document.getElementById('tournamentForm'),
        loading: document.getElementById('loading'),
        results: document.getElementById('results'),
        error: document.getElementById('error'),
        scheduleContainer: document.getElementById('scheduleContainer'),
        urlInput: document.getElementById('tournamentUrl')
    };

    // Constants
    const DISPLAY_STATES = {
        LOADING: { loading: 'block', results: 'none', error: 'none' },
        ERROR: { loading: 'none', results: 'none', error: 'block' },
        RESULTS: { loading: 'none', results: 'block', error: 'none' }
    };

    const TABLE_COLUMNS = [
        { id: 'name', label: 'Name', key: 'Imię i nazwisko' },
        { id: 'category', label: 'Category', key: 'Kategoria', class: 'category-header' },
        { id: 'mat', label: 'Mat', key: 'Mata' },
        { id: 'time', label: 'Time', key: 'Szacowany czas' }
    ];

    // UI State Management
    function updateUIState(state) {
        Object.entries(state).forEach(([element, display]) => {
            elements[element].style.display = display;
        });
    }

    // HTML Generation
    function generateTableHeader() {
        return `
            <thead>
                <tr>
                    ${TABLE_COLUMNS.map(col => 
                        `<th data-column="${col.id}"${col.class ? ` class="${col.class}"` : ''}>${col.label}</th>`
                    ).join('')}
                </tr>
            </thead>`;
    }

    function generateTableRow(item) {
        const timeStr = item[TABLE_COLUMNS[3].key] || '';
        const startTime = timeStr.split(' - ')[0];
        const [hours, minutes] = startTime.split(':').map(Number);

        const now = new Date();
        const eventTime = new Date();
        eventTime.setHours(hours, minutes, 0);

        return `
            <tr class="${now > eventTime ? 'past-event' : ''}">
                ${TABLE_COLUMNS.map(col => 
                    `<td data-column="${col.id}"${col.class ? ` class="${col.class}"` : ''}>${escapeHtml(item[col.key] || '-')}</td>`
                ).join('')}
            </tr>`;
    }

    function generateSchedule(scheduleData) {
        if (Object.keys(scheduleData).length === 0) {
            return '<div class="error">No schedule data available for this tournament.</div>';
        }

        return Object.entries(scheduleData)
            .filter(([_, items]) => items && items.length > 0)
            .map(([day, items]) => `
                <h3>${day}</h3>
                <table>
                    ${generateTableHeader()}
                    <tbody>
                        ${items.map(generateTableRow).join('')}
                    </tbody>
                </table>
            `).join('');
    }

    // Event Handlers
    async function handleFormSubmit(e) {
        e.preventDefault();
        updateUIState(DISPLAY_STATES.LOADING);

        try {
            const response = await fetch(`/api/bjj-participants?url=${encodeURIComponent(elements.urlInput.value)}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred');
            }

            elements.scheduleContainer.innerHTML = generateSchedule(data.schedule);
            updateUIState(DISPLAY_STATES.RESULTS);
        } catch (err) {
            elements.error.textContent = err.message;
            updateUIState(DISPLAY_STATES.ERROR);
        }
    }

    // Utility Functions
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

    // Event Listeners
    elements.form.addEventListener('submit', handleFormSubmit);
});
