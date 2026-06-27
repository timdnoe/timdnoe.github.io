/* ============================================================
   Terebinth Translation reader — /tb/reader.js
   Loads the static snapshot in /tb/data/ (committed by sync_tb.py) and
   renders parallel Greek / TB verses with hover/tap word morphology.
   No build step, no runtime API dependency, same-origin fetches only.
   ============================================================ */
(function () {
  "use strict";

  var DATA = "data/";
  var manifest = null;
  var bookById = {};

  var els = {
    intro: document.getElementById("tb-intro"),
    reader: document.getElementById("tb-reader"),
    status: document.getElementById("tb-status"),
    introMeta: document.getElementById("intro-meta"),
    bookGrid: document.getElementById("book-grid"),
    bookSelect: document.getElementById("book-select"),
    chapterSelect: document.getElementById("chapter-select"),
    verses: document.getElementById("verses"),
    readerTitle: document.getElementById("reader-title"),
    readerGreek: document.getElementById("reader-greek-title"),
    prev: document.getElementById("prev-chapter"),
    next: document.getElementById("next-chapter"),
    toggleGreek: document.getElementById("toggle-greek"),
    toggleMorph: document.getElementById("toggle-morph"),
    morph: document.getElementById("morph-pop"),
    year: document.getElementById("year"),
    footerDate: document.getElementById("footer-date"),
  };

  // ----------------------------- helpers -----------------------------
  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true; }

  function status(msg) {
    if (!msg) { hide(els.status); return; }
    els.status.textContent = msg;
    show(els.status);
  }

  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  // hash form: #book/chapter  e.g. #nt-john/1
  function parseHash() {
    var h = (location.hash || "").replace(/^#\/?/, "");
    if (!h) return null;
    var parts = h.split("/");
    var book = parts[0];
    var ch = parseInt(parts[1], 10) || 1;
    return book && bookById[book] ? { book: book, chapter: ch } : null;
  }

  // ---------------------------- rendering ----------------------------
  function buildGreek(verse) {
    // Prefer word-by-word spans (for morphology); fall back to plain text.
    if (verse.words && verse.words.length) {
      var frag = document.createDocumentFragment();
      verse.words.forEach(function (w, i) {
        var span = document.createElement("span");
        span.className = "tb-word";
        span.textContent = w.form || "";
        span.dataset.lemma = w.lemma || "";
        span.dataset.type = w.type || "";
        frag.appendChild(span);
        if (i < verse.words.length - 1) frag.appendChild(document.createTextNode(" "));
      });
      return frag;
    }
    return document.createTextNode(verse.grc || "");
  }

  function renderChapter(data) {
    var book = bookById[data.book];
    els.readerTitle.textContent = book.name + " " + data.chapter;
    els.readerGreek.textContent = book.greek_title || "";

    var frag = document.createDocumentFragment();
    var lastPara = null;
    data.verses.forEach(function (v) {
      var row = document.createElement("div");
      row.className = "tb-verse";
      if (v.para && v.para !== lastPara && !v.para_continued) row.classList.add("is-para-start");
      lastPara = v.para;

      var grcCol = document.createElement("div");
      grcCol.className = "tb-verse__col tb-verse__col--grc";
      var grc = document.createElement("p");
      grc.className = "tb-grc";
      var num1 = document.createElement("span");
      num1.className = "tb-verse__num";
      num1.textContent = v.v;
      grc.appendChild(num1);
      grc.appendChild(buildGreek(v));
      grcCol.appendChild(grc);

      var engCol = document.createElement("div");
      engCol.className = "tb-verse__col tb-verse__col--eng";
      var eng = document.createElement("p");
      eng.className = "tb-eng";
      var num2 = document.createElement("span");
      num2.className = "tb-verse__num";
      num2.textContent = v.v;
      eng.appendChild(num2);
      eng.appendChild(document.createTextNode(v.tr || ""));
      engCol.appendChild(eng);

      row.appendChild(grcCol);
      row.appendChild(engCol);
      frag.appendChild(row);
    });

    els.verses.innerHTML = "";
    els.verses.appendChild(frag);

    // chapter nav
    els.prev.disabled = !data.prev;
    els.next.disabled = !data.next;
    els.prev.onclick = data.prev ? function () { go(data.book, data.prev); } : null;
    els.next.onclick = data.next ? function () { go(data.book, data.next); } : null;

    // keep selects in sync
    els.bookSelect.value = data.book;
    populateChapters(book, data.chapter);

    hide(els.intro);
    show(els.reader);
    window.scrollTo(0, 0);
  }

  function loadChapter(book, chapter) {
    status("Loading…");
    getJSON(DATA + book + "/" + chapter + ".json")
      .then(function (data) { status(null); renderChapter(data); })
      .catch(function (err) {
        console.error(err);
        status("Could not load " + book + " " + chapter + ".");
      });
  }

  // Navigate (updates hash, which triggers the router).
  function go(book, chapter) {
    location.hash = "#" + book + "/" + chapter;
  }

  // ----------------------------- controls ----------------------------
  function populateBooks() {
    manifest.books.forEach(function (b) {
      var opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.name;
      els.bookSelect.appendChild(opt);
    });
  }

  function populateChapters(book, current) {
    els.chapterSelect.innerHTML = "";
    for (var c = 1; c <= book.chapters; c++) {
      var opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (c === current) opt.selected = true;
      els.chapterSelect.appendChild(opt);
    }
  }

  function buildBookGrid() {
    manifest.books.forEach(function (b) {
      var btn = document.createElement("button");
      btn.className = "tb-book";
      btn.type = "button";
      btn.innerHTML =
        '<span class="tb-book__name"></span><span class="tb-book__greek"></span>';
      btn.querySelector(".tb-book__name").textContent = b.name;
      btn.querySelector(".tb-book__greek").textContent = b.greek_title || "";
      btn.onclick = function () { go(b.id, 1); };
      els.bookGrid.appendChild(btn);
    });
  }

  // --------------------------- morphology ----------------------------
  function positionMorph(target) {
    var pop = els.morph;
    var r = target.getBoundingClientRect();
    pop.hidden = false;
    var top = window.scrollY + r.top - pop.offsetHeight - 8;
    if (top < window.scrollY + 4) top = window.scrollY + r.bottom + 8; // flip below
    var left = window.scrollX + r.left;
    var maxLeft = window.scrollX + document.documentElement.clientWidth - pop.offsetWidth - 8;
    if (left > maxLeft) left = maxLeft;
    if (left < window.scrollX + 4) left = window.scrollX + 4;
    pop.style.top = top + "px";
    pop.style.left = left + "px";
  }

  function showMorph(target) {
    if (!document.body.classList.contains("morph-on")) return;
    var lemma = target.dataset.lemma || "";
    var type = target.dataset.type || "";
    if (!lemma && !type) return;
    els.morph.innerHTML =
      '<span class="tb-morph__form"></span>' +
      ' &middot; <span class="tb-morph__type"></span><br>' +
      '<span class="tb-morph__lemma"></span>';
    els.morph.querySelector(".tb-morph__form").textContent = target.textContent;
    els.morph.querySelector(".tb-morph__type").textContent = type;
    els.morph.querySelector(".tb-morph__lemma").textContent = lemma ? "lemma: " + lemma : "";
    positionMorph(target);
    target.classList.add("is-active");
  }

  function hideMorph() {
    els.morph.hidden = true;
    var a = els.verses.querySelector(".tb-word.is-active");
    if (a) a.classList.remove("is-active");
  }

  function wireMorph() {
    // hover (desktop)
    els.verses.addEventListener("mouseover", function (e) {
      var w = e.target.closest(".tb-word");
      if (w) showMorph(w);
    });
    els.verses.addEventListener("mouseout", function (e) {
      if (e.target.closest(".tb-word")) hideMorph();
    });
    // tap (touch) — toggle
    els.verses.addEventListener("click", function (e) {
      var w = e.target.closest(".tb-word");
      if (!w) { hideMorph(); return; }
      if (w.classList.contains("is-active")) { hideMorph(); return; }
      hideMorph();
      showMorph(w);
    });
  }

  function setToggle(btn, on, cls) {
    btn.classList.toggle("is-on", on);
    btn.setAttribute("aria-pressed", String(on));
    document.body.classList.toggle(cls, on);
  }

  // ------------------------------ router -----------------------------
  function route() {
    var loc = parseHash();
    if (!loc) { hide(els.reader); show(els.intro); status(null); return; }
    loadChapter(loc.book, loc.chapter);
  }

  // ------------------------------- init ------------------------------
  function init() {
    els.year.textContent = String(new Date().getFullYear());

    getJSON(DATA + "manifest.json").then(function (m) {
      manifest = m;
      m.books.forEach(function (b) { bookById[b.id] = b; });

      els.footerDate.textContent = m.generated || "";
      els.introMeta.textContent =
        "Greek: " + (m.greek_source || "SBLGNT") +
        " · Translation: " + (m.translation && m.translation.name || "Terebinth") +
        " by " + (m.translation && m.translation.translator || "Timothy Noe") +
        " · Snapshot " + (m.generated || "");

      populateBooks();
      buildBookGrid();

      els.bookSelect.onchange = function () { go(this.value, 1); };
      els.chapterSelect.onchange = function () { go(els.bookSelect.value, this.value); };

      // default view state
      document.body.classList.add("show-greek", "morph-on");
      els.toggleGreek.onclick = function () {
        setToggle(this, !this.classList.contains("is-on"), "show-greek");
      };
      els.toggleMorph.onclick = function () {
        setToggle(this, !this.classList.contains("is-on"), "morph-on");
        if (!this.classList.contains("is-on")) hideMorph();
      };

      wireMorph();
      window.addEventListener("hashchange", route);
      window.addEventListener("scroll", hideMorph, { passive: true });
      route();
    }).catch(function (err) {
      console.error(err);
      status("Could not load the translation index. Please try again later.");
    });
  }

  init();
})();
