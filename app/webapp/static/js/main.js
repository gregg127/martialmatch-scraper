document.addEventListener("DOMContentLoaded", function () {
  const MAX_ACTIVE_TOURNAMENTS = 10;

  const elements = {
    form: document.getElementById("tournamentForm"),
    loading: document.getElementById("loading"),
    results: document.getElementById("results"),
    error: document.getElementById("error"),
    scheduleContainer: document.getElementById("scheduleContainer"),
    tournamentTrigger: document.getElementById("tournamentTrigger"),
    tournamentDisplay: document.getElementById("tournamentDisplay"),
    tournamentDropdown: document.getElementById("tournamentDropdown"),
    clubInput: document.getElementById("clubInput"),
    clubDropdown: document.getElementById("clubDropdown"),
    clubAcademy: document.getElementById("clubAcademy"),
    clubBranch: document.getElementById("clubBranch"),
    tournamentTypeRadios: document.getElementsByName("tournamentType"),
  };

  let tournamentData = { active: [], archived: [] };
  let currentTournaments = [];
  let selectedTournamentId = null;
  let serverTimestamp = null;
  let featuredClubs = [];
  let eventClubs = [];
  let eventClubsLoading = false;
  let currentFiltered = [];
  let activeIndex = -1;

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
      <h3 class="collapsible-header collapsed">${escapeHtml(day)} <span class="collapse-indicator">&#8645;</span></h3>
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

  // --- Tournament dropdown ---

  function openTournamentDropdown() {
    elements.tournamentDropdown.hidden = false;
    elements.tournamentTrigger.classList.add("combobox-open");
    highlightSelectedTournament();
  }

  function closeTournamentDropdown() {
    elements.tournamentDropdown.hidden = true;
    elements.tournamentTrigger.classList.remove("combobox-open");
  }

  function highlightSelectedTournament() {
    elements.tournamentDropdown.querySelectorAll(".combobox-item").forEach((el) => {
      const t = currentTournaments[parseInt(el.dataset.idx, 10)];
      el.classList.toggle("active", t && t.id === selectedTournamentId);
    });
    const active = elements.tournamentDropdown.querySelector(".combobox-item.active");
    if (active) active.scrollIntoView({ block: "nearest" });
  }

  function setSelectedTournament(idx) {
    const t = currentTournaments[idx];
    if (!t) return;
    selectedTournamentId = t.id;
    elements.tournamentDisplay.textContent = t.name;
    highlightSelectedTournament();
    loadEventClubs(t.id);
  }

  function updateTournamentList(showArchived) {
    currentTournaments = showArchived
      ? tournamentData.archived
      : tournamentData.active.slice(0, MAX_ACTIVE_TOURNAMENTS);

    if (!currentTournaments.length) {
      elements.tournamentDropdown.innerHTML =
        '<li class="combobox-item combobox-empty">Brak turniejów</li>';
      selectedTournamentId = null;
      elements.tournamentDisplay.textContent = "Brak turniejów";
      return;
    }

    elements.tournamentDropdown.innerHTML = currentTournaments
      .map(
        (t, i) =>
          `<li class="combobox-item" data-idx="${i}" role="option" tabindex="-1">${escapeHtml(t.name)}</li>`
      )
      .join("");

    setSelectedTournament(0);
  }

  elements.tournamentTrigger.addEventListener("click", () => {
    if (elements.tournamentDropdown.hidden) openTournamentDropdown();
    else closeTournamentDropdown();
  });

  elements.tournamentTrigger.addEventListener("blur", () => {
    setTimeout(closeTournamentDropdown, 150);
  });

  elements.tournamentTrigger.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (elements.tournamentDropdown.hidden) openTournamentDropdown();
      else closeTournamentDropdown();
    } else if (e.key === "Escape") {
      closeTournamentDropdown();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (elements.tournamentDropdown.hidden) {
        openTournamentDropdown();
        return;
      }
      const items = [
        ...elements.tournamentDropdown.querySelectorAll(".combobox-item:not(.combobox-empty)"),
      ];
      const currentIdx = items.findIndex(
        (el) => currentTournaments[parseInt(el.dataset.idx, 10)]?.id === selectedTournamentId
      );
      const next = Math.max(0, Math.min(items.length - 1, currentIdx + (e.key === "ArrowDown" ? 1 : -1)));
      setSelectedTournament(parseInt(items[next].dataset.idx, 10));
    }
  });

  elements.tournamentDropdown.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".combobox-item:not(.combobox-empty)");
    if (!item) return;
    e.preventDefault();
    setSelectedTournament(parseInt(item.dataset.idx, 10));
    closeTournamentDropdown();
  });

  async function initializeTournaments() {
    elements.tournamentTrigger.disabled = true;
    elements.tournamentDisplay.textContent = "Pobieram...";

    try {
      const response = await fetch("/api/tournaments");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to fetch tournaments");

      tournamentData = data.tournaments;
      updateTournamentList(false);

      elements.tournamentTypeRadios.forEach((radio) => {
        radio.addEventListener("change", (e) => {
          updateTournamentList(e.target.value === "archived");
        });
      });
    } catch (err) {
      elements.tournamentDisplay.textContent = "Błąd podczas ładowania";
      console.error("Error fetching tournaments:", err);
    } finally {
      elements.tournamentTrigger.disabled = false;
    }
  }

  // --- Club combobox ---

  function isFeatured(club) {
    return featuredClubs.some(
      (f) => f.academy === club.academy && f.branch === club.branch
    );
  }

  function buildDropdownItems(query) {
    const lower = query.toLowerCase();
    const matches = (c) => !query || c.display_name.toLowerCase().includes(lower);

    const filtered = featuredClubs.filter(matches);
    const nonFeatured = eventClubs.filter((c) => !isFeatured(c) && matches(c));

    currentFiltered = [...filtered, ...nonFeatured];
    return { featured: filtered, nonFeatured };
  }

  function renderDropdown(query) {
    activeIndex = -1;
    const { featured, nonFeatured } = buildDropdownItems(query);

    if (!currentFiltered.length && !eventClubsLoading) {
      elements.clubDropdown.hidden = true;
      elements.clubInput.classList.remove("combobox-open");
      return;
    }

    let html = featured
      .map(
        (c, i) =>
          `<li class="combobox-item" data-idx="${i}" role="option" tabindex="-1">` +
          `<span class="featured-badge" aria-hidden="true">★</span>${escapeHtml(c.display_name)}` +
          `</li>`
      )
      .join("");

    if (featured.length && nonFeatured.length) {
      html += `<li class="combobox-separator" role="separator"></li>`;
    }

    html += nonFeatured
      .map(
        (c, i) =>
          `<li class="combobox-item" data-idx="${featured.length + i}" role="option" tabindex="-1">` +
          escapeHtml(c.display_name) +
          `</li>`
      )
      .join("");

    if (eventClubsLoading) {
      html += `<li class="combobox-loading">Pobieram kluby...</li>`;
    }

    elements.clubDropdown.innerHTML = html;
    elements.clubDropdown.hidden = false;
    elements.clubInput.classList.add("combobox-open");
    updateActiveItem();
  }

  function updateActiveItem() {
    elements.clubDropdown.querySelectorAll(".combobox-item").forEach((el, i) => {
      el.classList.toggle("active", i === activeIndex);
    });
    if (activeIndex >= 0) {
      const active = elements.clubDropdown.querySelector(
        `.combobox-item[data-idx="${activeIndex}"]`
      );
      if (active) active.scrollIntoView({ block: "nearest" });
    }
  }

  function selectClub(club) {
    elements.clubInput.value = club.display_name;
    elements.clubAcademy.value = club.academy;
    elements.clubBranch.value = club.branch;
    elements.clubDropdown.hidden = true;
    elements.clubInput.classList.remove("combobox-open");
    activeIndex = -1;
  }

  function clearSelection() {
    elements.clubAcademy.value = "";
    elements.clubBranch.value = "";
  }

  function closeDropdown() {
    elements.clubDropdown.hidden = true;
    elements.clubInput.classList.remove("combobox-open");
    activeIndex = -1;
  }

  elements.clubInput.addEventListener("focus", () => {
    elements.clubInput.select();
    renderDropdown("");
  });

  elements.clubInput.addEventListener("click", () => {
    if (elements.clubDropdown.hidden) renderDropdown("");
  });

  elements.clubInput.addEventListener("input", () => {
    clearSelection();
    renderDropdown(elements.clubInput.value);
  });

  elements.clubInput.addEventListener("blur", () => {
    setTimeout(closeDropdown, 150);
  });

  elements.clubInput.addEventListener("keydown", (e) => {
    const items = elements.clubDropdown.querySelectorAll(".combobox-item");
    if (elements.clubDropdown.hidden || !items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      updateActiveItem();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, -1);
      updateActiveItem();
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      selectClub(currentFiltered[activeIndex]);
    } else if (e.key === "Escape") {
      closeDropdown();
    }
  });

  elements.clubDropdown.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".combobox-item");
    if (!item) return;
    e.preventDefault();
    selectClub(currentFiltered[parseInt(item.dataset.idx, 10)]);
  });

  async function initializeClubs() {
    elements.clubInput.disabled = true;
    elements.clubInput.placeholder = "Pobieram...";

    try {
      const response = await fetch("/api/clubs");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to fetch clubs");
      featuredClubs = data.clubs;
      elements.clubInput.placeholder = "Wpisz lub wybierz klub...";
    } catch (err) {
      elements.clubInput.placeholder = "Błąd podczas ładowania";
      console.error("Error fetching clubs:", err);
    } finally {
      elements.clubInput.disabled = false;
    }
  }

  async function loadEventClubs(eventId) {
    if (!eventId) {
      eventClubs = [];
      return;
    }
    eventClubsLoading = true;
    if (!elements.clubDropdown.hidden) renderDropdown(elements.clubInput.value);

    try {
      const response = await fetch(
        `/api/event-clubs?event_id=${encodeURIComponent(eventId)}`
      );
      const data = await response.json();
      if (eventId === selectedTournamentId) {
        eventClubs = response.ok ? data.clubs || [] : [];
      }
    } catch (err) {
      if (eventId === selectedTournamentId) eventClubs = [];
      console.error("Error fetching event clubs:", err);
    } finally {
      eventClubsLoading = false;
      if (!elements.clubDropdown.hidden) renderDropdown(elements.clubInput.value);
    }
  }

  // --- Form submit ---

  async function handleFormSubmit(e) {
    e.preventDefault();

    const eventId = selectedTournamentId;
    const academy = elements.clubAcademy.value || elements.clubInput.value.trim();
    const branch = elements.clubBranch.value;

    if (!eventId) {
      elements.error.textContent = "Wybierz zawody";
      elements.error.style.display = "block";
      return;
    }

    if (!academy) {
      elements.error.textContent = "Wpisz lub wybierz klub";
      elements.error.style.display = "block";
      return;
    }

    elements.loading.style.display = "block";
    elements.results.style.display = "none";
    elements.error.style.display = "none";

    try {
      const url =
        `/api/participants?event_id=${encodeURIComponent(eventId)}` +
        `&academy=${encodeURIComponent(academy)}` +
        `&branch=${encodeURIComponent(branch)}`;
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "An error occurred");

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
      if (response.ok) serverTimestamp = data.timestamp;
    } catch (err) {
      console.error("Error fetching server time:", err);
    }
  }

  initializeTournaments();
  initializeClubs();
  initializeServerTime();

  elements.form.addEventListener("submit", handleFormSubmit);
});
