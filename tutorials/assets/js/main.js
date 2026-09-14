// Shared behavior across every page. Plain DOM, no framework/build step —
// this site is meant to also work opened directly from disk (file://), not
// only via GitHub Pages, so nothing here depends on fetch() or a server.
//
// Every page declares two globals in a small inline <script> at the top of
// <head>, before this file loads:
//   window.DOCS_BASE  - "" for tutorials/index.html, "../" for every page
//                        one folder down (overview/…, api/…, etc).
//   window.DOCS_PAGE  - this page's href exactly as it appears in
//                        nav-data.js (e.g. "overview/features.html").
// Nav, breadcrumbs, prev/next, and search all key off those two globals
// plus the NAV_SECTIONS/NAV_FLAT/SEARCH_INDEX data loaded from
// nav-data.js / search-index.js.

document.addEventListener("DOMContentLoaded", () => {
  const BASE = typeof window.DOCS_BASE === "string" ? window.DOCS_BASE : "";
  const CURRENT = window.DOCS_PAGE || "index.html";

  const sidebar = document.querySelector(".sidebar");
  const toggle = document.querySelector(".menu-toggle");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (event) => {
      if (!sidebar.classList.contains("open")) return;
      if (sidebar.contains(event.target) || toggle.contains(event.target)) return;
      sidebar.classList.remove("open");
    });
  }

  // ---------- Data-driven, collapsible sidebar nav ----------
  const navRoot = document.getElementById("nav-root");
  if (navRoot && typeof NAV_SECTIONS !== "undefined") {
    let openState = {};
    try { openState = JSON.parse(localStorage.getItem("docs-nav-open") || "{}"); } catch (e) {}

    NAV_SECTIONS.forEach((section) => {
      const hasActive = section.pages.some((p) => p.href === CURRENT);
      const details = document.createElement("details");
      details.className = "nav-group";
      if (hasActive) details.classList.add("has-active");
      if (hasActive || openState[section.title]) details.open = true;

      const summary = document.createElement("summary");
      summary.textContent = section.title;
      details.appendChild(summary);

      const linksWrap = document.createElement("div");
      linksWrap.className = "nav-group-links";
      section.pages.forEach((page) => {
        const a = document.createElement("a");
        a.href = BASE + page.href;
        a.textContent = page.title;
        if (page.href === CURRENT) a.classList.add("active");
        linksWrap.appendChild(a);
      });
      details.appendChild(linksWrap);

      details.addEventListener("toggle", () => {
        openState[section.title] = details.open;
        try { localStorage.setItem("docs-nav-open", JSON.stringify(openState)); } catch (e) {}
      });

      navRoot.appendChild(details);
    });
  }

  // ---------- Breadcrumb ----------
  const breadcrumb = document.getElementById("breadcrumb");
  if (breadcrumb && typeof NAV_FLAT !== "undefined") {
    const entry = NAV_FLAT.find((p) => p.href === CURRENT);
    if (entry && CURRENT !== "index.html") {
      breadcrumb.innerHTML = "";
      const hub = document.createElement("a");
      hub.href = BASE + "index.html";
      hub.textContent = "Hub";
      breadcrumb.appendChild(hub);
      breadcrumb.append(" / " + entry.section + " / " + entry.title);
    }
  }

  // ---------- Prev / next footer nav ----------
  const pageNav = document.getElementById("page-nav");
  if (pageNav && typeof NAV_FLAT !== "undefined") {
    const idx = NAV_FLAT.findIndex((p) => p.href === CURRENT);
    if (idx !== -1) {
      const prev = NAV_FLAT[idx - 1];
      const next = NAV_FLAT[idx + 1];
      pageNav.innerHTML = "";
      if (prev) {
        const a = document.createElement("a");
        a.className = "prev";
        a.href = BASE + prev.href;
        a.innerHTML = '<span class="label">← Previous</span>' + prev.title;
        pageNav.appendChild(a);
      }
      if (next) {
        const a = document.createElement("a");
        a.className = "next";
        a.href = BASE + next.href;
        a.innerHTML = '<span class="label">Next →</span>' + next.title;
        pageNav.appendChild(a);
      }
    }
  }

  // ---------- Theme toggle (light / dark / system, persisted) ----------
  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    const order = ["system", "light", "dark"];
    const icons = { system: "🌓", light: "☀️", dark: "🌙" };
    let mode = "system";
    try { mode = localStorage.getItem("docs-theme") || "system"; } catch (e) {}
    const apply = (m) => {
      if (m === "light" || m === "dark") document.documentElement.setAttribute("data-theme", m);
      else document.documentElement.removeAttribute("data-theme");
      themeBtn.textContent = icons[m];
      themeBtn.setAttribute("aria-label", `Theme: ${m} (click to change)`);
    };
    apply(mode);
    themeBtn.addEventListener("click", () => {
      mode = order[(order.indexOf(mode) + 1) % order.length];
      apply(mode);
      try { localStorage.setItem("docs-theme", mode); } catch (e) {}
    });
  }

  // ---------- Ctrl+K / "/" search palette ----------
  const overlay = document.getElementById("search-overlay");
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  const searchTrigger = document.getElementById("search-trigger");
  if (overlay && searchInput && searchResults && typeof SEARCH_INDEX !== "undefined") {
    let activeIndex = -1;
    let currentResults = [];

    const renderResults = (items) => {
      currentResults = items;
      activeIndex = items.length ? 0 : -1;
      searchResults.innerHTML = "";
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "search-empty";
        empty.textContent = "No matches.";
        searchResults.appendChild(empty);
        return;
      }
      items.forEach((item, i) => {
        const a = document.createElement("a");
        a.className = "search-result" + (i === 0 ? " active" : "");
        a.href = BASE + item.url;
        a.innerHTML =
          `<span class="sr-title">${item.title}<span class="sr-section">${item.section}</span></span>` +
          `<div class="sr-summary">${item.summary || ""}</div>`;
        a.addEventListener("mouseenter", () => setActive(i));
        searchResults.appendChild(a);
      });
    };

    const setActive = (i) => {
      const links = searchResults.querySelectorAll(".search-result");
      links.forEach((el) => el.classList.remove("active"));
      if (links[i]) {
        links[i].classList.add("active");
        activeIndex = i;
      }
    };

    const search = (query) => {
      const q = query.trim().toLowerCase();
      if (!q) return renderResults([]);
      const scored = SEARCH_INDEX.map((item) => {
        const title = item.title.toLowerCase();
        const keywords = (item.keywords || []).join(" ").toLowerCase();
        const summary = (item.summary || "").toLowerCase();
        let score = -1;
        if (title.includes(q)) score = title.startsWith(q) ? 100 : 70;
        else if (keywords.includes(q)) score = 50;
        else if (summary.includes(q)) score = 20;
        else if (item.section.toLowerCase().includes(q)) score = 10;
        return { item, score };
      })
        .filter((r) => r.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 8)
        .map((r) => r.item);
      renderResults(scored);
    };

    const openPalette = () => {
      overlay.hidden = false;
      searchInput.value = "";
      renderResults([]);
      searchInput.focus();
    };
    const closePalette = () => {
      overlay.hidden = true;
    };

    if (searchTrigger) searchTrigger.addEventListener("click", openPalette);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closePalette();
    });
    searchInput.addEventListener("input", () => search(searchInput.value));
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePalette();
      else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (currentResults.length) setActive((activeIndex + 1) % currentResults.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (currentResults.length) setActive((activeIndex - 1 + currentResults.length) % currentResults.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const link = searchResults.querySelectorAll(".search-result")[activeIndex];
        if (link) link.click();
      }
    });

    document.addEventListener("keydown", (e) => {
      const tag = (document.activeElement && document.activeElement.tagName) || "";
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        openPalette();
      } else if (e.key === "/" && !typing) {
        e.preventDefault();
        openPalette();
      } else if (e.key === "Escape" && !overlay.hidden) {
        closePalette();
      }
    });
  }

  // ---------- Click-to-step diagrams ----------
  document.querySelectorAll("[data-step-diagram]").forEach((container) => {
    const total = parseInt(container.dataset.totalSteps, 10) || 1;
    let labels = [];
    try { labels = JSON.parse(container.dataset.stepLabels || "[]"); } catch (e) {}
    let active = 1;
    const svgSteps = container.querySelectorAll(".sd-step");
    const prevBtn = container.querySelector("[data-step-prev]");
    const nextBtn = container.querySelector("[data-step-next]");
    const labelEl = container.querySelector(".step-label");

    const render = () => {
      container.setAttribute("data-active-step", String(active));
      svgSteps.forEach((g) => {
        const steps = (g.getAttribute("data-step") || "")
          .split(/\s+/)
          .filter(Boolean)
          .map(Number);
        g.classList.toggle("sd-step-active", steps.includes(active));
      });
      if (prevBtn) prevBtn.disabled = active === 1;
      if (nextBtn) nextBtn.disabled = active === total;
      if (labelEl) {
        const text = labels[active - 1] || "";
        labelEl.innerHTML = `Step <strong>${active}</strong> of ${total}${text ? ": " + text : ""}`;
      }
    };
    if (prevBtn) prevBtn.addEventListener("click", () => { if (active > 1) { active -= 1; render(); } });
    if (nextBtn) nextBtn.addEventListener("click", () => { if (active < total) { active += 1; render(); } });
    render();
  });

  // Glossary filter, only present on reference/glossary.html.
  const glossarySearch = document.getElementById("glossary-search");
  const terms = document.querySelectorAll("dl.glossary > div");
  if (glossarySearch && terms.length) {
    glossarySearch.addEventListener("input", () => {
      const query = glossarySearch.value.trim().toLowerCase();
      terms.forEach((entry) => {
        const text = entry.textContent.toLowerCase();
        entry.hidden = query.length > 0 && !text.includes(query);
      });
    });
  }

  // Reading progress bar, tied to how far down the main content the
  // reader has scrolled.
  const progress = document.createElement("div");
  progress.className = "reading-progress";
  document.body.appendChild(progress);

  // Floating back-to-top button, shown once the reader has scrolled
  // a screen or so down.
  const backToTop = document.createElement("button");
  backToTop.className = "back-to-top";
  backToTop.type = "button";
  backToTop.setAttribute("aria-label", "Back to top");
  backToTop.textContent = "↑";
  backToTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.body.appendChild(backToTop);

  let ticking = false;
  const updateOnScroll = () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = docHeight > 0 ? Math.min(1, Math.max(0, scrollTop / docHeight)) : 0;
    progress.style.width = `${ratio * 100}%`;
    backToTop.classList.toggle("visible", scrollTop > 480);
    ticking = false;
  };
  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(updateOnScroll);
      ticking = true;
    }
  });
  updateOnScroll();

  // Scroll-reveal: fade/slide content into view as it enters the
  // viewport. Skipped entirely for readers who've asked for reduced
  // motion.
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
  if (!prefersReducedMotion && "IntersectionObserver" in window) {
    const revealTargets = document.querySelectorAll(
      "main.content > h2, main.content > .card-grid > .card, .box, details.accordion, main.content > table, main.content > pre, .note, .warn, .ok, .diagram"
    );
    revealTargets.forEach((el, i) => {
      el.classList.add("reveal");
      el.style.transitionDelay = `${(i % 6) * 0.05}s`;
    });
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -10% 0px" }
    );
    revealTargets.forEach((el) => observer.observe(el));
  }

  // Cursor-spotlight glow on cards: only wired up on devices that
  // actually have a hover-capable pointer, so it's a no-op on touch.
  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.querySelectorAll(".card").forEach((card) => {
      card.addEventListener("mousemove", (event) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
        card.style.setProperty("--my", `${event.clientY - rect.top}px`);
      });
    });
  }

  // Copy-to-clipboard button injected into every code block.
  document.querySelectorAll("pre").forEach((block) => {
    const code = block.textContent.replace(/^\s*\n/, "");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-btn";
    button.textContent = "Copy";
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code);
        button.textContent = "Copied";
        button.classList.add("copied");
      } catch (err) {
        button.textContent = "Failed";
      }
      setTimeout(() => {
        button.textContent = "Copy";
        button.classList.remove("copied");
      }, 1600);
    });
    block.appendChild(button);
  });
});
