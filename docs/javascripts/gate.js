/* Client half of the `status: gated` page gate.
   Server half is hooks/visibility.py. Documented in AUTHORING.md.

   THESE TWO FILES SHARE THE CIPHER, THE KDF AND THE ITERATION COUNT.
   Change one without the other and every gated page fails to unlock with no
   error anyone can read. They move in the same PR, always.

   ENVELOPE UNWRAP (2026-08-01)
   A page may be openable by several groups (`gates: [psm, admin]`). The build
   encrypts the body ONCE with a random content key, then ships that content
   key wrapped separately for each group. So unlocking is two steps:

     1. try the typed password against each wrapped key until one unwraps,
        which recovers the content key
     2. decrypt the body with the content key

   A wrong password unwraps nothing and decrypts nothing: it fails to DECRYPT
   rather than failing a comparison, so there is no plaintext in the page to
   read around. That only matters once the repo is private, since the markdown
   source is public until then.

   Cost note: each candidate costs one PBKDF2 derivation (250k iterations,
   roughly 100-200ms on a phone). Three groups is imperceptible. A few dozen
   would not be, and that is the practical ceiling on keys per page. */

(function () {
  var gate = document.querySelector('.gate');
  if (!gate) return;

  var form = gate.querySelector('.gate__form');
  var input = gate.querySelector('.gate__input');
  var button = gate.querySelector('.gate__btn');
  var error = gate.querySelector('.gate__error');
  var storeKey = 'gate:' + location.pathname;

  function b64(s) {
    return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); });
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

  /* Walk the wraps one at a time. Sequential on purpose: the common case is
     the first or second key, and firing every PBKDF2 in parallel would burn a
     phone's battery to save nothing. */
  function unlock(password) {
    var keys = wrappedKeys();

    function attempt(i) {
      if (i >= keys.length) return Promise.reject(new Error('no key matched'));
      var entry = keys[i];
      return deriveKek(password, entry.s).then(function (kek) {
        return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(entry.n) }, kek, b64(entry.w));
      }).then(decryptBody).catch(function () {
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
    unlock(attempt).then(function (html) {
      /* Session only: closing the tab re-locks. Deliberately NOT localStorage,
         because a shared machine in a shop or a lab is the normal case here. */
      sessionStorage.setItem(storeKey, attempt);
      reveal(html);
    }).catch(function () {
      error.hidden = false;
      input.value = '';
      input.focus();
      button.disabled = false;
      button.textContent = 'Unlock';
    });
  });

  /* Already unlocked this session? Skip the form. */
  var remembered = sessionStorage.getItem(storeKey);
  if (remembered) {
    unlock(remembered).then(reveal).catch(function () {
      sessionStorage.removeItem(storeKey);
    });
  }
})();
