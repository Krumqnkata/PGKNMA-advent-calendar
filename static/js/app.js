/* Адвент календар: вратички, модален прозорец, брояч и музика. */
(function () {
  "use strict";

  var TYPES = {
    wish: { label: "Пожелание", icon: "gift" },
    challenge: { label: "Предизвикателство", icon: "trophy" },
    riddle: { label: "Гатанка", icon: "riddle" },
    quote: { label: "Цитат", icon: "quote" },
    joke: { label: "Шега", icon: "smile" },
    fact: { label: "Интересен факт", icon: "bulb" },
    photo: { label: "Снимка", icon: "camera" }
  };
  var DECOS = ["snowflake", "star", "tree", "bell", "sparkle"];
  var SPARK_COLORS = ["#f7e0a3", "#ffffff", "#8fd3c3", "#ff8a9a"];
  var STORAGE_VISIT = "advent-visit";
  var STORAGE_MUSIC = "advent-music";
  var LOCKED_MESSAGE = "Още не е време!";

  var calendar = document.getElementById("calendar");
  if (!calendar) return;

  // Отворените, харесаните и изпълнените вратички са за конкретна година,
  // за да не се пренасят в календара за следващата година.
  var yearKey = "advent-" + calendar.dataset.year + "-";
  var STORAGE_OPENED = yearKey + "opened";
  var STORAGE_COUNTED = yearKey + "counted";
  var STORAGE_HEARTS = yearKey + "hearts";
  var STORAGE_DONE = yearKey + "done";

  var apiBase = calendar.dataset.api;
  var visitApi = calendar.dataset.visitApi;
  var todayIso = calendar.dataset.today;
  var preview = calendar.dataset.preview === "1";
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var unlockedDays = new Set();

  /* --- localStorage (може да липсва в частен режим) --- */

  var storage = {
    get: function (key, fallback) {
      try {
        var value = window.localStorage.getItem(key);
        return value === null ? fallback : JSON.parse(value);
      } catch (e) {
        return fallback;
      }
    },
    set: function (key, value) {
      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch (e) { /* няма място или е забранено */ }
    },
    remove: function (key) {
      try {
        window.localStorage.removeItem(key);
      } catch (e) { /* без значение */ }
    }
  };

  // Множества от дни (отворени, харесани, изпълнени), пазени само в браузъра.
  function getDays(key) {
    var list = storage.get(key, []);
    return new Set(Array.isArray(list) ? list.map(Number) : []);
  }

  function setDay(key, day, on) {
    var days = getDays(key);
    if (on) days.add(day);
    else days.delete(day);
    storage.set(key, Array.from(days).sort(function (a, b) { return a - b; }));
  }

  function getOpened() {
    return getDays(STORAGE_OPENED);
  }

  function markOpened(day) {
    setDay(STORAGE_OPENED, day, true);
  }

  function plural(n, one, many) {
    return n === 1 ? one : many;
  }

  /* --- Помощни --- */

  function icon(name, className) {
    return '<svg class="icon ' + (className || "") + '" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
  }

  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function toast(message) {
    toastEl.textContent = message;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove("show");
    }, 2600);
  }

  /* --- Брояч на отворените --- */

  var countEl = document.getElementById("opened-count");
  var totalEl = document.getElementById("opened-total");
  var barEl = document.getElementById("opened-bar");

  function updateProgress(total) {
    if (!countEl) return;
    var opened = calendar.querySelectorAll(".door.is-open").length;
    if (typeof total === "number") totalEl.textContent = String(total);
    var max = Number(totalEl.textContent) || 1;
    countEl.textContent = String(opened);
    barEl.style.width = Math.min(100, (opened / max) * 100) + "%";
  }

  /* --- API --- */

  function apiUrl(path) {
    var url = new URL(path, window.location.href);
    if (preview) url.searchParams.set("preview", "1");
    return url.toString();
  }

  function fetchJson(path) {
    return fetch(apiUrl(path), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      cache: "no-store"
    });
  }

  // Анонимни броячи: без бисквитки и без идентификатори.
  function postJson(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body || {}),
      credentials: "omit",
      keepalive: true
    }).then(function (response) {
      if (!response.ok) {
        var error = new Error("HTTP " + response.status);
        error.status = response.status;
        throw error;
      }
      return response.json();
    });
  }

  function react(day, action, active) {
    return postJson(apiBase + day + "/react/", { action: action, active: active });
  }

  function countVisit() {
    if (preview || !visitApi || storage.get(STORAGE_VISIT, null) === todayIso) return;
    postJson(visitApi)
      .then(function () { storage.set(STORAGE_VISIT, todayIso); })
      .catch(function () { /* статистиката не е важна за потребителя */ });
  }

  function countOpen(day) {
    if (preview || getDays(STORAGE_COUNTED).has(day)) return;
    react(day, "open", true)
      .then(function () { setDay(STORAGE_COUNTED, day, true); })
      .catch(function () {});
  }

  /* --- Декоративно (но стабилно) подреждане --- */

  function seededRandom(seed) {
    return function () {
      seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function shuffle(list, rand) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(rand() * (i + 1));
      var tmp = list[i];
      list[i] = list[j];
      list[j] = tmp;
    }
    return list;
  }

  /* --- Рендериране --- */

  function setLabel(btn) {
    var day = btn.dataset.day;
    var parts = ["Вратичка " + day];
    if (btn.classList.contains("is-today")) parts.push("днешна");
    if (btn.classList.contains("is-locked")) parts.push("заключена");
    if (btn.classList.contains("is-open")) parts.push("отворена");
    btn.setAttribute("aria-label", parts.join(", "));
  }

  // Размерите се подбират така, че общият брой клетки да се дели на 12
  // (6, 4 и 3 колони), за да няма празни места в края на решетката.
  function pickSizes(doors, rand, lastDay) {
    var sizes = doors.map(function (door) {
      if (door.day === lastDay) return "big";
      var r = rand();
      return r < 0.12 ? "wide" : r < 0.2 ? "tall" : "";
    });
    var cells = sizes.reduce(function (sum, size) {
      return sum + (size === "big" ? 4 : size ? 2 : 1);
    }, 0);
    for (var step = 0; cells % 12 !== 0 && step < sizes.length * 2; step++) {
      var i = (step * 7 + 3) % sizes.length;
      if (!sizes[i]) {
        sizes[i] = "wide";
        cells += 1;
      }
    }
    return sizes;
  }

  function createDoor(door, size, rand, today) {
    var type = TYPES[door.type] || TYPES.wish;
    var variant = Math.floor(rand() * 5);
    var hasRibbon = variant === 2 || rand() < 0.18;
    var snowy = rand() < 0.38;
    var deco = DECOS[Math.floor(rand() * DECOS.length)];

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "door";
    btn.dataset.day = String(door.day);
    btn.dataset.type = door.type;
    btn.dataset.variant = String(variant);
    btn.style.setProperty("--tilt", (rand() * 3 - 1.5).toFixed(2) + "deg");
    btn.style.setProperty("--shift", (rand() * 8 - 4).toFixed(1) + "px");

    if (size) btn.classList.add(size);
    if (hasRibbon) btn.classList.add("has-ribbon");
    if (door.unlocked) btn.classList.add("is-ready");
    else btn.classList.add("is-locked");
    if (door.day === today) btn.classList.add("is-today");

    var number = '<span class="door-number">' + door.day + "</span>";
    // Само числа и константи: съдържанието на вратата идва отделно, след отключване.
    btn.innerHTML =
      '<span class="door-inner">' +
        '<span class="door-back" aria-hidden="true">' +
          icon(type.icon, "door-back-icon") +
          '<span class="door-back-label">' + type.label + "</span>" +
        "</span>" +
        '<span class="door-front" aria-hidden="true">' +
          '<span class="door-face">' +
            (hasRibbon ? '<span class="door-ribbon"></span><span class="door-medal">' + number + "</span>" : number) +
            icon(deco, "door-deco") +
            (door.unlocked ? "" : icon("lock", "door-lock")) +
            '<span class="door-knob"></span>' +
          "</span>" +
          (snowy ? '<span class="door-snow"></span>' : "") +
        "</span>" +
      "</span>";
    setLabel(btn);
    return btn;
  }

  function renderDoors(data) {
    var opened = getOpened();
    var rand = seededRandom(1225);
    var doors = shuffle(data.doors.slice(), rand);

    calendar.textContent = "";
    calendar.setAttribute("aria-busy", "false");
    unlockedDays = new Set();

    if (!doors.length) {
      var empty = document.createElement("p");
      empty.className = "calendar-message";
      empty.textContent = "Все още няма публикувани вратички.";
      calendar.appendChild(empty);
      updateProgress(0);
      return;
    }

    var sizes = pickSizes(doors, rand, data.last_day);
    doors.forEach(function (door, index) {
      var el = createDoor(door, sizes[index], rand, data.today);
      if (door.unlocked) unlockedDays.add(door.day);
      // Вратата остава отворена само ако и сървърът я счита за отключена.
      if (door.unlocked && opened.has(door.day)) {
        el.classList.add("is-open");
        el.classList.remove("is-ready");
        setLabel(el);
      }
      calendar.appendChild(el);
    });
    updateProgress(doors.length);
  }

  /* --- Отваряне --- */

  function refuse(btn) {
    toast(LOCKED_MESSAGE);
    if (reduceMotion.matches) return;
    btn.classList.remove("is-shaking");
    void btn.offsetWidth; // рестартира анимацията
    btn.classList.add("is-shaking");
  }

  calendar.addEventListener("animationend", function (event) {
    if (event.animationName === "shake") {
      var door = event.target.closest(".door");
      if (door) door.classList.remove("is-shaking");
    }
  });

  function sparkle(btn) {
    if (reduceMotion.matches) return;
    var burst = document.createElement("span");
    burst.className = "burst";
    for (var i = 0; i < 16; i++) {
      var spark = document.createElement("i");
      var angle = (Math.PI * 2 * i) / 16 + Math.random() * 0.4;
      var distance = 40 + Math.random() * 46;
      spark.style.setProperty("--dx", (Math.cos(angle) * distance).toFixed(1) + "px");
      spark.style.setProperty("--dy", (Math.sin(angle) * distance).toFixed(1) + "px");
      spark.style.setProperty("--delay", (Math.random() * 0.12).toFixed(2) + "s");
      spark.style.setProperty("--spark", SPARK_COLORS[i % SPARK_COLORS.length]);
      burst.appendChild(spark);
    }
    btn.appendChild(burst);
    setTimeout(function () { burst.remove(); }, 1300);
  }

  function swingOpen(btn) {
    return new Promise(function (resolve) {
      btn.classList.remove("is-ready");
      btn.classList.add("is-open");
      sparkle(btn);
      if (reduceMotion.matches) {
        resolve();
        return;
      }
      var front = btn.querySelector(".door-front");
      var done = false;
      function finish() {
        if (done) return;
        done = true;
        front.removeEventListener("transitionend", onEnd);
        resolve();
      }
      function onEnd(event) {
        if (event.target === front && event.propertyName === "transform") finish();
      }
      front.addEventListener("transitionend", onEnd);
      setTimeout(finish, 1000);
    });
  }

  var busy = false;

  function onDoorClick(btn) {
    if (busy) return;
    var day = Number(btn.dataset.day);

    if (btn.classList.contains("is-locked")) {
      refuse(btn);
      return;
    }

    busy = true;
    fetchJson(apiBase + day + "/")
      .then(function (response) {
        if (response.status === 403) {
          btn.classList.remove("is-ready");
          btn.classList.add("is-locked");
          refuse(btn);
          return null;
        }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (content) {
        if (!content) return null;
        var wasOpen = btn.classList.contains("is-open");
        return (wasOpen ? Promise.resolve() : swingOpen(btn)).then(function () {
          if (!wasOpen) {
            markOpened(day);
            setLabel(btn);
            updateProgress();
          }
          countOpen(day);
          showModal(content, btn);
        });
      })
      .catch(function () {
        toast("Нещо се обърка. Опитай отново.");
      })
      .then(function () {
        busy = false;
      });
  }

  calendar.addEventListener("click", function (event) {
    var btn = event.target.closest(".door");
    if (btn && calendar.contains(btn)) onDoorClick(btn);
  });

  /* --- Модален прозорец --- */

  var modal = document.getElementById("door-modal");
  var modalIcon = modal.querySelector(".modal-icon");
  var modalType = modal.querySelector(".modal-type");
  var modalDay = modal.querySelector(".modal-day");
  var modalTitle = modal.querySelector(".modal-title");
  var modalText = modal.querySelector(".modal-text");
  var modalFigure = modal.querySelector(".modal-figure");
  var modalImage = modalFigure.querySelector("img");
  var modalCredit = modalFigure.querySelector(".modal-credit");

  // Автор и лиценз под снимката; връзката към източника е само ако е http(s).
  function renderCredit(credit, source) {
    modalCredit.textContent = "";
    modalCredit.hidden = !credit;
    if (!credit) return;
    modalCredit.appendChild(document.createTextNode("Снимка: "));
    if (source && /^https?:\/\//i.test(source)) {
      var link = document.createElement("a");
      link.href = source;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = credit;
      modalCredit.appendChild(link);
    } else {
      modalCredit.appendChild(document.createTextNode(credit));
    }
  }
  var modalAnswer = modal.querySelector(".modal-answer");
  var answerBtn = modal.querySelector(".btn-answer");
  var answerText = modal.querySelector(".answer-text");
  var heartBtn = modal.querySelector(".react-heart");
  var heartCount = modal.querySelector(".react-heart-count");
  var doneBtn = modal.querySelector(".react-done");
  var doneLabel = modal.querySelector(".react-done-label");
  var doneCount = modal.querySelector(".react-done-count");
  var lastOpener = null;
  var current = null; // { day, type, hearts, completions }

  function renderReactions() {
    var hearted = getDays(STORAGE_HEARTS).has(current.day);
    heartBtn.setAttribute("aria-pressed", hearted ? "true" : "false");
    heartBtn.setAttribute("aria-label", (hearted ? "Харесано" : "Харесва ми") + ", " + current.hearts);
    heartCount.textContent = String(current.hearts);

    var isChallenge = current.type === "challenge";
    doneBtn.hidden = !isChallenge;
    doneCount.hidden = !isChallenge;
    if (!isChallenge) return;

    var done = getDays(STORAGE_DONE).has(current.day);
    doneBtn.setAttribute("aria-pressed", done ? "true" : "false");
    doneLabel.textContent = done ? "Изпълнено!" : "Изпълних предизвикателството!";
    var n = current.completions;
    doneCount.textContent = n
      ? "Изпълнено от " + n + " " + plural(n, "човек", "души")
      : "Бъди първият, който го изпълни!";
  }

  function toggleReaction(action, key, field, button) {
    if (!current) return;
    var day = current.day;
    var on = !getDays(key).has(day);
    setDay(key, day, on);
    current[field] = Math.max(0, current[field] + (on ? 1 : -1));
    renderReactions();
    if (on && !reduceMotion.matches) {
      button.classList.remove("is-bouncing");
      void button.offsetWidth;
      button.classList.add("is-bouncing");
    }

    react(day, action, on)
      .then(function (counts) {
        if (!current || current.day !== day) return;
        current.hearts = counts.hearts;
        current.completions = counts.completions;
        renderReactions();
      })
      .catch(function (error) {
        setDay(key, day, !on);
        if (current && current.day === day) {
          current[field] = Math.max(0, current[field] + (on ? -1 : 1));
          renderReactions();
        }
        toast(error.status === 403
          ? "В тестов режим реакциите за бъдещи дни не се записват."
          : "Не успяхме да запишем това. Опитай пак.");
      });
  }

  heartBtn.addEventListener("click", function () {
    toggleReaction("heart", STORAGE_HEARTS, "hearts", heartBtn);
  });

  doneBtn.addEventListener("click", function () {
    toggleReaction("done", STORAGE_DONE, "completions", doneBtn);
  });

  modal.addEventListener("animationend", function (event) {
    if (event.animationName === "bounce") event.target.classList.remove("is-bouncing");
  });

  function showModal(content, opener) {
    var type = TYPES[content.type] || TYPES.wish;
    lastOpener = opener;

    modal.dataset.type = content.type;
    modalIcon.setAttribute("href", "#i-" + type.icon);
    modalType.textContent = content.type_label || type.label;
    modalDay.textContent = "Ден " + content.day;
    modalTitle.textContent = content.title;
    modalText.textContent = content.text || "";
    modalText.hidden = !content.text;

    if (content.image) {
      modalImage.src = content.image;
      modalImage.alt = content.title;
      modalFigure.hidden = false;
      renderCredit(content.image_credit, content.image_source);
    } else {
      modalImage.removeAttribute("src");
      modalFigure.hidden = true;
    }

    var hasAnswer = content.type === "riddle" && content.answer;
    modalAnswer.hidden = !hasAnswer;
    answerText.hidden = true;
    answerText.textContent = hasAnswer ? content.answer : "";
    answerBtn.hidden = false;
    answerBtn.setAttribute("aria-expanded", "false");

    current = {
      day: content.day,
      type: content.type,
      hearts: content.hearts || 0,
      completions: content.completions || 0
    };
    renderReactions();

    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      modal.setAttribute("open", "");
    }
    modal.querySelector(".modal-body").scrollTop = 0;
    modal.querySelector(".modal-close").focus();
  }

  function closeModal() {
    if (typeof modal.close === "function") modal.close();
    else modal.removeAttribute("open");
  }

  answerBtn.addEventListener("click", function () {
    answerText.hidden = false;
    answerBtn.hidden = true;
    answerBtn.setAttribute("aria-expanded", "true");
  });

  modal.querySelector(".modal-close").addEventListener("click", closeModal);

  // Клик извън картата (върху фона) затваря прозореца.
  modal.addEventListener("click", function (event) {
    if (event.target === modal) closeModal();
  });

  modal.addEventListener("close", function () {
    if (lastOpener) lastOpener.focus({ preventScroll: true });
  });

  /* --- Нулиране --- */

  document.getElementById("reset-doors").addEventListener("click", function () {
    storage.remove(STORAGE_OPENED);
    calendar.querySelectorAll(".door.is-open").forEach(function (door) {
      door.classList.remove("is-open");
      if (unlockedDays.has(Number(door.dataset.day))) door.classList.add("is-ready");
      setLabel(door);
    });
    updateProgress();
    toast("Всички вратички са затворени.");
  });

  /* --- Музика --- */

  var audio = document.getElementById("music");
  var musicBtn = document.getElementById("music-toggle");
  var musicIcon = musicBtn.querySelector("use");
  var musicOn = storage.get(STORAGE_MUSIC, "off") === "on";
  var pendingResume = null;

  audio.volume = 0.35;

  function renderMusicButton() {
    musicBtn.setAttribute("aria-pressed", musicOn ? "true" : "false");
    musicIcon.setAttribute("href", musicOn ? "#i-volume" : "#i-volume-x");
    musicBtn.title = musicOn ? "Заглуши музиката" : "Пусни музиката";
  }

  function setMusic(on) {
    musicOn = on;
    storage.set(STORAGE_MUSIC, on ? "on" : "off");
    renderMusicButton();
  }

  function musicUnavailable() {
    audio.pause();
    setMusic(false);
    toast("Музикалният файл липсва (static/music/theme.mp3).");
  }

  function clearPendingResume() {
    if (!pendingResume) return;
    document.removeEventListener("pointerdown", pendingResume, true);
    document.removeEventListener("keydown", pendingResume, true);
    pendingResume = null;
  }

  function play() {
    return audio.play().catch(function (error) {
      if (error && error.name === "NotAllowedError") throw error;
      musicUnavailable();
    });
  }

  // Браузърите блокират автоматичното пускане: изчакваме първото действие на потребителя.
  function resumeOnFirstGesture() {
    pendingResume = function (event) {
      if (event.target.closest && event.target.closest("#music-toggle")) return;
      clearPendingResume();
      if (musicOn) play().catch(function () {});
    };
    document.addEventListener("pointerdown", pendingResume, true);
    document.addEventListener("keydown", pendingResume, true);
  }

  musicBtn.addEventListener("click", function () {
    clearPendingResume();
    if (musicOn) {
      audio.pause();
      setMusic(false);
      return;
    }
    setMusic(true);
    play().catch(function () {
      toast("Браузърът блокира звука. Натисни бутона отново.");
      setMusic(false);
    });
  });

  renderMusicButton();
  if (musicOn) {
    play().catch(resumeOnFirstGesture);
  }

  /* --- Обратно броене до първата вратичка --- */

  var countdownEl = document.querySelector(".countdown");
  var UNIT_FORMS = {
    days: ["ден", "дни"],
    hours: ["час", "часа"],
    minutes: ["минута", "минути"],
    seconds: ["секунда", "секунди"]
  };

  // Цифрата е вратичка: старото число се отваря, отзад е новото, после вратичката се затваря с него.
  function swingDigit(unitEl, text) {
    var back = unitEl.querySelector(".cd-back");
    var door = unitEl.querySelector(".cd-door");
    var face = door.querySelector(".countdown-value");
    if (back.textContent === text) return;
    back.textContent = text;
    if (reduceMotion.matches) {
      face.textContent = text;
      return;
    }
    door.classList.remove("is-opening", "is-closing");
    void door.offsetWidth; // рестартира анимацията
    door.classList.add("is-opening");
  }

  if (countdownEl) {
    countdownEl.addEventListener("animationend", function (event) {
      var door = event.target;
      if (event.animationName === "cd-open") {
        door.querySelector(".countdown-value").textContent =
          door.parentNode.querySelector(".cd-back").textContent;
        door.classList.remove("is-opening");
        door.classList.add("is-closing");
      } else if (event.animationName === "cd-close") {
        door.classList.remove("is-closing");
      }
    });
  }

  function startCountdown(el) {
    var target = Date.parse(el.dataset.start);
    // Ползваме часовника на сървъра, ако този на устройството е сверен грешно.
    var offset = Date.parse(el.dataset.now) - Date.now();
    var timer = null;

    function tick() {
      var left = Math.max(0, Math.floor((target - (Date.now() + offset)) / 1000));
      var parts = {
        days: Math.floor(left / 86400),
        hours: Math.floor((left % 86400) / 3600),
        minutes: Math.floor((left % 3600) / 60),
        seconds: left % 60
      };
      Object.keys(parts).forEach(function (unit) {
        var value = parts[unit];
        var unitEl = el.querySelector('[data-unit="' + unit + '"]');
        swingDigit(unitEl, unit === "days" ? String(value) : String(value).padStart(2, "0"));
        unitEl.querySelector(".countdown-label").textContent =
          plural(value, UNIT_FORMS[unit][0], UNIT_FORMS[unit][1]);
      });
      if (left === 0) {
        clearInterval(timer);
        setTimeout(function () { window.location.reload(); }, 1500);
      }
    }

    tick();
    timer = setInterval(tick, 1000);
  }

  if (countdownEl && !isNaN(Date.parse(countdownEl.dataset.start))) {
    startCountdown(countdownEl);
  }

  /* --- Старт --- */

  countVisit();

  fetchJson(apiBase)
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(renderDoors)
    .catch(function () {
      calendar.setAttribute("aria-busy", "false");
      calendar.textContent = "";
      var error = document.createElement("p");
      error.className = "calendar-message";
      error.textContent = "Календарът не може да се зареди. Опитай да презаредиш страницата.";
      calendar.appendChild(error);
    });
})();
