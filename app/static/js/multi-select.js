/* Multi-select con búsqueda — bottom sheet en mobile, dropdown en desktop */
(function () {
    'use strict';

    function norm(s) { return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
    function isTouch() { return window.matchMedia('(hover: none)').matches; }

    /* ── Singleton bottom sheet ─────────────────────────────── */
    var ssBackdrop = document.createElement('div');
    ssBackdrop.className = 'ss-backdrop';
    var ssSheet = document.createElement('div');
    ssSheet.className = 'ss-sheet';
    ssSheet.innerHTML =
        '<div class="ss-sheet-handle"></div>' +
        '<div class="ss-sheet-header">' +
            '<span class="ss-sheet-title"></span>' +
            '<button type="button" class="ss-sheet-close" aria-label="Cerrar">✕</button>' +
        '</div>' +
        '<div class="ss-sheet-search-wrap">' +
            '<input type="text" class="ss-sheet-search" placeholder="Buscar…">' +
        '</div>' +
        '<ul class="ss-sheet-list"></ul>';
    document.body.appendChild(ssBackdrop);
    document.body.appendChild(ssSheet);

    var _savedScrollY = 0;

    function lockBodyScroll() {
        _savedScrollY = window.scrollY;
        document.body.style.top = -_savedScrollY + 'px';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';
    }
    function unlockBodyScroll() {
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.width = '';
        window.scrollTo({ top: _savedScrollY, behavior: 'instant' });
    }
    function closeSheet() {
        ssSheet.classList.remove('ss-active');
        ssBackdrop.classList.remove('ss-active');
        unlockBodyScroll();
    }
    ssSheet.querySelector('.ss-sheet-close').addEventListener('click', closeSheet);
    ssBackdrop.addEventListener('click', closeSheet);

    /* ── Init ───────────────────────────────────────────────── */
    window.initMultiSelect = function (containerId, opts) {
        opts = opts || {};
        var container = document.getElementById(containerId);
        if (!container) return;

        var display  = container.querySelector('.ms-display');
        var tagsEl   = container.querySelector('.ms-tags');
        var placeholder = container.querySelector('.ms-placeholder');
        var dropdown = container.querySelector('.ms-dropdown');
        var searchEl = container.querySelector('.ms-search');
        var optEls   = container.querySelectorAll('.ms-option');
        var hiddenWrap = container.querySelector('.ms-hiddens');
        var selected  = {};   // { value: label }

        /* Pre-seleccionar valores iniciales */
        var initial = opts.initial || [];
        initial.forEach(function (val) {
            var opt = container.querySelector('.ms-option[data-value="' + val + '"]');
            if (opt) {
                selected[val] = opt.dataset.label || opt.textContent.trim();
                opt.classList.add('ms-selected');
            }
        });
        renderTags();

        function renderTags() {
            tagsEl.innerHTML = '';
            var keys = Object.keys(selected);
            if (!keys.length) {
                placeholder && tagsEl.appendChild(placeholder);
            } else {
                keys.forEach(function (val) {
                    var tag = document.createElement('span');
                    tag.className = 'ms-tag';
                    tag.innerHTML = selected[val] + '<button type="button" class="ms-tag-remove" data-val="' + val + '">✕</button>';
                    tag.querySelector('.ms-tag-remove').addEventListener('click', function (e) {
                        e.stopPropagation();
                        deselect(val);
                    });
                    tagsEl.appendChild(tag);
                });
            }
            renderHiddens();
        }

        function renderHiddens() {
            hiddenWrap.innerHTML = '';
            Object.keys(selected).forEach(function (val) {
                var inp = document.createElement('input');
                inp.type = 'hidden';
                inp.name = opts.fieldName || 'selected_ids';
                inp.value = val;
                hiddenWrap.appendChild(inp);
            });
        }

        function select(val, label) {
            selected[val] = label;
            var opt = container.querySelector('.ms-option[data-value="' + val + '"]');
            if (opt) opt.classList.add('ms-selected');
            renderTags();
        }

        function deselect(val) {
            delete selected[val];
            var opt = container.querySelector('.ms-option[data-value="' + val + '"]');
            if (opt) opt.classList.remove('ms-selected');
            renderTags();
        }

        function toggleOption(val, label) {
            if (selected[val]) { deselect(val); } else { select(val, label); }
        }

        /* ── Desktop dropdown ───────────────────────────────── */
        function openDropdown() {
            container.classList.add('ms-open');
            if (searchEl) {
                searchEl.value = '';
                filterOpts('');
                setTimeout(function () { searchEl.focus(); }, 50);
            }
        }
        function closeDropdown() { container.classList.remove('ms-open'); }

        display.addEventListener('click', function (e) {
            e.stopPropagation();
            if (isTouch()) { openMobileSheet(); return; }
            container.classList.contains('ms-open') ? closeDropdown() : openDropdown();
        });

        if (searchEl) {
            searchEl.addEventListener('click', function (e) { e.stopPropagation(); });
            searchEl.addEventListener('input', function () { filterOpts(this.value); });
        }

        function filterOpts(term) {
            var t = norm(term.trim());
            optEls.forEach(function (opt) {
                opt.classList.toggle('ms-hidden', t !== '' && !norm(opt.textContent).includes(t));
            });
        }

        optEls.forEach(function (opt) {
            opt.addEventListener('click', function (e) {
                e.stopPropagation();
                toggleOption(opt.dataset.value, opt.dataset.label || opt.textContent.trim());
            });
        });

        document.addEventListener('click', function (e) {
            if (!container.contains(e.target)) closeDropdown();
        });

        /* ── Mobile bottom sheet ────────────────────────────── */
        function openMobileSheet() {
            lockBodyScroll();
            ssSheet.querySelector('.ss-sheet-title').textContent = opts.title || 'Seleccioná';

            var oldSearch = ssSheet.querySelector('.ss-sheet-search');
            var newSearch = oldSearch.cloneNode(true);
            oldSearch.replaceWith(newSearch);
            newSearch.value = '';

            var list = ssSheet.querySelector('.ss-sheet-list');
            list.innerHTML = '';

            optEls.forEach(function (opt) {
                var li = document.createElement('li');
                var isSel = !!selected[opt.dataset.value];
                li.className = 'ss-sheet-option' + (isSel ? ' ss-sheet-selected' : '');
                li.dataset.value = opt.dataset.value;
                var label = opt.dataset.label || opt.textContent.trim();
                li.dataset.label = label;
                li.innerHTML = '<span class="ss-sheet-check">✓</span>' + label;
                li.addEventListener('click', function () {
                    var v = li.dataset.value, l = li.dataset.label;
                    if (selected[v]) {
                        delete selected[v];
                        li.classList.remove('ss-sheet-selected');
                        var o = container.querySelector('.ms-option[data-value="' + v + '"]');
                        if (o) o.classList.remove('ms-selected');
                    } else {
                        selected[v] = l;
                        li.classList.add('ss-sheet-selected');
                        var o2 = container.querySelector('.ms-option[data-value="' + v + '"]');
                        if (o2) o2.classList.add('ms-selected');
                    }
                    renderTags();
                });
                list.appendChild(li);
            });

            newSearch.addEventListener('input', function () {
                var t = norm(this.value.trim());
                list.querySelectorAll('.ss-sheet-option').forEach(function (li) {
                    li.classList.toggle('ss-sheet-hidden', t !== '' && !norm(li.dataset.label).includes(t));
                });
            });

            ssBackdrop.classList.add('ss-active');
            requestAnimationFrame(function () { ssSheet.classList.add('ss-active'); });
        }
    };
})();
