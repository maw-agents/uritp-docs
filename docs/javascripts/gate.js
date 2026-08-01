/* Client half of the `status: gated` page gate.
   Server half is hooks/visibility.py. Documented in AUTHORING.md.

   THESE TWO FILES SHARE THE CIPHER, THE KDF AND THE ITERATION COUNT.
   Change one without the other and every gated page fails to unlock with no
   error anyone can read. They move in the same PR, always.

   ENVELOPE UNWRAP
   A page may be openable by several groups (`gates: [psm, admin]`). The build
   encrypts the body ONCE with a random content key, then ships that content
   key wrapped separately for each group. Unlocking is two steps:

     1. try the password against each wrapped key until one unwraps, which
        recovers the content key
     2. decrypt the body with the content key

   A wrong password unwraps nothing and decrypts nothing: it fails to DECRYPT
   rather than failing a comparison, so there is no plaintext in the page to
   read around. That only matters once the repo is private, since the markdown
   source is public until then.

   THE KEYRING (2026-08-01)
   Unlocking is per SESSION, not per page. A password that works anywhere is
   remembered, and every gated page afterwards tries the whole keyring on load
   before showing the form. Unlock the Safety index with the PSM key and every
   other PSM page opens by itself.

   Note what this does NOT require: the page never learns which GROUP a key
   belongs to. The wraps are deliberately unlabelled, so the keyring just
   re-attempts the same trial decryption it would do anyway. Access is proven
   by decryption every single time, never by a remembered "I am PSM" flag that
   a reader could set in devtools.

   Storage is sessionStorage: closing the tab re-locks everything. Deliberately
   NOT localStorage, because a shared machine in a shop or a lab is the normal
   case here.

   Cost: one PBKDF2 derivation (250k iterations, ~100-200ms on a phone) per
   candidate key per wrap, worst case, and it stops at the first success. Three
   groups and two remembered keys is imperceptible. Dozens would not be, which
   is the practical ceiling on both numbers. */

(function () {
  var STORE = 'uritp.gate.keyring';
  var LIMIT = 8;               // keep the worst-case derivation count sane

  var gate = document.querySelector('.gate');
  if (!gate) return;

  var form = gate.querySelector('.gate__form');
  var input = gate.querySelector('.gate__input');
  var button = gate.querySelector('.gate__btn');
  var error = gate.querySelector('.gate__error');

  function b64(s) {
    return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); });
  }

  function keyring() {
    try {
      var held = JSON.parse(sessionStorage.getItem(STORE));
      return Array.isArray(held) ? held : [];
    } catch (e) {
      return [];
    }
  }

  function remember(password) {
    var held = keyring().filter(function (k) { return k !== password; });
    held.unshift(password);                    // most recent first
    try {
      sessionStorage.setItem(STORE, JSON.stringify(held.slice(0, LIMIT)));
    } catch (e) { /* private mode: unlocking still works, just not sticky */ }
  }

  function forget(password) {
    try {
      sessionStorage.setItem(STORE, JSON.stringify(
        keyring().filter(function (k) { return k !== password; })
      ));
    } catch (e) { /* nothing to do */ }
  }

  function wrappedKeys() {
    try {
      return JSON.parse(atob(gate.dataset.keys)) || [];
    } catch (e) {
      return [];
    }
  }

  /* password + this wrap's own salt -> the key that wraps the content key */
  function deriveKek(password, saltB64) {
    return crypto.subtle.importKey(
      'raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']
    ).then(function (material) {
      return crypto.subtle.deriveKey(
        { name: 'PBKDF2',
          salt: b64(saltB64),
          iterations: parseInt(gate.dataset.iter, 10),
          hash: 'SHA-256' },
        material,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
      );
    });
  }

  function decryptBody(cekRaw) {
    return crypto.subtle.importKey(
      'raw', cekRaw, { name: 'AES-GCM' }, false, ['decrypt']
    ).then(function (cek) {
      var iv = b64(gate.dataset.nonce);
      return crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, cek, b64(gate.dataset.ct));
    }).then(function (plain) {
      return new TextDecoder().decode(plain);
    });
  }

  /* One password against every wrap on this page. Sequential on purpose: the
     common case is the first or second wrap, and firing every PBKDF2 in
     parallel would burn a phone's battery to save nothing. */
  function tryPassword(password) {
    var keys = wrappedKeys();

    function attempt(i) {
      if (i >= keys.length) return Promise.reject(new Error('no wrap matched'));
      var entry = keys[i];
      return deriveKek(password, entry.s).then(function (kek) {
        return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(entry.n) }, kek, b64(entry.w));
      }).then(decryptBody).catch(function () {
        return attempt(i + 1);
      });
    }

    return attempt(0);
  }

  /* Every key we already hold, newest first. Resolves with the html AND the
     key that worked, so a stale key can be dropped from the ring. */
  function tryKeyring() {
    var held = keyring();

    function attempt(i) {
      if (i >= held.length) return Promise.reject(new Error('keyring exhausted'));
      return tryPassword(held[i]).then(function (html) {
        return { html: html, key: held[i] };
      }).catch(function () {
        return attempt(i + 1);
      });
    }

    return attempt(0);
  }

  function reveal(html) {
    var host = document.createElement('div');
    host.className = 'gate__revealed';
    host.innerHTML = html;
    gate.replaceWith(host);
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    error.hidden = true;
    button.disabled = true;
    button.textContent = 'Checking';
    var attempt = input.value;
    tryPassword(attempt).then(function (html) {
      remember(attempt);
      reveal(html);
    }).catch(function () {
      error.hidden = false;
      input.value = '';
      input.focus();
      button.disabled = false;
      button.textContent = 'Unlock';
    });
  });

  /* Held a working key already this session? Open without asking. The form
     stays in the DOM until a key actually decrypts, so a failed keyring is
     indistinguishable from arriving cold -- which is correct. */
  if (keyring().length) {
    gate.classList.add('gate--checking');
    tryKeyring().then(function (result) {
      reveal(result.html);
    }).catch(function () {
      gate.classList.remove('gate--checking');
    });
  }
})();
