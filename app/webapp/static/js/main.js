document.addEventListener("DOMContentLoaded", function () {
  const MAX_ACTIVE_TOURNAMENTS = 10;

  const elements = {
    form: document.getElementById("tournamentForm"),
    loading: document.getElementById("loading"),
    results: document.getElementById("results"),
    error: document.getElementById("error"),
    scheduleContainer: document.getElementById("scheduleContainer"),
    tournamentSelect: document.getElementById("tournamentSelect"),
    clubSelect: document.getElementById("clubSelect"),
    tournamentTypeRadios: document.getElementsByName("tournamentType"),
  };

  let tournamentData = { active: [], archived: [] };
  let serverTimestamp = null;

  function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return "-";
    return unsafe
      .toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function buildRowHtml(item) {
    const isPast =
      serverTimestamp && item.end_timestamp && serverTimestamp > item.end_timestamp;
    return `
      <tr class="${isPast ? "time-past" : ""}">
        <td data-column="name">${escapeHtml(item.name)}</td>
        <td data-column="category" class="category-cell">${escapeHtml(item.category)}</td>
        <td data-column="mat">${escapeHtml(item.mat)}</td>
        <td data-column="time">${escapeHtml(item.time)}</td>
      </tr>`;
  }

  function buildDayHtml(day, items) {
    return `
      <h3 class="collapsible-header collapsed">${day} <span class="collapse-indicator">&#8645;</span></h3>
      <div class="collapsible-content" style="display: none;">
        <table>
          <thead>
            <tr>
              <th data-column="name">Imię i nazwisko</th>
              <th data-column="category" class="category-header">Kategoria</th>
              <th data-column="mat">Mata</th>
              <th data-column="time">Czas</th>
            </tr>
          </thead>
          <tbody>${items.map(buildRowHtml).join("")}</tbody>
        </table>
      </div>`;
  }

  async function initializeTournaments() {
    elements.tournamentSelect.disabled = true;
    elements.tournamentSelect.innerHTML = '<option value="">Pobieram...</option>';

    try {
      const response = await fetch("/api/tournaments");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to fetch tournaments");
      }

      tournamentData = data.tournaments;
      updateTournamentList(false);

      elements.tournamentTypeRadios.forEach((radio) => {
        radio.addEventListener("change", (e) => {
          updateTournamentList(e.target.value === "archived");
        });
      });
    } catch (err) {
      elements.tournamentSelect.innerHTML =
        '<option value="">Błąd podczas ładowania</option>';
      console.error("Error fetching tournaments:", err);
    } finally {
      elements.tournamentSelect.disabled = false;
    }
  }

  function updateTournamentList(showArchived) {
    const tournaments = showArchived
      ? tournamentData.archived
      : tournamentData.active.slice(0, MAX_ACTIVE_TOURNAMENTS);
    elements.tournamentSelect.innerHTML = tournaments.length
      ? tournaments
          .map((t) => `<option value="${t.id}">${t.name}</option>`)
          .join("")
      : '<option value="">Brak turniejów</option>';
  }

  async function initializeClubs() {
    elements.clubSelect.disabled = true;
    elements.clubSelect.innerHTML = '<option value="">Pobieram...</option>';

    try {
      const response = await fetch("/api/clubs");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to fetch clubs");
      }

      elements.clubSelect.innerHTML = data.clubs
        .map((club) => `<option value="${club.id}">${club.display_name}</option>`)
        .join("");
    } catch (err) {
      elements.clubSelect.innerHTML =
        '<option value="">Błąd podczas ładowania</option>';
      console.error("Error fetching clubs:", err);
    } finally {
      elements.clubSelect.disabled = false;
    }
  }

  async function handleFormSubmit(e) {
    e.preventDefault();

    elements.loading.style.display = "block";
    elements.results.style.display = "none";
    elements.error.style.display = "none";

    try {
      const eventId = elements.tournamentSelect.value;
      const clubId = elements.clubSelect.value;

      const response = await fetch(
        `/api/participants?event_id=${eventId}&club_id=${clubId}`,
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "An error occurred");
      }

      if (Object.keys(data.schedule).length === 0) {
        const message = data.message || "Nie znaleziono danych.";
        elements.scheduleContainer.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
      } else {
        elements.scheduleContainer.innerHTML = Object.entries(data.schedule)
          .filter(([, items]) => items && items.length > 0)
          .map(([day, items]) => buildDayHtml(day, items))
          .join("");
      }

      addCollapsibleBehavior();
      elements.results.style.display = "block";
    } catch (err) {
      elements.error.textContent = err.message;
      elements.error.style.display = "block";
    } finally {
      elements.loading.style.display = "none";
    }
  }

  function addCollapsibleBehavior() {
    document.querySelectorAll(".collapsible-header").forEach((header) => {
      header.addEventListener("click", function () {
        const content = this.nextElementSibling;
        const isCollapsed = this.classList.contains("collapsed");
        content.style.display = isCollapsed ? "block" : "none";
        this.classList.toggle("collapsed", !isCollapsed);
        this.classList.toggle("expanded", isCollapsed);
      });
    });
  }

  async function initializeServerTime() {
    try {
      const response = await fetch("/api/server-time");
      const data = await response.json();
      if (response.ok) {
        serverTimestamp = data.timestamp;
      }
    } catch (err) {
      console.error("Error fetching server time:", err);
    }
  }

  initializeTournaments();
  initializeClubs();
  initializeServerTime();

  elements.form.addEventListener("submit", handleFormSubmit);
});
