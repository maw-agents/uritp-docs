/* URITP Docs — in-site Theme Lab.

   A floating control dock that retunes the LIVE site in real time. Every knob
   writes a CSS custom property onto <html>, overriding docs/stylesheets/uritp.css
   for this browser only.

   OPEN IT:   add ?lab to any page URL.  Sticks until you turn it off.
   CLOSE IT:  the dock's own switch, or ?lab=off

   ── WHY THIS NEEDS NO PASSWORD ──────────────────────────────────────────────
   It cannot change what anyone else sees. There is no write path from a browser
   to a static site: settings live in this browser's localStorage and reach the
   real site only when the generated CSS is committed to the repo, which needs
   repo access. A stranger who finds ?lab can restyle their own screen and
   nothing more. Obscurity is enough here precisely because the blast radius is
   one person's tab.

   ── MAKING A CHANGE STICK ───────────────────────────────────────────────────
   Ship -> copies the palette block. Paste over the top of uritp.css, commit,
   ~90s rebuild. The dock also links straight to that file in GitHub's editor.

   Wired in mkdocs.yml under extra_javascript. Documented in README.md.
   POINTER: if a token name here stops matching uritp.css, the knob silently
   does nothing. Change both in the same PR. */

(function () {
  'use strict';

  var FLAG = 'uritp:lab';
  var SAVE = 'uritp:lab:state';
  var EDIT = 'https://github.com/maw-agents/uritp-docs/edit/main/docs/stylesheets/uritp.css';

  /* ?lab / ?lab=off ------------------------------------------------------- */
  var q = new URLSearchParams(location.search);
  if (q.has('lab')) {
    if (q.get('lab') === 'off') { localStorage.removeItem(FLAG); localStorage.removeItem(SAVE); }
    else { localStorage.setItem(FLAG, '1'); }
    history.replaceState(null, '', location.pathname + location.hash);
  }

  var DEFAULTS = {
    hue: 282, chr: 0.145, lig: 48,
    nhue: 258, plig: 98.4, tlig: 41, rlig: 91,
    rbox: 10, rpill: 5, rctl: 7, bw: 1,
    serif: 'Crimson Pro', scale: 1, ahue: 62
  };

  var PRESETS = [
    { n: 'Violet',  h: 282, c: 0.145, l: 48, nh: 258 },
    { n: 'Ink',     h: 265, c: 0.045, l: 32, nh: 265 },
    { n: 'Oxblood', h: 18,  c: 0.135, l: 42, nh: 22  },
    { n: 'Forest',  h: 158, c: 0.095, l: 40, nh: 160 },
    { n: 'Slate',   h: 232, c: 0.075, l: 44, nh: 236 },
    { n: 'Rust',    h: 44,  c: 0.135, l: 47, nh: 52  },
    { n: 'Teal',    h: 198, c: 0.105, l: 44, nh: 205 },
    { n: 'Plum',    h: 330, c: 0.115, l: 44, nh: 322 }
  ];

  var FONTS = {
    'Crimson Pro':       'wght@400;500;600',
    'Fraunces':          'opsz,wght@9..144,400;9..144,500;9..144,600',
    'Instrument Serif':  'ital@0;1',
    'Libre Baskerville': 'wght@400;700',
    'Space Grotesk':     'wght@400;500;600;700',
    'DM Sans':           'opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600'
  };

  var SOFT = {
    'Sharp':  [0, 0, 0],
    'Crisp':  [4, 3, 4],
    'Soft':   [10, 5, 7],
    'Rounder':[16, 8, 10],
    'Pill':   [22, 999, 12]
  };

  var S = load();

  function load() {
    var out = {};
    for (var k in DEFAULTS) out[k] = DEFAULTS[k];
    try {
      var raw = JSON.parse(localStorage.getItem(SAVE) || '{}');
      for (var j in raw) if (j in out) out[j] = raw[j];
    } catch (e) { /* corrupt save: fall back to defaults rather than break the site */ }
    return out;
  }

  function save() { localStorage.setItem(SAVE, JSON.stringify(S)); }

  /* Applied on EVERY page load when saved settings exist, dock open or not,
     so the site stays consistent while browsing. */
  function apply() {
    var r = document.documentElement.style;
    var P   = 'oklch(' + S.lig + '% ' + S.chr + ' ' + S.hue + ')';
    var A   = 'oklch(' + Math.max(24, S.lig - 4) + '% ' + (S.chr + 0.01).toFixed(3) + ' ' + S.hue + ')';
    var PB  = 'oklch(99% 0.003 ' + S.hue + ')';
    var BG  = 'oklch(' + S.plig + '% 0.006 ' + S.nhue + ')';
    var TX  = 'oklch(' + S.tlig + '% 0.014 ' + S.nhue + ')';
    var INK = 'oklch(' + Math.max(14, S.tlig - 20) + '% 0.018 ' + S.nhue + ')';
    var LT  = 'oklch(' + Math.min(72, S.tlig + 17) + '% 0.012 ' + S.nhue + ')';
    var RL  = 'oklch(' + S.rlig + '% 0.008 ' + S.nhue + ')';
    var AM  = 'oklch(52% 0.12 ' + S.ahue + ')';
    var fam = '"' + S.serif + '", ' +
      (/Grotesk|DM Sans/.test(S.serif) ? 'system-ui, sans-serif' : 'Georgia, serif');

    r.setProperty('--md-primary-fg-color', P);
    r.setProperty('--md-accent-fg-color', A);
    r.setProperty('--md-primary-bg-color', PB);
    r.setProperty('--md-typeset-a-color', P);
    r.setProperty('--md-default-bg-color', BG);
    r.setProperty('--md-typeset-color', TX);
    r.setProperty('--md-default-fg-color', INK);
    r.setProperty('--md-default-fg-color--light', LT);
    r.setProperty('--md-default-fg-color--lightest', RL);
    r.setProperty('--serif', fam);
    r.setProperty('--amber', AM);

    ensureFont(S.serif);
    softCSS();
    if (window.__labPaint) window.__labPaint();
  }

  function ensureFont(name) {
    var id = 'lab-font-' + name.replace(/\W/g, '');
    if (document.getElementById(id)) return;
    var l = document.createElement('link');
    l.id = id; l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=' +
      name.replace(/ /g, '+') + ':' + FONTS[name] + '&display=swap';
    document.head.appendChild(l);
  }

  /* Radius and border width are not tokens in uritp.css, so the dock injects
     real rules for them rather than setting variables. */
  function softCSS() {
    var el = document.getElementById('lab-soft') || (function () {
      var s = document.createElement('style'); s.id = 'lab-soft';
      document.head.appendChild(s); return s;
    })();
    var pill = S.rpill > 99 ? 999 : S.rpill;
    el.textContent =
      '.md-typeset .admonition,.md-typeset details{border-radius:' + S.rbox + 'px;border-width:' + S.bw + 'px}' +
      '.md-typeset .gate{border-radius:' + (S.rbox + 2) + 'px;border-width:' + S.bw + 'px}' +
      '.md-typeset .tbc{border-radius:' + pill + 'px;border-width:' + S.bw + 'px}' +
      '.md-typeset .gate__input,.md-typeset .gate__btn{border-radius:' + S.rctl + 'px}' +
      '.md-typeset table:not([class]) td,.md-typeset table:not([class]) th{border-bottom-width:' + S.bw + 'px}' +
      '.md-typeset h2{border-top-width:' + S.bw + 'px;margin-top:' + (3 * S.scale).toFixed(2) + 'rem;padding-top:' + (1.5 * S.scale).toFixed(2) + 'rem}' +
      '.md-typeset h3{margin-top:' + (1.75 * S.scale).toFixed(2) + 'rem}' +
      '.md-typeset p{margin-bottom:' + (1 * S.scale).toFixed(2) + 'rem}';
  }

  function cssBlock() {
    var P   = 'oklch(' + S.lig + '% ' + S.chr + ' ' + S.hue + ')';
    var A   = 'oklch(' + Math.max(24, S.lig - 4) + '% ' + (S.chr + 0.01).toFixed(3) + ' ' + S.hue + ')';
    var PB  = 'oklch(99% 0.003 ' + S.hue + ')';
    var BG  = 'oklch(' + S.plig + '% 0.006 ' + S.nhue + ')';
    var TX  = 'oklch(' + S.tlig + '% 0.014 ' + S.nhue + ')';
    var INK = 'oklch(' + Math.max(14, S.tlig - 20) + '% 0.018 ' + S.nhue + ')';
    var LT  = 'oklch(' + Math.min(72, S.tlig + 17) + '% 0.012 ' + S.nhue + ')';
    var RL  = 'oklch(' + S.rlig + '% 0.008 ' + S.nhue + ')';
    var AM  = 'oklch(52% 0.12 ' + S.ahue + ')';
    var fam = '"' + S.serif + '", ' +
      (/Grotesk|DM Sans/.test(S.serif) ? 'system-ui, sans-serif' : 'Georgia, serif');
    var pill = S.rpill > 99 ? 999 : S.rpill;

    return '@import url("https://fonts.googleapis.com/css2?family=' +
      S.serif.replace(/ /g, '+') + ':' + FONTS[S.serif] + '&display=swap");\n' +
'/* ^ MUST stay line 1. CSS silently drops any @import that follows another rule. */\n\n' +
'/* -- PALETTE. Change these six values and the whole site follows. ---------- */\n' +
':root, [data-md-color-primary=custom], [data-md-color-accent=custom] {\n' +
'  --md-primary-fg-color: ' + P + ';\n' +
'  --md-accent-fg-color:  ' + A + ';\n' +
'  --md-primary-bg-color: ' + PB + ';\n' +
'  --md-typeset-a-color:  ' + P + ';\n' +
'  --md-default-bg-color: ' + BG + ';\n' +
'  --md-typeset-color:    ' + TX + ';\n\n' +
'  --md-default-fg-color:           ' + INK + ';\n' +
'  --md-default-fg-color--light:    ' + LT + ';\n' +
'  --md-default-fg-color--lightest: ' + RL + ';\n\n' +
'  --serif: ' + fam + ';\n' +
'  --amber: ' + AM + ';\n' +
'}\n\n' +
'/* -- SOFTNESS ------------------------------------------------------------- */\n' +
'.md-typeset .admonition,\n.md-typeset details { border-radius: ' + S.rbox + 'px; border-width: ' + S.bw + 'px; }\n' +
'.md-typeset .gate  { border-radius: ' + (S.rbox + 2) + 'px; border-width: ' + S.bw + 'px; }\n' +
'.md-typeset .tbc   { border-radius: ' + pill + 'px; border-width: ' + S.bw + 'px; }\n' +
'.md-typeset .gate__input,\n.md-typeset .gate__btn { border-radius: ' + S.rctl + 'px; }\n' +
'.md-typeset table:not([class]) td,\n.md-typeset table:not([class]) th { border-bottom-width: ' + S.bw + 'px; }\n\n' +
'/* -- RHYTHM --------------------------------------------------------------- */\n' +
'.md-typeset h2 { border-top-width: ' + S.bw + 'px; margin-top: ' + (3 * S.scale).toFixed(2) + 'rem; padding-top: ' + (1.5 * S.scale).toFixed(2) + 'rem; }\n' +
'.md-typeset h3 { margin-top: ' + (1.75 * S.scale).toFixed(2) + 'rem; }\n' +
'.md-typeset p  { margin-bottom: ' + (1 * S.scale).toFixed(2) + 'rem; }\n';
  }

  /* ── dock ──────────────────────────────────────────────────────────────── */

  function build() {
    var d = document.createElement('div');
    d.id = 'lab';
    d.innerHTML =
      '<button class="lab__tab" id="labTab" title="Theme Lab">Theme</button>' +
      '<div class="lab__panel" id="labPanel" hidden>' +
        '<header class="lab__hd"><b>Theme Lab</b>' +
          '<span class="lab__local">this browser only</span>' +
          '<button class="lab__x" id="labX" title="Collapse">&times;</button>' +
        '</header>' +
        '<div class="lab__scroll">' +
          '<p class="lab__lbl">Brand</p><div class="lab__chips" id="labChips"></div>' +
          row('hue', 'Hue', 0, 360, 1) +
          row('chr', 'Saturation', 0, 0.24, 0.005) +
          row('lig', 'Darkness', 28, 72, 1) +
          '<p class="lab__lbl">Paper &amp; ink</p>' +
          row('nhue', 'Neutral tint', 0, 360, 1) +
          row('plig', 'Page warmth', 94, 100, 0.2) +
          row('tlig', 'Text contrast', 24, 52, 1) +
          row('rlig', 'Rule contrast', 78, 95, 0.5) +
          '<p class="lab__lbl">Shape</p>' +
          '<div class="lab__f"><label for="labSoft">Corners</label>' +
            '<select id="labSoft">' + Object.keys(SOFT).map(function (k) {
              return '<option value="' + k + '">' + k + '</option>'; }).join('') + '</select></div>' +
          '<div class="lab__f"><label for="labBw">Rule weight</label>' +
            '<select id="labBw"><option value="1">Hairline</option>' +
            '<option value="1.5">Medium</option><option value="2">Heavy</option></select></div>' +
          '<p class="lab__lbl">Type</p>' +
          '<div class="lab__f"><label for="labSerif">Headings</label>' +
            '<select id="labSerif">' + Object.keys(FONTS).map(function (k) {
              return '<option value="' + k + '">' + k + '</option>'; }).join('') + '</select></div>' +
          row('scale', 'Breathing room', 0.7, 1.5, 0.05) +
          '<p class="lab__lbl">Signals</p>' +
          row('ahue', 'Unconfirmed badge', 0, 360, 1) +
          '<div id="labHex" class="lab__hex"></div>' +
        '</div>' +
        '<footer class="lab__ft">' +
          '<button class="lab__btn" id="labCopy">Copy CSS</button>' +
          '<a class="lab__btn lab__btn--ghost" href="' + EDIT + '" target="_blank" rel="noopener">Edit file</a>' +
          '<button class="lab__btn lab__btn--quiet" id="labReset">Reset</button>' +
          '<button class="lab__btn lab__btn--quiet" id="labOff">Turn off</button>' +
        '</footer>' +
      '</div>';
    document.body.appendChild(d);
    return d;
  }

  function row(k, label, min, max, step) {
    return '<div class="lab__f"><label for="lab_' + k + '">' + label +
      '<i id="v_' + k + '"></i></label>' +
      '<input type="range" id="lab_' + k + '" min="' + min + '" max="' + max +
      '" step="' + step + '"></div>';
  }

  function oklchHex(L, C, H) {
    L = L / 100;
    var h = H * Math.PI / 180, a = C * Math.cos(h), b = C * Math.sin(h);
    var l_ = L + 0.3963377774 * a + 0.2158037573 * b,
        m_ = L - 0.1055613458 * a - 0.0638541728 * b,
        s_ = L - 0.0894841775 * a - 1.2914855480 * b;
    var l = l_ * l_ * l_, m = m_ * m_ * m_, s = s_ * s_ * s_;
    var r  =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        g  = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;
    function enc(v) {
      v = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(Math.max(v, 0), 1 / 2.4) - 0.055;
      return Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, '0');
    }
    return '#' + enc(r) + enc(g) + enc(bb);
  }

  function init() {
    if (localStorage.getItem(FLAG) !== '1') { apply(); return; }

    var dock = build();
    var panel = document.getElementById('labPanel');
    var tab = document.getElementById('labTab');

    tab.addEventListener('click', function () { panel.hidden = false; tab.hidden = true; });
    document.getElementById('labX').addEventListener('click', function () { panel.hidden = true; tab.hidden = false; });

    document.getElementById('labChips').innerHTML = PRESETS.map(function (p, i) {
      return '<button class="lab__chip" data-i="' + i + '" title="' + p.n + '"' +
        ' style="background:oklch(' + p.l + '% ' + p.c + ' ' + p.h + ')"></button>';
    }).join('');

    dock.querySelectorAll('.lab__chip').forEach(function (c) {
      c.addEventListener('click', function () {
        var p = PRESETS[+c.dataset.i];
        S.hue = p.h; S.chr = p.c; S.lig = p.l; S.nhue = p.nh;
        sync(); save(); apply();
      });
    });

    ['hue', 'chr', 'lig', 'nhue', 'plig', 'tlig', 'rlig', 'scale', 'ahue'].forEach(function (k) {
      document.getElementById('lab_' + k).addEventListener('input', function (e) {
        S[k] = +e.target.value; save(); apply();
      });
    });

    document.getElementById('labSoft').addEventListener('change', function (e) {
      var v = SOFT[e.target.value];
      S.rbox = v[0]; S.rpill = v[1]; S.rctl = v[2]; save(); apply();
    });
    document.getElementById('labBw').addEventListener('change', function (e) {
      S.bw = +e.target.value; save(); apply();
    });
    document.getElementById('labSerif').addEventListener('change', function (e) {
      S.serif = e.target.value; save(); apply();
    });

    document.getElementById('labCopy').addEventListener('click', function (e) {
      navigator.clipboard.writeText(cssBlock());
      e.target.textContent = 'Copied';
      setTimeout(function () { e.target.textContent = 'Copy CSS'; }, 1500);
    });
    document.getElementById('labReset').addEventListener('click', function () {
      for (var k in DEFAULTS) S[k] = DEFAULTS[k];
      sync(); save(); apply();
    });
    document.getElementById('labOff').addEventListener('click', function () {
      localStorage.removeItem(FLAG); localStorage.removeItem(SAVE);
      location.reload();
    });

    /* repaint readouts + swatches on every change */
    window.__labPaint = function () {
      set('hue', S.hue); set('chr', S.chr.toFixed(3)); set('lig', S.lig + '%');
      set('nhue', S.nhue); set('plig', S.plig.toFixed(1) + '%');
      set('tlig', S.tlig + '%'); set('rlig', S.rlig.toFixed(1) + '%');
      set('scale', S.scale.toFixed(2) + '\u00d7'); set('ahue', S.ahue);

      document.getElementById('labHex').innerHTML = [
        ['Brand', oklchHex(S.lig, S.chr, S.hue)],
        ['Badge', oklchHex(52, 0.12, S.ahue)],
        ['Page',  oklchHex(S.plig, 0.006, S.nhue)],
        ['Text',  oklchHex(S.tlig, 0.014, S.nhue)],
        ['Rules', oklchHex(S.rlig, 0.008, S.nhue)]
      ].map(function (p) {
        return '<button class="lab__hexrow" data-h="' + p[1] + '">' +
          '<span style="background:' + p[1] + '"></span>' + p[0] +
          '<code>' + p[1] + '</code></button>';
      }).join('');

      document.querySelectorAll('.lab__hexrow').forEach(function (b) {
        b.addEventListener('click', function () {
          navigator.clipboard.writeText(b.dataset.h);
          var c = b.querySelector('code'), o = c.textContent;
          c.textContent = 'copied'; setTimeout(function () { c.textContent = o; }, 900);
        });
      });
    };

    function set(k, v) { var n = document.getElementById('v_' + k); if (n) n.textContent = v; }

    function sync() {
      ['hue', 'chr', 'lig', 'nhue', 'plig', 'tlig', 'rlig', 'scale', 'ahue'].forEach(function (k) {
        document.getElementById('lab_' + k).value = S[k];
      });
      document.getElementById('labBw').value = S.bw;
      document.getElementById('labSerif').value = S.serif;
      for (var name in SOFT) {
        if (SOFT[name][0] === S.rbox) { document.getElementById('labSoft').value = name; break; }
      }
    }

    sync();
    apply();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
