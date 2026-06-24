document.addEventListener('submit', async (event) => {
    const form = event.target.closest('.favorite-toggle');
    if (!form) {
        return;
    }

    event.preventDefault();
    const button = form.querySelector('.favorite-toggle__button');
    button.disabled = true;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();

        if (response.status === 401 && data.login_url) {
            window.location.assign(data.login_url);
            return;
        }
        if (!response.ok) {
            throw new Error('Favorite request failed');
        }

        const isFavorite = data.is_favorite;
        const label = isFavorite ? 'Удалить из избранного' : 'Добавить в избранное';
        button.classList.toggle('favorite-toggle__button--active', isFavorite);
        button.textContent = isFavorite ? '♥' : '♡';
        button.title = label;
        button.setAttribute('aria-label', label);
        button.setAttribute('aria-pressed', String(isFavorite));
    } catch (error) {
        form.submit();
    } finally {
        button.disabled = false;
    }
});

function openProductCard(card) {
    const url = card.dataset.productUrl;
    if (url) {
        window.location.assign(url);
    }
}

document.addEventListener('click', (event) => {
    const card = event.target.closest('[data-product-url]');
    if (!card || event.target.closest('a, button, form, input, select, textarea')) {
        return;
    }
    openProductCard(card);
});

document.addEventListener('keydown', (event) => {
    const card = event.target.closest('[data-product-url]');
    if (!card || (event.key !== 'Enter' && event.key !== ' ')) {
        return;
    }
    event.preventDefault();
    openProductCard(card);
});
