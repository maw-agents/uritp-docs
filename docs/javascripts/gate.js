/* Client half of the `status: gated` page gate.
   Server half is hooks/visibility.py. Documented in AUTHORING.md.

   PBKDF2-SHA256 -> AES-256-GCM via Web Crypto. No plaintext is served: a wrong
   password fails to DECRYPT rather than failing a comparison, so there is
   nothing in the page to read around. That only matters once the repo is
   private, since the markdown source is public until then. */

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

  function unlock(password) {
    return crypto.subtle.importKey(
      'raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']
    ).then(function (material) {
      return crypto.subtle.deriveKey(
        { name: 'PBKDF2',
          salt: b64(gate.dataset.salt),
          iterations: parseInt(gate.dataset.iter, 10),
          hash: 'SHA-256' },
        material,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
      );
    }).then(function (key) {
      return crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: b64(gate.dataset.nonce) }, key, b64(gate.dataset.ct)
      );
    }).then(function (plain) {
      return new TextDecoder().decode(plain);
    });
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
