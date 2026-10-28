/* =====================================================
   Nordexa Digital – all JavaScript for nettsiden.
   Hver del sjekker selv om elementene finnes, så samme
   fil kan brukes på alle sider uten feil.
   ===================================================== */

(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function onScroll(fn) {
    var waiting = false;
    function run() { waiting = false; fn(); }
    window.addEventListener("scroll", function () {
      if (!waiting) { waiting = true; requestAnimationFrame(run); }
    }, { passive: true });
    fn();
  }

  function whenVisible(elements, callback, threshold) {
    if (!elements.length) return;
    if (!("IntersectionObserver" in window)) {
      elements.forEach(callback);
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          callback(entry.target);
        }
      });
    }, { threshold: threshold || 0.15 });
    elements.forEach(function (el) { observer.observe(el); });
  }

  function all(selector) {
    return Array.prototype.slice.call(document.querySelectorAll(selector));
  }


  /* ================= MENYEN BLIR TETTERE NÅR DU RULLER ================= */

  var navbar = document.getElementById("navbar");
  if (navbar) {
    onScroll(function () {
      navbar.classList.toggle("scrolled", window.scrollY > 50);
    });
  }


  /* ================= MOBILMENY ================= */

  var menuToggle = document.getElementById("menuToggle");
  var navLinks = document.getElementById("navLinks");

  function setMenu(open) {
    if (!menuToggle || !navLinks) return;
    navLinks.classList.toggle("open", open);
    document.documentElement.classList.toggle("menu-open", open);
    menuToggle.setAttribute("aria-expanded", String(open));
    menuToggle.setAttribute("aria-label", open ? "Lukk menyen" : "Åpne menyen");
  }

  if (menuToggle && navLinks) {
    menuToggle.addEventListener("click", function () {
      setSearch(false);
      setMenu(!navLinks.classList.contains("open"));
    });
    document.addEventListener("click", function (e) {
      if (!navLinks.contains(e.target) && !menuToggle.contains(e.target)) setMenu(false);
    });
  }


  /* ================= SØK ================= */

  var searchToggle = document.getElementById("searchToggle");
  var searchOverlay = document.getElementById("searchOverlay");
  var searchInput = document.getElementById("searchInput");

  function setSearch(open) {
    if (!searchToggle || !searchOverlay) return;
    searchOverlay.classList.toggle("active", open);
    searchToggle.setAttribute("aria-expanded", String(open));
    searchToggle.setAttribute("aria-label", open ? "Lukk søk" : "Åpne søk");
    if (open && searchInput) searchInput.focus();
  }

  if (searchToggle && searchOverlay) {
    searchOverlay.hidden = false; // skjult med CSS herfra, så det kan animeres
    searchToggle.addEventListener("click", function () {
      setMenu(false);
      setSearch(!searchOverlay.classList.contains("active"));
    });
    document.addEventListener("click", function (e) {
      if (!searchOverlay.contains(e.target) && !searchToggle.contains(e.target)) setSearch(false);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (searchOverlay && searchOverlay.classList.contains("active")) {
      setSearch(false);
      searchToggle.focus();
    }
    if (navLinks && navLinks.classList.contains("open")) {
      setMenu(false);
      menuToggle.focus();
    }
  });


  /* ================= INNHOLD SOM TONES INN ================= */

  whenVisible(all(".reveal"), function (el) {
    el.classList.add("reveal-active");
    // Når innfasingen er ferdig, får kortet tilbake den raske hover-effekten
    setTimeout(function () { el.classList.add("reveal-done"); }, reduceMotion ? 0 : 1300);
  });


  /* ================= TALL SOM TELLER OPP ================= */

  whenVisible(all(".stat-number"), function (counter) {
    var target = Number(counter.getAttribute("data-target"));
    var prefix = counter.getAttribute("data-prefix") || "";
    var suffix = counter.getAttribute("data-suffix") || "";
    if (reduceMotion || !isFinite(target)) return;

    var duration = 1800;
    var start = null;

    function tick(now) {
      if (start === null) start = now;
      var progress = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      counter.textContent = prefix + Math.round(target * eased) + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }

    counter.textContent = prefix + "0" + suffix;
    requestAnimationFrame(tick);
  }, 0.4);


  /* ================= SØYLER SOM VOKSER ================= */

  whenVisible(all(".bar-fill[data-width]"), function (bar) {
    var width = Math.max(0, Math.min(100, Number(bar.getAttribute("data-width")) || 0));
    requestAnimationFrame(function () { bar.style.width = width + "%"; });
  }, 0.2);


  /* ================= TELLING AV KLIKK (uten informasjonskapsler) ================= */

  function sendEvent(name) {
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/hendelse", new Blob([name], { type: "text/plain" }));
      }
    } catch (err) { /* statistikk skal aldri ødelegge noe */ }
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("[data-event]") : null;
    if (el && el.tagName !== "BUTTON") sendEvent(el.getAttribute("data-event"));
  });


  /* ================= SKJEMAER: VIS AT NOE SKJER ================= */

  all("form").forEach(function (form) {
    var button = form.querySelector("button[data-busy]");
    if (!button) return;
    form.addEventListener("submit", function () {
      sendEvent(button.getAttribute("data-event"));
      button.textContent = button.getAttribute("data-busy");
      // slås av etter at skjemaet er sendt, ellers stopper noen nettlesere innsendingen
      setTimeout(function () { button.disabled = true; }, 0);
    });
  });

  window.addEventListener("pageshow", function (e) {
    if (e.persisted) all("button[data-busy]").forEach(function (b) { b.disabled = false; });
  });


  /* ================= BLOGG: FREMDRIFTSLINJE ================= */

  var blogTimeline = document.getElementById("blogTimeline");
  var blogProgress = document.getElementById("blogProgress");
  var blogBlocks = all(".blog-block");

  if (blogTimeline && blogProgress) {
    onScroll(function () {
      var rect = blogTimeline.getBoundingClientRect();
      var reference = window.innerHeight * 0.6;
      var progress = (reference - rect.top) / rect.height;
      progress = Math.max(0, Math.min(1, progress));
      blogProgress.style.height = (progress * 100) + "%";

      blogBlocks.forEach(function (block) {
        if (block.getBoundingClientRect().top < window.innerHeight - 100) {
          block.classList.add("visible");
        }
      });
    });
  }


  /* ================= NORDLYS I TOPPEN AV FORSIDEN ================= */

  var aurora = document.getElementById("aurora");

  if (aurora && aurora.getContext) {
    var ctx = aurora.getContext("2d");
    var width = 0;
    var height = 0;
    var frame = null;
    var visible = true;

    var bands = [
      { y: 0.30, wave: 0.11, thick: 0.26, freq: 5.2, speed: 0.00016, from: "0,191,255", to: "255,77,77", alpha: 0.75 },
      { y: 0.52, wave: 0.14, thick: 0.22, freq: 3.6, speed: 0.00011, from: "0,120,255", to: "255,0,120", alpha: 0.55 },
      { y: 0.70, wave: 0.09, thick: 0.20, freq: 6.4, speed: 0.00021, from: "0,191,255", to: "0,191,255", alpha: 0.38 }
    ];

    var resize = function () {
      var rect = aurora.getBoundingClientRect();
      width = aurora.width = Math.max(240, Math.round(rect.width / 4));
      height = aurora.height = Math.max(160, Math.round(rect.height / 4));
    };

    var draw = function (now) {
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";

      bands.forEach(function (band, index) {
        var gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, "rgba(" + band.from + ",0)");
        gradient.addColorStop(0.3, "rgba(" + band.from + "," + band.alpha + ")");
        gradient.addColorStop(0.72, "rgba(" + band.to + "," + band.alpha + ")");
        gradient.addColorStop(1, "rgba(" + band.to + ",0)");

        var top = [];
        for (var x = 0; x <= width; x += 6) {
          var p = x / width;
          var y = band.y
            + band.wave * Math.sin(p * band.freq + now * band.speed + index * 2)
            + band.wave * 0.5 * Math.sin(p * band.freq * 2.3 - now * band.speed * 1.7);
          top.push([x, y * height]);
        }

        ctx.beginPath();
        top.forEach(function (pt, i) { if (i) ctx.lineTo(pt[0], pt[1]); else ctx.moveTo(pt[0], pt[1]); });
        for (var i = top.length - 1; i >= 0; i--) {
          var thickness = band.thick * height * (0.6 + 0.4 * Math.sin(top[i][0] / width * 4 + now * band.speed * 0.8));
          ctx.lineTo(top[i][0], top[i][1] + thickness);
        }
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
      });
    };

    var loop = function (now) {
      draw(now);
      frame = visible && !reduceMotion ? requestAnimationFrame(loop) : null;
    };

    resize();
    window.addEventListener("resize", function () { resize(); if (!frame) draw(performance.now()); });

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible && !frame && !reduceMotion) frame = requestAnimationFrame(loop);
      }).observe(aurora);
    }

    document.addEventListener("visibilitychange", function () {
      visible = !document.hidden;
      if (visible && !frame && !reduceMotion) frame = requestAnimationFrame(loop);
    });

    loop(performance.now());

    /* Parallakse: bakgrunnen beveger seg saktere enn resten */
    if (!reduceMotion) {
      onScroll(function () {
        if (window.scrollY < window.innerHeight * 1.2) {
          aurora.style.transform = "translateY(" + (window.scrollY * 0.3) + "px)";
        }
      });
    }
  }


  /* ================= MYK OVERGANG MELLOM SIDER ================= */

  if (!reduceMotion) {
    document.addEventListener("click", function (e) {
      var link = e.target.closest ? e.target.closest("a") : null;
      if (!link || e.defaultPrevented) return;
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (link.target === "_blank" || link.hasAttribute("download")) return;
      if (link.origin !== window.location.origin) return;
      if (link.pathname === window.location.pathname && link.hash) return; // lenke på samme side

      e.preventDefault();
      document.body.classList.add("page-leaving");
      setTimeout(function () { window.location.href = link.href; }, 280);
    });
  }

  // Når du går tilbake i nettleseren, skal siden være synlig igjen
  window.addEventListener("pageshow", function () {
    document.body.classList.remove("page-leaving");
  });


  /* ================= SLETTING MÅ BEKREFTES ================= */

  all(".confirm-form").forEach(function (form) {
    var button = form.querySelector("button");
    var original = button.textContent;
    var armed = false;
    var timer = null;

    form.addEventListener("submit", function (e) {
      if (armed) return;
      e.preventDefault();
      armed = true;
      button.textContent = "Trykk igjen for å slette";
      timer = setTimeout(function () {
        armed = false;
        button.textContent = original;
      }, 4000);
    });

    button.addEventListener("blur", function () {
      clearTimeout(timer);
      armed = false;
      button.textContent = original;
    });
  });


  /* ================= MELDING OM INFORMASJONSKAPSLER ================= */

  var cookieBanner = document.getElementById("cookieBanner");
  var acceptCookies = document.getElementById("acceptCookies");

  if (cookieBanner && acceptCookies) {
    var seen = false;
    try { seen = localStorage.getItem("cookiesAccepted") === "true"; } catch (err) { /* privat modus */ }
    cookieBanner.hidden = seen;

    acceptCookies.addEventListener("click", function () {
      try { localStorage.setItem("cookiesAccepted", "true"); } catch (err) { /* privat modus */ }
      cookieBanner.hidden = true;
    });
  }
})();
