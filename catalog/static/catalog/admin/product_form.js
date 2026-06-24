document.addEventListener('DOMContentLoaded', () => {
    const categoryInput = document.getElementById('id_category');
    const imageInput = document.getElementById('id_image');
    const imagePreview = document.getElementById('product-image-preview');

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

    categoryInput?.addEventListener('change', updateSizeFields);
    updateSizeFields();

    imageInput?.addEventListener('change', () => {
        const [file] = imageInput.files;
        if (!file || !imagePreview) {
            return;
        }
        imagePreview.src = URL.createObjectURL(file);
        imagePreview.style.display = 'block';
    });
});
