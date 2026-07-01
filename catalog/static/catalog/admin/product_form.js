document.addEventListener('DOMContentLoaded', () => {
    const categoryInput = document.getElementById('id_category');
    const photosInput = document.getElementById('id_photos');
    const imagePreview = document.getElementById('product-image-preview');
    const initialPreviewSrc = imagePreview?.getAttribute('src') || '';
    const initialPreviewDisplay = imagePreview?.style.display || '';
    const selectedPhotos = [];
    let nextPhotoId = 1;

    const sizeFields = {
        length: {
            row: document.querySelector('.form-row.field-length_cm'),
            input: document.getElementById('id_length_cm'),
        },
        width: {
            row: document.querySelector('.form-row.field-width_cm'),
            input: document.getElementById('id_width_cm'),
        },
        height: {
            row: document.querySelector('.form-row.field-height_cm'),
            input: document.getElementById('id_height_cm'),
        },
        diameter: {
            row: document.querySelector('.form-row.field-diameter_cm'),
            input: document.getElementById('id_diameter_cm'),
        },
    };

    function addPreviewStyles() {
        if (document.getElementById('selected-product-photos-style')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'selected-product-photos-style';
        style.textContent = `
            .selected-product-photos {
                display: grid;
                gap: 10px;
                margin-top: 12px;
                max-width: 720px;
            }
            .selected-product-photos__item {
                display: grid;
                grid-template-columns: 92px minmax(0, 1fr) auto;
                gap: 12px;
                align-items: center;
                padding: 10px;
                border: 1px solid #d8d8d8;
                border-radius: 4px;
                background: #fff;
            }
            .selected-product-photos__item img {
                width: 92px;
                height: 72px;
                object-fit: cover;
                border-radius: 3px;
                background: #f1f1f1;
            }
            .selected-product-photos__meta {
                display: grid;
                gap: 4px;
                min-width: 0;
            }
            .selected-product-photos__meta strong,
            .selected-product-photos__meta span {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .selected-product-photos__meta small {
                color: #6b7280;
            }
        `;
        document.head.appendChild(style);
    }

    function setField(field, visible, label) {
        if (!field.row) {
            return;
        }
        field.row.hidden = !visible;
        const labelElement = field.row.querySelector('label');
        if (labelElement && label) {
            labelElement.textContent = label;
        }
        if (!visible && field.input) {
            field.input.value = '';
        }
    }

    function updateSizeFields() {
        const category = categoryInput?.value;
        const isPipe = category === 'pipe';
        const hasNoSize = category === 'other';

        setField(
            sizeFields.length,
            !hasNoSize,
            isPipe ? 'Длина одной трубы, см:' : 'Длина, см:',
        );
        setField(sizeFields.width, !isPipe && !hasNoSize, 'Ширина, см:');
        setField(sizeFields.height, !isPipe && !hasNoSize, 'Высота, см:');
        setField(sizeFields.diameter, isPipe, 'Диаметр трубы, см:');
    }

    function syncInputFiles() {
        if (!photosInput) {
            return;
        }
        const dataTransfer = new DataTransfer();
        selectedPhotos.forEach((photo) => dataTransfer.items.add(photo.file));
        photosInput.files = dataTransfer.files;
    }

    function ensureFileList() {
        let list = document.getElementById('selected-product-photos');
        if (list) {
            return list;
        }

        list = document.createElement('div');
        list.id = 'selected-product-photos';
        list.className = 'selected-product-photos';
        photosInput?.insertAdjacentElement('afterend', list);
        return list;
    }

    function updateMainPreview() {
        if (!imagePreview) {
            return;
        }

        if (selectedPhotos.length) {
            imagePreview.src = selectedPhotos[0].previewUrl;
            imagePreview.style.display = 'block';
            return;
        }

        imagePreview.src = initialPreviewSrc;
        imagePreview.style.display = initialPreviewSrc ? initialPreviewDisplay || 'block' : 'none';
    }

    function renderFileList() {
        addPreviewStyles();
        const list = ensureFileList();
        list.replaceChildren();

        if (!selectedPhotos.length) {
            const empty = document.createElement('p');
            empty.textContent = 'Фотографии не выбраны.';
            list.appendChild(empty);
            return;
        }

        selectedPhotos.forEach((photo, index) => {
            const item = document.createElement('div');
            item.className = 'selected-product-photos__item';

            const preview = document.createElement('img');
            preview.src = photo.previewUrl;
            preview.alt = photo.file.name;

            const meta = document.createElement('div');
            meta.className = 'selected-product-photos__meta';

            const name = document.createElement('strong');
            name.textContent = photo.file.name;

            const role = document.createElement('small');
            role.textContent = index === 0 ? 'Основная фотография' : 'Дополнительная фотография';

            const size = document.createElement('span');
            size.textContent = `${Math.ceil(photo.file.size / 1024)} КБ`;

            meta.append(name, role, size);

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'button';
            removeButton.textContent = 'Убрать';
            removeButton.addEventListener('click', () => {
                const photoIndex = selectedPhotos.findIndex((item) => item.id === photo.id);
                if (photoIndex === -1) {
                    return;
                }
                URL.revokeObjectURL(selectedPhotos[photoIndex].previewUrl);
                selectedPhotos.splice(photoIndex, 1);
                syncInputFiles();
                renderFileList();
                updateMainPreview();
            });

            item.append(preview, meta, removeButton);
            list.appendChild(item);
        });
    }

    function addSelectedFiles(files) {
        files.forEach((file) => {
            selectedPhotos.push({
                id: nextPhotoId,
                file,
                previewUrl: URL.createObjectURL(file),
            });
            nextPhotoId += 1;
        });
    }

    categoryInput?.addEventListener('change', updateSizeFields);
    updateSizeFields();

    photosInput?.addEventListener('change', () => {
        const newFiles = Array.from(photosInput.files || []);
        if (!newFiles.length) {
            syncInputFiles();
            renderFileList();
            updateMainPreview();
            return;
        }

        addSelectedFiles(newFiles);
        syncInputFiles();
        renderFileList();
        updateMainPreview();
    });
});
