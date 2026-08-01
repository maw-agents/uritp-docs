"""
Envelope encryption, and the markup that asks for the key.

One body ciphertext, one wrapped content key per password. Pure functions: give
them finished HTML and a list of passwords, get back the block that replaces it.

=======================================================================
⚠️⚠️ THIS FILE IS ONE HALF OF A PAIR. THE OTHER HALF IS A BROWSER.
=======================================================================

docs/javascripts/gate.js decrypts what this encrypts. The two share the CIPHER
(AES-GCM), the KDF (PBKDF2-HMAC-SHA256), the ITERATION COUNT, and the shape of
the data- attributes below. They are not merely related, they are one algorithm
written twice in two languages.

🔴 CHANGE THEM IN THE SAME PR OR EVERY GATED PAGE STOPS UNLOCKING, and it will
fail with NO ERROR ANYONE CAN READ -- a wrong key produces a failed auth tag,
which is indistinguishable from a wrong password. The reader sees "that
password did not work" and there is nothing in any log to contradict them.

This warning moved here with ITERATIONS on 2026-08-01. If ITERATIONS ever moves
again, THIS PARAGRAPH MOVES WITH IT. A pairing note left behind in the file the
value used to live in is worse than no note: it tells the next person the pair
is documented somewhere they have already looked.

=======================================================================
WHY AN ENVELOPE AND NOT N COPIES
=======================================================================

A random content key (CEK) encrypts the finished HTML ONCE, then the CEK is
separately encrypted for each password. A wrapped CEK is ~100 bytes, so page
weight is effectively independent of how many groups can open the page. That is
what makes the folder waterfall cheap: a locked child keeps its own password AND
gains its parent's, and the second one costs a hundred bytes rather than a
second copy of the page.

🔒 THE WRAP LIST IS SHUFFLED AND UNLABELLED, deliberately. Which desks can open
a document is itself information, and a stable order would leak it: the same
group would sit in the same slot on every page, so counting and comparing pages
would reconstruct the access map without opening anything. SystemRandom, not
random, because this is a privacy property and not a convenience.

Duplicate passwords are the CALLER's business to dedupe -- two wraps that open
with the same secret would tell an observer those two groups share a password.
hooks/visibility.py does that before calling in.

=======================================================================
WHAT THIS IS NOT
=======================================================================

⚠️ NOT ACCESS CONTROL while the repository is public. The markdown source of
every page, INCLUDING the plaintext of every gated page, is readable at
github.com by anyone who looks. This encrypts the BUILT page. It keeps a casual
reader out of a document they were not handed a password for. It does not keep
anything secret from someone who thinks to look at the repo.

See AUTHORING-GATES.md -> "What the gate actually does". That distinction has
to stay loud, because every part of this file looks like security.

Called only by hooks/visibility.py.
"""

import base64
import random
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 🔴 PAIRED WITH docs/javascripts/gate.js. See the warning above before editing.
ITERATIONS = 250000


def _b64(raw):
    return base64.b64encode(raw).decode()


def _derive(password, salt):
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS
    ).derive(password.encode())


def encrypt(plaintext, passwords):
    """Returns (nonce_b64, ciphertext_b64, wraps).

    `wraps` is a list of {s, n, w} dicts, already shuffled. Any one of the
    given passwords opens the result.
    """
    cek = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(12)
    body = AESGCM(cek).encrypt(nonce, plaintext.encode(), None)

    wraps = []
    for password in passwords:
        salt = secrets.token_bytes(16)
        wrap_nonce = secrets.token_bytes(12)
        wrapped = AESGCM(_derive(password, salt)).encrypt(wrap_nonce, cek, None)
        wraps.append({"s": _b64(salt), "n": _b64(wrap_nonce), "w": _b64(wrapped)})

    random.SystemRandom().shuffle(wraps)
    return _b64(nonce), _b64(body), wraps


def keys_attr(wraps):
    """The wrap list as one base64 attribute value. Built by hand rather than
    with json.dumps so the attribute can never acquire a quote character that
    would break out of the HTML attribute it is about to sit in."""
    parts = [
        '{"s":"' + w["s"] + '","n":"' + w["n"] + '","w":"' + w["w"] + '"}'
        for w in wraps
    ]
    return base64.b64encode(("[" + ",".join(parts) + "]").encode()).decode()


def form(nonce, ciphertext, wraps):
    """The unlock box. gate.js reads every data- attribute here by name."""
    note = (
        "This page is not public. Enter the password you were given, or ask "
        "production management."
    )
    return (
        '<div class="gate" data-nonce="' + nonce + '"'
        ' data-iter="' + str(ITERATIONS) + '"'
        ' data-keys="' + keys_attr(wraps) + '"'
        ' data-ct="' + ciphertext + '">'
        '<form class="gate__form" autocomplete="off">'
        '<p class="gate__label">Restricted page</p>'
        '<p class="gate__note">' + note + '</p>'
        '<div class="gate__row">'
        '<input class="gate__input" type="password" name="gatepw"'
        ' placeholder="Password" aria-label="Page password" required>'
        '<button class="gate__btn" type="submit">Unlock</button>'
        '</div>'
        '<p class="gate__error" hidden>That password did not work.</p>'
        '</form></div>'
    )


def notice(problems):
    """A page whose key is not configured.

    The content is DROPPED, not encrypted and not published: there is no key to
    open it with, so shipping ciphertext nobody can decrypt would only be
    confusing. The page says so plainly rather than pretending to be a lock.
    """
    return (
        '<div class="gate">'
        '<p class="gate__label">Unavailable</p>'
        '<p class="gate__note">This page is restricted and its key has not been '
        'set up yet, so it cannot be opened by anyone. Nothing is missing from '
        'the page itself. Ask production management, or see AUTHORING-GATES.md '
        '&rarr; Adding a key group.</p>'
        '<p class="gate__error">' + "; ".join(problems) + '</p>'
        '</div>'
    )
