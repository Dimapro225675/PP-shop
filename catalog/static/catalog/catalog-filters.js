(() => {
    const parser = new DOMParser();
    let controller = null;

    const dynamicFormSelector = '[data-dynamic-filter-form]';
    const replaceSelectors = [
        '.catalog-sidebar__filters',
        '.catalog-type-content',
        '.filter-column',
        '.catalog-heading',
        '.product-area',
    ];

    document.documentElement.classList.add('js-enabled');

    function getDynamicForm() {
        return document.querySelector(dynamicFormSelector);
    }

    function setLoading(isLoading) {
        document.body.classList.toggle('catalog-filter-loading', isLoading);
        document.querySelectorAll(dynamicFormSelector).forEach((form) => {
            form.setAttribute('aria-busy', String(isLoading));
        });
    }

    function formUrl(form) {
        const data = new FormData(form);
        data.delete('page');
        const params = new URLSearchParams(data);
        const query = params.toString();
        return `${window.location.pathname}${query ? `?${query}` : ''}`;
    }

    function replaceFromDocument(nextDocument) {
        replaceSelectors.forEach((selector) => {
            const currentElement = document.querySelector(selector);
            const nextElement = nextDocument.querySelector(selector);
            if (currentElement && nextElement) {
                currentElement.replaceWith(nextElement);
            }
        });
        document.title = nextDocument.title;
    }

    async function loadCatalog(url, pushState = true) {
        if (controller) controller.abort();
        controller = new AbortController();
        setLoading(true);

        try {
            const response = await fetch(url, {
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                signal: controller.signal,
            });
            if (!response.ok) throw new Error('Не удалось обновить каталог');

            const html = await response.text();
            const nextDocument = parser.parseFromString(html, 'text/html');
            replaceFromDocument(nextDocument);
            if (pushState) window.history.pushState({}, nextDocument.title, url);
        } catch (error) {
            if (error.name !== 'AbortError' && window.showToast) {
                window.showToast(error.message, 'error');
            }
        } finally {
            setLoading(false);
        }
    }

    document.addEventListener('change', (event) => {
        const form = event.target.closest(dynamicFormSelector);
        if (!form) return;
        loadCatalog(formUrl(form));
    });

    document.addEventListener('submit', (event) => {
        const form = event.target.closest(dynamicFormSelector);
        if (!form) return;
        event.preventDefault();
        loadCatalog(formUrl(form));
    });

    document.addEventListener('click', (event) => {
        const resetLink = event.target.closest('[data-filter-reset]');
        if (resetLink) {
            event.preventDefault();
            loadCatalog(resetLink.href);
            return;
        }

        const paginationLink = event.target.closest('.pagination a');
        if (paginationLink && getDynamicForm()) {
            event.preventDefault();
            loadCatalog(paginationLink.href);
        }
    });

    window.addEventListener('popstate', () => {
        loadCatalog(window.location.href, false);
    });
})();
