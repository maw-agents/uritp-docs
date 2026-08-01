"""
Support libraries for hooks/visibility.py. NOT HOOKS THEMSELVES.

MkDocs only loads what `mkdocs.yml` names under `hooks:`, and it names exactly
one file from this feature: `hooks/visibility.py`. Nothing in this folder is
registered, nothing in here is loaded on its own, and nothing in here should
ever be added to that list.

⚠️ WHY ONE HOOK AND NOT THREE. The hook ORDER in mkdocs.yml is load-bearing and
documented there: visibility.py drops `hidden` pages from the file list BEFORE
links.py builds its id registry, so a link to a hidden page can be recognised
rather than resolving to a 404. Splitting these event handlers across separate
registered hooks would turn one ordering constraint into several, each of them
silent when violated. One feature, one slot in the order.

THE RULE THAT KEEPS THIS SAFE, and it is the only one that matters:

    ALL MUTABLE BUILD STATE LIVES IN hooks/visibility.py.
    EVERYTHING IN HERE IS A PURE FUNCTION OR AN IMMUTABLE HOLDER.

The hook shares seven module-level dicts across six event callbacks. Spread
that state over three files and you get modules disagreeing about what happened
during one build, which is the kind of bug that cannot be found by reading.
These modules take arguments and return values. They remember nothing.

⚠️ THE NAMES IN HERE ARE PUBLIC ON PURPOSE -- no leading underscore. That is
not an oversight and it must not be "tidied". hooks/contrast.py imports five
UNDERSCORED names from hooks/theme.py, and on 2026-08-01 renaming one of them
(`_active`) nearly broke the contrast gate; it was caught by the branch build,
not by a person. A private that another file imports is not private, it is an
undocumented API wearing a misleading name. This seam is an API, so it is
spelled like one.

Import shape, matching the one already proven in hooks/contrast.py -- MkDocs
loads a hook as a standalone module rather than as part of a package, so
relative imports do not work and the hooks directory is put on sys.path first:

    _HOOKS = os.path.dirname(os.path.abspath(__file__))
    if _HOOKS not in sys.path:
        sys.path.insert(0, _HOOKS)
    from gate import envelope, keystore
"""
