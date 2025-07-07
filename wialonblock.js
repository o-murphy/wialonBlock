(function () {
    // Функція для створення SVG іконки (інформаційна іконка)
    function createInfoIcon(unitName, unitId, clickable = true) {
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');

        icon.style.cssText = 'width: 20px; height: 20px; display: block; margin: 0 auto;';
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
        path.setAttribute('d', 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z');

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

    // Застосування стилів для іконки та її контейнера <td>
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

    // --- Модифікації для елементів <col> та заголовка таблиці ---

    // Функція для оновлення <col> елементів в заданій таблиці
    function updateColElements(tableId) {
        const table = document.getElementById(tableId);
        if (!table) {
            console.warn(`Таблиця з ID "${tableId}" не знайдена.`);
            return;
        }

        let colgroup = table.querySelector('colgroup');
        if (!colgroup) {
            // Якщо colgroup не існує, створюємо його та додаємо на початок таблиці
            colgroup = document.createElement('colgroup');
            table.prepend(colgroup);
        }

        // Отримуємо всі <col> елементи, які є прямими дітьми таблиці (або colgroup)
        // та переміщуємо їх всередину colgroup, якщо вони ще не там.
        const existingColsInTableRoot = Array.from(table.children).filter(child => child.tagName === 'COL');

        if (existingColsInTableRoot.length > 0) {
            existingColsInTableRoot.forEach(col => {
                colgroup.appendChild(col); // Переміщуємо <col> всередині <colgroup>
            });
        }

        const cols = Array.from(colgroup.querySelectorAll('col')); // Тепер всі <col> елементи належать colgroup
        let filterColIndex = -1;

        // Знаходимо індекс <col> з класом 'monitoring_units_custom_filter_col'
        for (let i = 0; i < cols.length; i++) {
            if (cols[i].classList.contains('monitoring_units_custom_filter_col')) {
                filterColIndex = i;
                break;
            }
        }

        if (filterColIndex !== -1) {
            // Колонка, span якої потрібно збільшити, знаходиться одразу після filterCol
            const colToIncrementSpan = cols[filterColIndex + 1];

            // Перевіряємо, чи вже збільшений span (для ідемпотентності)
            if (colToIncrementSpan && colToIncrementSpan.hasAttribute('span')) {
                const currentSpan = parseInt(colToIncrementSpan.getAttribute('span'));
                // Якщо span вже більший за початкове значення (6), вважаємо, що він вже скоригований.
                // Можна використовувати `if (currentSpan > 6)` якщо ви знаєте початкове значення span.
                // Або перевіряти на конкретне значення, наприклад, `if (currentSpan === 7)`
                if (currentSpan === 7) { // Припускаємо, що початкове значення 6, і ми очікуємо 7
                    return; // Span вже збільшено, виходимо
                }
            }

            // Ми НЕ додаємо новий елемент <col width="22px" class="monitoring_units_info_col">
            // Замість цього, лише збільшуємо span існуючої наступної колонки.

            // Збільшуємо span для конкретного елемента <col>, який йде після колонки фільтра
            // Це <col width="27px" span="6">, яка знаходиться за індексом filterColIndex + 1
            if (filterColIndex + 1 < cols.length) {
                const targetCol = cols[filterColIndex + 1];
                if (targetCol.hasAttribute('span')) {
                    const currentSpan = parseInt(targetCol.getAttribute('span')) || 1;
                    targetCol.setAttribute('span', currentSpan + 1);
                }
            }
        }
    }

    // Оновлюємо <col> елементи для обох таблиць
    updateColElements('monitoring_units_custom_header_table');
    updateColElements('monitoring_units_target');


    // Додаємо неклікабельну іконку в хедер
    const headerRow = document.getElementById('monitoring_units_custom_header');
    if (headerRow) {
        // Перевіряємо, чи вже існує наша іконка (за її mod-атрибутом), щоб уникнути дублювання
        const existingInfoIconHeader = headerRow.querySelector('th[mod="monitoring_units_info_icon_header"]');
        if (!existingInfoIconHeader) { // Додаємо тільки якщо її немає
            const newTh = document.createElement('th');
            newTh.classList.add('monitoring-units-custom-header-td', 'mu-td-with-icon', 'mu-th-non-clickable-icon'); // Додаємо класи для стилів і неклікабельності
            newTh.style.cssText = 'text-align:center; width: 22px;'; // Ширина має відповідати ширині, яку ми "звільнили" збільшенням span
            newTh.setAttribute('mod', 'monitoring_units_info_icon_header');

            // Створюємо неклікабельну іконку (clickable = false)
            const nonClickableIcon = createInfoIcon('Header', 'N/A', false);
            newTh.appendChild(nonClickableIcon);

            // Знаходимо TD, після якого будемо вставляти нову TH
            const targetTdForHeader = headerRow.querySelector('td#monitoring_units_custom_target');
            if (targetTdForHeader) {
                headerRow.insertBefore(newTh, targetTdForHeader.nextElementSibling);
            }
        }
    }
    // --- Кінець модифікацій для елементів <col> та заголовка таблиці ---


    // 1. Знаходимо всі <tr> елементи з класом 'x-monitoring-unit-row'
    const monitoringUnitRows = document.querySelectorAll('tr.x-monitoring-unit-row');

    // 2. Проходимося по кожному знайденому рядку
    monitoringUnitRows.forEach(row => {
        let unitId = 'N/A';
        const rowId = row.id;

        // Витягуємо unitId з id рядка
        if (rowId && rowId.startsWith('monitoring_units_custom_row_')) {
            unitId = rowId.replace('monitoring_units_custom_row_', '');
        }

        // 3. Знаходимо дочірній елемент <td> з класом 'monitoring-unit-name-cell' всередині поточного рядка
        const nameCell = row.querySelector('.monitoring-unit-name-cell');

        if (nameCell) {
            // Перевіряємо, чи вже існує наша іконка (за її mod-атрибутом), щоб уникнути дублювання
            const existingInfoIconCell = row.querySelector('td[mod="monitoring_units_info_icon"]');
            if (existingInfoIconCell) {
                return;
            }

            const unitName = nameCell.textContent.trim();

            // 4. Створюємо клікабельну іконку
            const iconElement = createInfoIcon(unitName, unitId, true);

            // 5. Створюємо нову комірку <td> для іконки
            const iconTableCell = document.createElement('td');
            iconTableCell.classList.add('mu-td-with-icon');
            iconTableCell.style.cssText = 'text-align:center;';
            iconTableCell.setAttribute('mod', 'monitoring_units_info_icon');
            iconTableCell.appendChild(iconElement);

            // 6. Вставляємо нову <td> одразу після комірки з іменем юніта
            row.insertBefore(iconTableCell, nameCell.nextSibling);

        } else {
            console.warn(`Рядок TR з ID "${rowId}" має клас "x-monitoring-unit-row", але не містить дочірньої комірки з класом "monitoring-unit-name-cell".`);
        }
    });
})();