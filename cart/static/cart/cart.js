function updateCartSummary(data) {
    const total = document.getElementById('cart-selected-total');
    const count = document.getElementById('selected-product-count');
    const checkoutButton = document.getElementById('checkout-button');

    if (total) total.textContent = data.selected_total;
    if (count) count.textContent = data.selected_count;
    if (checkoutButton) checkoutButton.disabled = !data.has_selected;
}

async function submitCartForm(form) {
    const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {'X-Requested-With': 'XMLHttpRequest'},
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Не удалось обновить корзину');
    }
    return data;
}

document.addEventListener('submit', async (event) => {
    const form = event.target.closest('.cart-remove-form');
    if (!form) return;

    event.preventDefault();
    const item = form.closest('[data-cart-item]');
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;

    try {
        const data = await submitCartForm(form);
        if (item) item.remove();
        updateCartSummary(data);
        if (window.showToast) window.showToast(data.message);
        if (data.cart_empty) {
            window.setTimeout(() => window.location.reload(), 900);
        }
    } catch (error) {
        if (window.showToast) {
            window.showToast(error.message, 'error');
        } else {
            window.alert(error.message);
        }
        if (button) button.disabled = false;
    }
});

document.addEventListener('submit', async (event) => {
    const form = event.target.closest('.quantity-form');
    if (!form) return;

    event.preventDefault();
    const input = form.querySelector('input[name="quantity"]');
    try {
        const data = await submitCartForm(form);
        const item = form.closest('[data-cart-item]');
        item.querySelector('[data-item-total]').textContent = data.item_total;
        updateCartSummary(data);
    } catch (error) {
        window.alert(error.message);
    }
});

document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-quantity-delta]');
    if (!button) return;

    const form = button.closest('.quantity-form');
    const input = form.querySelector('input[name="quantity"]');
    input.value = Math.max(1, Number(input.value || 1) + Number(button.dataset.quantityDelta));
    form.requestSubmit();
});

document.addEventListener('change', async (event) => {
    const selectionInput = event.target.closest('.cart-select-form input[name="selected"]');
    if (selectionInput) {
        const form = selectionInput.form;
        const item = form.closest('[data-cart-item]');
        try {
            const data = await submitCartForm(form);
            item.classList.toggle('cart-item--selected', selectionInput.checked);
            updateCartSummary(data);
        } catch (error) {
            selectionInput.checked = !selectionInput.checked;
            window.alert(error.message);
        }
        return;
    }

    const quantityInput = event.target.closest('.quantity-form input[name="quantity"]');
    if (quantityInput) {
        quantityInput.value = Math.max(1, Number(quantityInput.value || 1));
        quantityInput.form.requestSubmit();
    }
});
