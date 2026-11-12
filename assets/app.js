const api = async (path, options = {}) => {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Request gagal (${response.status}).`);
  return result;
};

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));

const notify = (message, isError = false) => {
  let node = document.querySelector(".app-notice");
  if (!node) {
    node = document.createElement("div");
    node.className = "app-notice";
    node.setAttribute("role", "status");
    document.body.append(node);
  }
  node.textContent = message;
  node.classList.toggle("error", isError);
  node.hidden = false;
  window.clearTimeout(node.timeoutId);
  node.timeoutId = window.setTimeout(() => { node.hidden = true; }, 5000);
};

const songCard = (song) => `
  <a class="song-card" href="detail.html?id=${encodeURIComponent(song.id)}">
    <div class="cover-art ${escapeHtml(song.cover_class)}"><span>♫</span><small>${escapeHtml(song.game)}</small></div>
    <div class="song-card-body"><h3>${escapeHtml(song.title)}</h3>
      <p class="muted">${escapeHtml(song.game)} · ${escapeHtml(song.bpm)} BPM</p>
      <div class="tag-row"><span class="tag">${escapeHtml(song.difficulty)}</span><span class="tag">${song.rating ? `★ ${escapeHtml(song.rating)}` : `${escapeHtml(song.review_count)} ULASAN`}</span></div>
    </div>
  </a>`;

const mountAuth = () => {
  document.querySelectorAll("form[data-auth]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('[type="submit"]');
      button.disabled = true;
      try {
        const role = form.dataset.auth;
        const endpoint = role === "admin" ? "/api/admin/login" : "/api/auth/login";
        const result = await api(endpoint, {
          method: "POST",
          body: JSON.stringify({
            email: form.elements.email.value,
            password: form.elements.password.value,
            role,
          }),
        });
        window.location.href = result.user.role === "admin" ? "/admin/dashboard.html" : "/user/index.html";
      } catch (error) {
        notify(error.message, true);
      } finally {
        button.disabled = false;
      }
    });
  });

  const register = document.querySelector("#register-form");
  register?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(register);
    if (formData.get("password") !== formData.get("confirm_password")) {
      notify("Konfirmasi kata sandi tidak cocok.", true);
      return;
    }
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: formData.get("email"),
          name: formData.get("name"),
          password: formData.get("password"),
        }),
      });
      window.location.href = "/user/index.html";
    } catch (error) {
      notify(error.message, true);
    }
  });
};

const mountSession = async () => {
  const user = (await api("/api/me")).user;
  document.querySelectorAll(".site-header .avatar").forEach((avatar) => {
    if (!user) return;
    avatar.textContent = user.name.slice(0, 1).toUpperCase();
    avatar.href = user.role === "admin" ? "/admin/dashboard.html" : "#account-menu";
    avatar.title = `${user.name} · ${user.role}`;
    if (user.role === "user") {
      avatar.addEventListener("click", async (event) => {
        event.preventDefault();
        try {
          await api("/api/auth/logout", { method: "POST", body: "{}" });
          window.location.reload();
        } catch (error) {
          notify(error.message, true);
        }
      });
    }
  });
  return user;
};

const mountCatalog = async () => {
  const grid = document.querySelector(".catalog-grid");
  if (!grid) return;
  const form = document.querySelector(".catalog-tools .search-bar");
  const search = form?.querySelector('input[type="search"]');
  const filters = document.querySelectorAll(".catalog-tools .select-chip");
  const params = new URLSearchParams(window.location.search);
  if (search) search.value = params.get("q") || "";
  const games = (await api("/api/games")).games.filter((game) => game.active);
  if (filters[0]) {
    filters[0].innerHTML = `<span>All games</span><span>⌄</span>`;
    filters[0].classList.add("filter-game");
    filters[0].setAttribute("role", "button");
    filters[0].tabIndex = 0;
  }
  if (filters[1]) {
    filters[1].innerHTML = `<span>All levels</span><span>⌄</span>`;
    filters[1].classList.add("filter-difficulty");
    filters[1].setAttribute("role", "button");
    filters[1].tabIndex = 0;
  }
  if (filters[2]) {
    filters[2].innerHTML = `<span>BPM: all</span><span>⌄</span>`;
    filters[2].classList.add("filter-bpm");
    filters[2].setAttribute("role", "button");
    filters[2].tabIndex = 0;
  }
  const gameSelect = document.createElement("select");
  gameSelect.className = "catalog-filter-select";
  gameSelect.setAttribute("aria-label", "Filter game");
  gameSelect.innerHTML = `<option value="">All games</option>${games.map((game) => `<option value="${game.id}">${escapeHtml(game.name)}</option>`).join("")}`;
  const difficultySelect = document.createElement("select");
  difficultySelect.className = "catalog-filter-select";
  difficultySelect.setAttribute("aria-label", "Filter difficulty");
  difficultySelect.innerHTML = '<option value="">All levels</option><option>Normal</option><option>Veteran</option><option>Hard</option><option>Challenge</option>';
  const minBpm = document.createElement("input");
  minBpm.className = "catalog-filter-input";
  minBpm.type = "number";
  minBpm.min = "1";
  minBpm.max = "999";
  minBpm.placeholder = "Min BPM";
  minBpm.setAttribute("aria-label", "Minimum BPM");
  const maxBpm = document.createElement("input");
  maxBpm.className = "catalog-filter-input";
  maxBpm.type = "number";
  maxBpm.min = "1";
  maxBpm.max = "999";
  maxBpm.placeholder = "Max BPM";
  maxBpm.setAttribute("aria-label", "Maximum BPM");
  document.querySelector(".catalog-tools .filter-row")?.append(gameSelect, difficultySelect, minBpm, maxBpm);
  const loadSongs = async () => {
    const query = new URLSearchParams();
    if (search?.value.trim()) query.set("q", search.value.trim());
    if (gameSelect.value) query.set("game", gameSelect.value);
    if (difficultySelect.value) query.set("difficulty", difficultySelect.value);
    if (minBpm.value) query.set("bpmMin", minBpm.value);
    if (maxBpm.value) query.set("bpmMax", maxBpm.value);
    try {
      const { songs } = await api(`/api/songs?${query}`);
      grid.innerHTML = songs.length ? songs.map(songCard).join("") : '<p class="empty-state">Belum ada lagu yang sesuai filter.</p>';
      history.replaceState(null, "", `${location.pathname}${query.size ? `?${query}` : ""}`);
      const count = document.querySelector(".count-pill");
      if (count) count.textContent = `${songs.length} LAGU`;
    } catch (error) {
      notify(error.message, true);
    }
  };
  form?.addEventListener("submit", (event) => { event.preventDefault(); loadSongs(); });
  [gameSelect, difficultySelect, minBpm, maxBpm].forEach((control) => control.addEventListener("change", loadSongs));
  await loadSongs();
};

const mountHome = async () => {
  const grid = document.querySelector(".home-hero")?.nextElementSibling?.querySelector(".song-grid");
  if (!grid) return;
  const { songs } = await api("/api/songs");
  grid.innerHTML = songs.slice(0, 4).map(songCard).join("");
};

const mountSongDetail = async (user) => {
  if (!document.querySelector(".detail-shell")) return;
  const id = Number(new URLSearchParams(location.search).get("id")) || 1;
  const detail = await api(`/api/songs/${id}`);
  const song = detail;
  document.title = `${song.title} — RhythmShowcase`;
  const breadcrumbLabels = Array.from(document.querySelectorAll(".breadcrumb > span"))
    .filter((node) => node.textContent !== "›");
  if (breadcrumbLabels.length >= 2) {
    breadcrumbLabels[0].textContent = song.game;
    breadcrumbLabels[1].textContent = song.title;
  }
  document.querySelector(".detail-title h1").textContent = song.title;
  document.querySelector(".detail-title > .muted").textContent = song.artist;
  document.querySelector(".detail-title > .tag").textContent = song.game;
  document.querySelector(".detail-cover").textContent = "♫";
  document.querySelector(".detail-cover").className = `detail-cover ${song.cover_class}`;
  document.querySelectorAll(".song-detail-head .tag-row .tag").forEach((badge, index) => {
    badge.textContent = [
      song.difficulty,
      `BPM ${song.bpm}`,
      song.rating ? `★ ${song.rating} (${song.review_count})` : `${song.review_count} ulasan`,
    ][index];
  });
  const facts = document.querySelectorAll(".song-facts dd");
  [song.game, song.duration, song.bpm, song.difficulty, song.review_count].forEach((value, index) => {
    if (facts[index]) facts[index].textContent = value;
  });
  const guideValues = document.querySelectorAll(".guide-grid strong");
  [song.difficulty, song.bpm].forEach((value, index) => {
    if (guideValues[index]) guideValues[index].textContent = value;
  });
  document.querySelector(".detail-section p").textContent = song.description || `Review dan panduan untuk ${song.title}.`;
  const adminReview = song.review;
  const narrative = document.querySelectorAll(".detail-section p")[1];
  if (narrative) narrative.textContent = adminReview?.body || "Belum ada review editorial untuk lagu ini.";
  const lists = document.querySelectorAll(".pros-cons ul");
  [adminReview?.pros || [], adminReview?.cons || []].forEach((items, index) => {
    if (lists[index]) {
      lists[index].innerHTML = items.length
        ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
        : "<li>Belum ada catatan.</li>";
    }
  });
  const video = document.querySelector(".video-placeholder");
  if (video) {
    video.hidden = !adminReview?.video_url;
    if (adminReview?.video_url) {
      video.href = adminReview.video_url;
      video.target = "_blank";
      video.rel = "noopener noreferrer";
    }
  }
  const community = document.querySelector("#ulasan");
  const reviewForm = document.querySelector("#user-review-form");
  const communityHeading = community?.querySelector("h2");
  if (communityHeading) communityHeading.textContent = `Ulasan Komunitas (${song.community_reviews.length})`;
  community?.querySelectorAll(".mini-review").forEach((item) => item.remove());
  song.community_reviews.forEach((review) => {
    const item = document.createElement("div");
    item.className = "mini-review";
    item.innerHTML = `<span class="avatar small">${escapeHtml(review.author.slice(0, 1).toUpperCase())}</span><div><strong>${escapeHtml(review.author)} · ★ ${review.rating}</strong><p>${escapeHtml(review.content)}</p><time>${escapeHtml(review.created_at)}</time></div>`;
    community?.insertBefore(item, reviewForm);
  });
  if (reviewForm) {
    if (!user || user.role !== "user") {
      reviewForm.innerHTML = '<p class="muted">Masuk sebagai pengguna untuk menulis ulasan.</p><a class="button button-primary full-button" href="login.html">Masuk untuk Mengulas</a>';
    } else {
      reviewForm.elements.song_id.value = song.id;
      reviewForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(reviewForm));
        try {
          await api("/api/reviews", { method: "POST", body: JSON.stringify(data) });
          notify("Ulasan berhasil dikirim.");
          window.location.reload();
        } catch (error) {
          notify(error.message, true);
        }
      });
    }
  }
};

const mountDashboard = async () => {
  if (!document.querySelector(".admin-list-section")) return;
  const user = (await api("/api/me")).user;
  if (user?.role !== "admin") {
    window.location.href = "/admin/login.html";
    return;
  }
  const [stats, result] = await Promise.all([api("/api/dashboard"), api("/api/admin/reviews")]);
  document.querySelectorAll(".stat-card strong").forEach((node, index) => {
    node.textContent = [stats.total_reviews, stats.published, stats.draft, stats.games][index];
  });
  const tbody = document.querySelector(".admin-table tbody");
  tbody.innerHTML = result.reviews.length ? result.reviews.map((review) => `
    <tr><td><span class="table-title"><span class="table-icon">♫</span><span><strong>${escapeHtml(review.title)}</strong><small>${escapeHtml(review.author)}</small></span></span></td>
    <td>${escapeHtml(review.game)}</td><td>${escapeHtml(review.updated_at)}</td>
    <td><span class="status ${review.status}">${escapeHtml(review.status)}</span></td>
    <td><a class="table-action" href="review.html?id=${review.id}" aria-label="Edit review">✎</a><a class="delete-action" href="confirm-delete.html?id=${review.id}">Hapus</a></td></tr>`).join("") : '<tr><td colspan="5" class="empty-state">Belum ada review. Buat review pertama.</td></tr>';
};

const mountAdminReviewForm = async () => {
  const form = document.querySelector("#admin-review-form");
  if (!form) return;
  const user = (await api("/api/me")).user;
  if (user?.role !== "admin") {
    window.location.href = "/admin/login.html";
    return;
  }
  const { songs } = await api("/api/songs");
  const songSelect = form.elements.song_id;
  songSelect.innerHTML = songs.map((song) => `<option value="${song.id}">${escapeHtml(song.title)} — ${escapeHtml(song.game)}</option>`).join("");
  const reviewId = new URLSearchParams(location.search).get("id");
  if (reviewId) {
    const review = await api(`/api/admin/reviews/${encodeURIComponent(reviewId)}`);
    for (const key of ["song_id", "title", "body", "status", "video_url"]) {
      if (form.elements[key]) form.elements[key].value = review[key];
    }
    form.elements.pros.value = review.pros.join("\n");
    form.elements.cons.value = review.cons.join("\n");
    document.querySelector(".admin-heading h1").textContent = "Edit Review";
  }
  document.querySelectorAll("[data-review-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!form.reportValidity()) return;
      const data = readAdminReview(form, button.dataset.reviewStatus);
      try {
        const result = reviewId
          ? await api(`/api/admin/reviews/${reviewId}`, { method: "PUT", body: JSON.stringify(data) })
          : await api("/api/admin/reviews", { method: "POST", body: JSON.stringify(data) });
        if (button.dataset.reviewStatus === "published") {
          sessionStorage.setItem("rhythm-pending-publish", String(result.review.id));
          window.location.href = "confirm-publish.html?id=" + result.review.id;
        } else {
          window.location.href = "dashboard.html";
        }
      } catch (error) {
        notify(error.message, true);
      }
    });
  });
};

const readAdminReview = (form, status) => ({
  song_id: Number(form.elements.song_id.value),
  title: form.elements.title.value,
  body: form.elements.body.value,
  status,
  pros: form.elements.pros.value.split("\n").map((value) => value.trim()).filter(Boolean),
  cons: form.elements.cons.value.split("\n").map((value) => value.trim()).filter(Boolean),
  video_url: form.elements.video_url.value.trim(),
});

const mountAdminGames = async () => {
  const grid = document.querySelector(".game-admin-grid");
  if (!grid) return;
  const user = (await api("/api/me")).user;
  if (user?.role !== "admin") {
    window.location.href = "/admin/login.html";
    return;
  }
  const render = async () => {
    const { games } = await api("/api/admin/games");
    grid.innerHTML = games.map((game) => `
      <article class="game-admin-card"><span class="table-icon">♫</span><div><h2>${escapeHtml(game.name)}</h2><p class="muted">${game.song_count} lagu</p><span class="status ${game.active ? "published" : "draft"}">${game.active ? "Aktif" : "Nonaktif"}</span></div>
      <button class="button button-secondary" type="button" data-edit-game="${game.id}" data-name="${escapeHtml(game.name)}" data-active="${Boolean(game.active)}">Edit Game</button></article>`).join("");
    grid.querySelectorAll("[data-edit-game]").forEach((button) => button.addEventListener("click", () => {
      const form = document.querySelector("#game-form");
      form.elements.id.value = button.dataset.editGame;
      form.elements.name.value = button.dataset.name;
      form.elements.active.checked = button.dataset.active === "true";
    }));
  };
  await render();
  document.querySelector("#game-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const id = form.elements.id.value;
    try {
      await api(id ? `/api/admin/games/${id}` : "/api/admin/games", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify({ name: form.elements.name.value, active: form.elements.active.checked }),
      });
      form.reset();
      form.elements.id.value = "";
      await render();
      notify("Game berhasil disimpan.");
    } catch (error) {
      notify(error.message, true);
    }
  });
};

const mountAdminSettings = async () => {
  const form = document.querySelector("#settings-form");
  if (!form) return;
  const user = (await api("/api/me")).user;
  if (user?.role !== "admin") {
    window.location.href = "/admin/login.html";
    return;
  }
  const settings = await api("/api/admin/settings");
  for (const key of ["confirm_publish", "notify_new_reviews", "auto_save_draft"]) {
    form.elements[key].checked = Boolean(settings[key]);
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(["confirm_publish", "notify_new_reviews", "auto_save_draft"].map((key) => [key, form.elements[key].checked]));
    try {
      await api("/api/admin/settings", { method: "POST", body: JSON.stringify(data) });
      notify("Pengaturan berhasil disimpan.");
    } catch (error) {
      notify(error.message, true);
    }
  });
};

const mountConfirmations = () => {
  document.querySelector("#confirm-publish-action")?.addEventListener("click", async (event) => {
    event.preventDefault();
    const id = new URLSearchParams(location.search).get("id") || sessionStorage.getItem("rhythm-pending-publish");
    if (!id) {
      notify("Tidak ada review yang menunggu publikasi.", true);
      return;
    }
    try {
      const review = await api(`/api/admin/reviews/${id}`);
      await api(`/api/admin/reviews/${id}`, {
        method: "PUT",
        body: JSON.stringify({ song_id: review.song_id, title: review.title, body: review.body, pros: review.pros, cons: review.cons, video_url: review.video_url, status: "published" }),
      });
      sessionStorage.removeItem("rhythm-pending-publish");
      window.location.href = "dashboard.html";
    } catch (error) {
      notify(error.message, true);
    }
  });

  document.querySelector("#confirm-delete-action")?.addEventListener("click", async (event) => {
    event.preventDefault();
    const id = new URLSearchParams(location.search).get("id");
    if (!id) {
      notify("Review yang akan dihapus tidak ditemukan.", true);
      return;
    }
    try {
      await api(`/api/admin/reviews/${id}`, { method: "DELETE" });
      window.location.href = "dashboard.html";
    } catch (error) {
      notify(error.message, true);
    }
  });

  document.querySelector(".logout-link")?.addEventListener("click", (event) => {
    event.preventDefault();
    sessionStorage.setItem("rhythm-logout-confirm", "true");
    window.location.href = event.currentTarget.href;
  });
  document.querySelector("#confirm-logout-action")?.addEventListener("click", async (event) => {
    event.preventDefault();
    try {
      await api("/api/auth/logout", { method: "POST", body: "{}" });
      window.location.href = "login.html";
    } catch (error) {
      notify(error.message, true);
    }
  });
};

document.addEventListener("DOMContentLoaded", async () => {
  mountAuth();
  mountConfirmations();
  try {
    const user = await mountSession();
    await Promise.all([
      mountHome(),
      mountCatalog(),
      mountSongDetail(user),
      mountDashboard(),
      mountAdminReviewForm(),
      mountAdminGames(),
      mountAdminSettings(),
    ]);
  } catch (error) {
    notify(error.message || "Tidak dapat menghubungi server.", true);
  }
});
