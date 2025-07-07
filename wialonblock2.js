(function () {
    // --- Constants ---
    const ICON_SVG_PATH = 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    const ICON_BASE_STYLE = 'width: 20px; height: 20px; display: block; margin: 0 auto;';

    // --- Utility Functions ---

    /**
     * Створює SVG іконку інформації.
     * @param {string} unitName - Назва юніта, для якого створюється іконка.
     * @param {string} unitId - ID юніта.
     * @param {boolean} clickable - Чи повинна іконка бути клікабельною.
     * @returns {SVGElement} Створений SVG елемент іконки.
     */
    function createInfoIcon(unitName, unitId, clickable = true) {
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.style.cssText = ICON_BASE_STYLE;
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

        if (clickable) {
            icon.style.cursor = 'pointer';
        }

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('d', ICON_SVG_PATH);

        icon.appendChild(path);

        if (clickable) {
            icon.addEventListener('click', (event) => {
                event.stopPropagation();
                console.log(`Інфо-іконка натиснута для Юніта: "${unitName}" (ID: ${unitId})`);
                // Тут можна викликати функцію для показу кастомного модального вікна
            });
        }

        return icon;
    }

    /**
     * Впроваджує CSS-стилі для іконок у <head> документа.
     */
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .mu-td-with-icon svg {
                color: #3b82f6;
                transition: transform 0.2s ease-in-out, color 0.2s ease-in-out;
            }
            .mu-td-with-icon svg:hover {
                transform: scale(1.1);
                color: #2563eb;
            }
            /* Стилі для неклікабельної іконки в хедері */
            .mu-th-non-clickable-icon svg {
                color: #9ca3af; /* Сірий колір для неактивної іконки */
                cursor: default; /* Курсор за замовчуванням */
                transition: none; /* Прибираємо transition для неклікабельних іконок */
            }
            .mu-th-non-clickable-icon svg:hover {
                transform: none; /* Прибираємо трансформацію при наведенні */
                color: #9ca3af; /* Зберігаємо сірий колір при наведенні */
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Оновлює елементи <col> в заданій таблиці: переміщує їх в colgroup
     * та збільшує span відповідної колонки після колонки фільтра.
     * @param {string} tableId - ID таблиці, яку потрібно оновити.
     */
    function updateColElements(tableId) {
        const table = document.getElementById(tableId);
        if (!table) {
            console.warn(`Таблиця з ID "${tableId}" не знайдена.`);
            return;
        }

        let colgroup = table.querySelector('colgroup');
        if (!colgroup) {
            colgroup = document.createElement('colgroup');
            table.prepend(colgroup);
        }

        const existingColsInTableRoot = Array.from(table.children).filter(child => child.tagName === 'COL');
        if (existingColsInTableRoot.length > 0) {
            existingColsInTableRoot.forEach(col => {
                colgroup.appendChild(col);
            });
        }

        const cols = Array.from(colgroup.querySelectorAll('col'));
        let filterColIndex = -1;

        for (let i = 0; i < cols.length; i++) {
            if (cols[i].classList.contains('monitoring_units_custom_filter_col')) {
                filterColIndex = i;
                break;
            }
        }

        if (filterColIndex !== -1) {
            const colToIncrementSpan = cols[filterColIndex + 1];

            if (colToIncrementSpan && colToIncrementSpan.hasAttribute('span')) {
                const currentSpan = parseInt(colToIncrementSpan.getAttribute('span'));
                if (currentSpan === 7) {
                    return;
                }
            }

            if (filterColIndex + 1 < cols.length) {
                const targetCol = cols[filterColIndex + 1];
                if (targetCol.hasAttribute('span')) {
                    const currentSpan = parseInt(targetCol.getAttribute('span')) || 1;
                    targetCol.setAttribute('span', currentSpan + 1);
                }
            }
        }
    }

    /**
     * Додає неклікабельну іконку до хедера таблиці.
     */
    function addHeaderIcon() {
        const headerRow = document.getElementById('monitoring_units_custom_header');
        if (!headerRow) {
            console.warn('Рядок хедера з ID "monitoring_units_custom_header" не знайдено.');
            return;
        }

        const existingInfoIconHeader = headerRow.querySelector('th[mod="monitoring_units_info_icon_header"]');
        if (!existingInfoIconHeader) {
            const newTh = document.createElement('th');
            newTh.classList.add('monitoring-units-custom-header-td', 'mu-td-with-icon', 'mu-th-non-clickable-icon');
            newTh.style.cssText = 'text-align:center; width: 22px;';
            newTh.setAttribute('mod', 'monitoring_units_info_icon_header');

            const nonClickableIcon = createInfoIcon('Header', 'N/A', false);
            newTh.appendChild(nonClickableIcon);

            const targetTdForHeader = headerRow.querySelector('td#monitoring_units_custom_target');
            if (targetTdForHeader) {
                headerRow.insertBefore(newTh, targetTdForHeader.nextElementSibling);
            }
        }
    }

    /**
     * Додає клікабельну іконку до конкретного рядка юніта.
     * @param {HTMLElement} row - Елемент <tr> рядка юніта.
     */
    function addIconToUnitRow(row) {
        let unitId = 'N/A';
        const rowId = row.id;

        if (rowId && rowId.startsWith('monitoring_units_custom_row_')) {
            unitId = rowId.replace('monitoring_units_custom_row_', '');
        }

        const nameCell = row.querySelector('.monitoring-unit-name-cell');

        if (nameCell) {
            const existingInfoIconCell = row.querySelector('td[mod="monitoring_units_info_icon"]');
            if (existingInfoIconCell) {
                return;
            }

            const unitName = nameCell.textContent.trim();
            const iconElement = createInfoIcon(unitName, unitId, true);

            const iconTableCell = document.createElement('td');
            iconTableCell.classList.add('mu-td-with-icon');
            iconTableCell.style.cssText = 'text-align:center;';
            iconTableCell.setAttribute('mod', 'monitoring_units_info_icon');
            iconTableCell.appendChild(iconElement);

            row.insertBefore(iconTableCell, nameCell.nextSibling);

        } else {
            console.warn(`Рядок TR з ID "${rowId}" має клас "x-monitoring-unit-row", але не містить дочірньої комірки з класом "monitoring-unit-name-cell".`);
        }
    }

    /**
     * Перебирає всі рядки юнітів та додає до них іконки.
     */
    function addUnitIcons() {
        const monitoringUnitRows = document.querySelectorAll('tr.x-monitoring-unit-row');
        monitoringUnitRows.forEach(addIconToUnitRow);
    }

    // --- Main Initialization ---
    /**
     * Головна функція для ініціалізації всіх модифікацій таблиці моніторингу.
     */
    function initializeMonitoringTable() {
        injectStyles();
        updateColElements('monitoring_units_custom_header_table');
        updateColElements('monitoring_units_target');
        addHeaderIcon();
        addUnitIcons();
    }

    // Запускаємо ініціалізацію, коли DOM повністю завантажений
    // Або ж, якщо скрипт вбудований в кінець <body>, можна викликати безпосередньо
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeMonitoringTable);
    } else {
        initializeMonitoringTable();
    }

})();