function showToast(message, type = 'success') {
    if (!message) return;

    let container = document.querySelector('[data-toast-container]');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.dataset.toastContainer = 'true';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.setAttribute('role', 'status');
    toast.textContent = message;
    container.appendChild(toast);

    window.setTimeout(() => {
        toast.classList.add('toast--hide');
        toast.addEventListener('transitionend', () => toast.remove(), {once: true});
        window.setTimeout(() => toast.remove(), 500);
    }, 5000);
}

window.showToast = showToast;

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
        showToast(data.message);
        if (!isFavorite && form.dataset.removeCard === 'true') {
            const card = form.closest('.favorite-card');
            const section = form.closest('.account-section');
            if (card) card.remove();
            const counter = section ? section.querySelector('.account-section__heading span') : null;
            if (counter) {
                counter.textContent = String(Math.max(0, Number(counter.textContent || 0) - 1));
            }
        }
    } catch (error) {
        form.submit();
    } finally {
        button.disabled = false;
    }
});

document.addEventListener('submit', async (event) => {
    const form = event.target.closest('.cart-toggle');
    if (!form) {
        return;
    }

    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Не удалось обновить корзину');
        }

        const inCart = Boolean(data.in_cart);
        form.dataset.inCart = String(inCart);
        form.action = inCart ? form.dataset.removeUrl : form.dataset.addUrl;
        if (button) {
            button.textContent = inCart ? 'Удалить из корзины' : 'Добавить в корзину';
        }
        showToast(data.message);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        if (button) button.disabled = false;
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
