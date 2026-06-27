document.addEventListener('DOMContentLoaded', () => {
    const gallery = document.querySelector('.product-detail__gallery');
    const modal = document.querySelector('[data-gallery-modal]');
    const mainImage = document.querySelector('[data-gallery-main]');
    const modalImage = document.querySelector('[data-gallery-modal-image]');
    const prevButton = document.querySelector('[data-gallery-prev]');
    const nextButton = document.querySelector('[data-gallery-next]');
    const thumbs = Array.from(document.querySelectorAll('[data-gallery-thumb]'));

    if (!gallery || !modal || !mainImage || !modalImage || !thumbs.length) {
        return;
    }

    const photos = thumbs.map((thumb) => ({
        src: thumb.dataset.src,
        alt: thumb.dataset.alt || '',
    }));
    let currentIndex = Math.max(
        0,
        thumbs.findIndex((thumb) => thumb.classList.contains('product-detail__thumb--active')),
    );

    const normalizeIndex = (index) => {
        if (index < 0) {
            return photos.length - 1;
        }
        if (index >= photos.length) {
            return 0;
        }
        return index;
    };

    const renderPhoto = (index, syncMainImage = true) => {
        currentIndex = normalizeIndex(index);
        const photo = photos[currentIndex];

        if (syncMainImage) {
            mainImage.src = photo.src;
            mainImage.alt = photo.alt;
        }

        if (!modal.hidden) {
            modalImage.src = photo.src;
            modalImage.alt = photo.alt;
        }

        thumbs.forEach((thumb, thumbIndex) => {
            thumb.classList.toggle('product-detail__thumb--active', thumbIndex === currentIndex);
        });
    };

    const openModal = () => {
        modal.hidden = false;
        renderPhoto(currentIndex, false);
        document.body.classList.add('gallery-modal-open');
    };

    const closeModal = () => {
        modal.hidden = true;
        modalImage.removeAttribute('src');
        document.body.classList.remove('gallery-modal-open');
    };

    const showPrevious = (event) => {
        event?.stopPropagation();
        renderPhoto(currentIndex - 1);
    };

    const showNext = (event) => {
        event?.stopPropagation();
        renderPhoto(currentIndex + 1);
    };

    gallery.addEventListener('click', (event) => {
        const thumb = event.target.closest('[data-gallery-thumb]');
        if (!thumb) {
            return;
        }
        renderPhoto(thumbs.indexOf(thumb));
    });

    document.querySelector('[data-gallery-open]')?.addEventListener('click', openModal);
    prevButton?.addEventListener('click', showPrevious);
    nextButton?.addEventListener('click', showNext);
    modal.querySelectorAll('[data-gallery-close]').forEach((button) => {
        button.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', (event) => {
        if (modal.hidden) {
            return;
        }
        if (event.key === 'Escape') {
            closeModal();
        }
        if (event.key === 'ArrowLeft') {
            showPrevious(event);
        }
        if (event.key === 'ArrowRight') {
            showNext(event);
        }
    });
});
