function getElement(id) {
  return document.getElementById(id);
}
function safeText(value) {
  return String(value || "").trim();
}
function normalizeNumberText(value) {
  return safeText(value)
    .replace(/٠/g, "0")
    .replace(/١/g, "1")
    .replace(/٢/g, "2")
    .replace(/٣/g, "3")
    .replace(/٤/g, "4")
    .replace(/٥/g, "5")
    .replace(/٦/g, "6")
    .replace(/٧/g, "7")
    .replace(/٨/g, "8")
    .replace(/٩/g, "9");
}
function toSafeNumber(value) {
  const cleaned = normalizeNumberText(value);
  if (cleaned === "") {
    return 0;
  }
  const numberValue = Number(cleaned);
  return Number.isNaN(numberValue) ? 0 : numberValue;
}
function parseJsonScript(scriptId) {
  const script = getElement(scriptId);
  if (!script) {
    return {};
  }
  try {
    let value = JSON.parse(script.textContent || "{}");
    if (typeof value === "string") {
      try {
        value = JSON.parse(value || "{}");
      } catch (error) {
        return {};
      }
    }
    return value || {};
  } catch (error) {
    console.error("خطأ في قراءة JSON:", scriptId, error);
    return {};
  }
}
function getFieldByName(fieldName) {
  return document.querySelector('[name="' + fieldName + '"]');
}
function getInputByIdOrName(id, name) {
  return getElement(id) || document.querySelector('[name="' + name + '"]');
}
function setFieldValue(field, value) {
  if (!field) {
    return;
  }
  if (field.type === "file") {
    return;
  }
  if (field.type === "checkbox") {
    field.checked = Boolean(value);
    return;
  }
  if (field.type === "radio") {
    field.checked = String(field.value) === String(value);
    return;
  }
  if (field.tagName === "SELECT") {
    const stringValue = String(value || "");
    if (
      stringValue &&
      !Array.from(field.options).some(function (option) {
        return option.value === stringValue;
      })
    ) {
      const option = document.createElement("option");
      option.value = stringValue;
      option.textContent = stringValue;
      field.appendChild(option);
    }
    field.value = stringValue;
    return;
  }
  field.value = value || "";
}
function fireFieldEvents(field) {
  if (!field) {
    return;
  }
  field.dispatchEvent(new Event("input", { bubbles: true }));
  field.dispatchEvent(new Event("change", { bubbles: true }));
}
function setCalculatedField(field, value) {
  if (!field) {
    return;
  }
  field.readOnly = true;
  field.dataset.completionIgnore = "1";
  field.value = value;
}
function formatPercentNumber(value, total) {
  if (!total || total <= 0) {
    return "";
  }
  const percentage = (value / total) * 100;
  return Number.isInteger(percentage)
    ? String(percentage)
    : percentage.toFixed(1);
}
/* ========================================================= Tabs ========================================================= */ function initializeTabs() {
  const tabs = document.querySelectorAll(".aq-tab");
  const panels = document.querySelectorAll(".aq-panel");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (item) {
        item.classList.remove("active");
      });
      panels.forEach(function (panel) {
        panel.classList.remove("active");
      });
      tab.classList.add("active");
      const targetPanelId = tab.getAttribute("data-tab");
      const targetPanel = getElement(targetPanelId);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
      setTimeout(refreshAllCompletionStatuses, 50);
    });
  });
}
/* ========================================================= Program Dialog ========================================================= */ function initializeProgramDialog() {
  const programs = {
    "تقنية معلومات": { startYear: 2011, specialties: [] },
    "تقنية معلومات انجليزي": { startYear: 2019, specialties: [] },
    "نظم معلومات": {
      startYear: null,
      specialties: ["ذكاء أعمال", "أعمال إلكترونية"],
    },
    "أمن سيبراني": { startYear: 2021, specialties: [] },
    "هندسة البرمجيات": { startYear: 2007, specialties: [] },
    "ذكاء اصطناعي": { startYear: 2024, specialties: [] },
  };
  const specialtyYears = { "ذكاء أعمال": 2021, "أعمال إلكترونية": 2021 };
  const currentYear = new Date().getFullYear();
  const programDialog = getElement("programDialog");
  const dialogProgramSelect = getElement("dialogProgramSelect");
  const dialogSpecialtySelect = getElement("dialogSpecialtySelect");
  const dialogYearSelect = getElement("dialogYearSelect");
  const specialtyWrapper = getElement("specialtyWrapper");
  const programNote = getElement("programNote");
  const confirmProgramBtn = getElement("confirmProgramBtn");
  const changeProgramBtn = getElement("changeProgramBtn");
  const selectedProgramText = getElement("selectedProgramText");
  const selectedYearText = getElement("selectedYearText");
  const evaluationFileInput = getElement("evaluationFileInput");
  const selectedProgramInput = getElement("selectedProgramInput");
  const selectedSpecialtyInput = getElement("selectedSpecialtyInput");
  const selectedYearInput = getElement("selectedYearInput");
  const selectedStartYearInput = getElement("selectedStartYearInput");
  const dataEntryForm = getElement("dataEntryForm");
  if (
    !programDialog ||
    !dialogProgramSelect ||
    !dialogSpecialtySelect ||
    !dialogYearSelect ||
    !confirmProgramBtn ||
    !selectedProgramInput ||
    !selectedYearInput
  ) {
    return;
  }
  function resetYearSelect(message) {
    dialogYearSelect.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = message || "اختاري البرنامج أولًا";
    dialogYearSelect.appendChild(option);
    dialogYearSelect.disabled = true;
  }
  function fillYears(startYear, selectedYear) {
    dialogYearSelect.innerHTML = "";
    const firstOption = document.createElement("option");
    firstOption.value = "";
    firstOption.textContent = "اختاري سنة التقييم";
    dialogYearSelect.appendChild(firstOption);
    for (let year = startYear; year <= currentYear; year++) {
      const academicYear = year + "-" + (year + 1);
      const option = document.createElement("option");
      option.value = academicYear;
      option.textContent = academicYear;
      dialogYearSelect.appendChild(option);
    }
    dialogYearSelect.disabled = false;
    if (selectedYear) {
      dialogYearSelect.value = selectedYear;
    }
  }
  function validateProgramSelection() {
    const program = safeText(dialogProgramSelect.value);
    const specialty = safeText(dialogSpecialtySelect.value);
    const year = safeText(dialogYearSelect.value);
    if (!program) {
      confirmProgramBtn.disabled = true;
      return;
    }
    if (program === "نظم معلومات") {
      confirmProgramBtn.disabled = !(specialty && year);
      return;
    }
    confirmProgramBtn.disabled = !year;
  }
  function updateSpecialtyUI(specialtyValue, selectedYearValue) {
    const specialty = safeText(specialtyValue);
    const selectedYear = safeText(selectedYearValue);
    if (!specialty) {
      resetYearSelect("اختاري التخصص أولًا");
      if (programNote) {
        programNote.textContent =
          "اختاري تخصص نظم المعلومات لتظهر سنوات التقييم المتاحة.";
      }
      validateProgramSelection();
      return;
    }
    const startYear = specialtyYears[specialty];
    if (startYear) {
      fillYears(startYear, selectedYear);
      if (programNote) {
        programNote.textContent =
          "سنوات تخصص " +
          specialty +
          " تبدأ من " +
          startYear +
          "-" +
          (startYear + 1) +
          " إلى " +
          currentYear +
          "-" +
          (currentYear + 1) +
          ".";
      }
    } else {
      resetYearSelect("سنة البداية غير محددة");
      if (programNote) {
        programNote.textContent = "لم يتم تحديد سنة بداية هذا التخصص بعد.";
      }
    }
    validateProgramSelection();
  }
  function updateProgramUI(
    programValue,
    selectedYearValue,
    selectedSpecialtyValue,
  ) {
    const program = safeText(programValue);
    const selectedYear = safeText(selectedYearValue);
    const selectedSpecialty = safeText(selectedSpecialtyValue);
    dialogSpecialtySelect.value = "";
    resetYearSelect();
    if (!program || !programs[program]) {
      if (specialtyWrapper) {
        specialtyWrapper.classList.add("hidden");
      }
      if (programNote) {
        programNote.textContent = "لم يتم اختيار برنامج بعد.";
      }
      validateProgramSelection();
      return;
    }
    const programData = programs[program];
    if (programData.specialties.length > 0) {
      if (specialtyWrapper) {
        specialtyWrapper.classList.remove("hidden");
      }
      if (selectedSpecialty) {
        dialogSpecialtySelect.value = selectedSpecialty;
        updateSpecialtyUI(selectedSpecialty, selectedYear);
      } else if (programNote) {
        programNote.textContent =
          "اختاري تخصص نظم المعلومات لتظهر سنوات التقييم المتاحة.";
      }
    } else {
      if (specialtyWrapper) {
        specialtyWrapper.classList.add("hidden");
      }
      if (programData.startYear) {
        fillYears(programData.startYear, selectedYear);
        if (programNote) {
          programNote.textContent =
            "سنوات " +
            program +
            " تبدأ من " +
            programData.startYear +
            "-" +
            (programData.startYear + 1) +
            " إلى " +
            currentYear +
            "-" +
            (currentYear + 1) +
            ".";
        }
      }
    }
    validateProgramSelection();
  }
  function prefillDialogFromCurrentInputs() {
    const currentProgram = safeText(selectedProgramInput.value);
    const currentSpecialty = safeText(
      selectedSpecialtyInput ? selectedSpecialtyInput.value : "",
    );
    const currentYearValue = safeText(selectedYearInput.value);
    if (!currentProgram) {
      return;
    }
    dialogProgramSelect.value = currentProgram;
    updateProgramUI(currentProgram, currentYearValue, currentSpecialty);
  }
  function confirmProgramSelection() {
    const program = safeText(dialogProgramSelect.value);
    const specialty = safeText(dialogSpecialtySelect.value) || "لا يوجد";
    const year = safeText(dialogYearSelect.value);
    if (!program || !year) {
      validateProgramSelection();
      return;
    }
    let startYear = "";
    if (program === "نظم معلومات") {
      startYear = specialtyYears[specialty] || "غير محددة";
    } else {
      startYear = programs[program].startYear || "غير محددة";
    }
    if (selectedProgramText) {
      if (program === "نظم معلومات" && specialty !== "لا يوجد") {
        selectedProgramText.textContent =
          "البرنامج: " + program + " - " + specialty;
      } else {
        selectedProgramText.textContent = "البرنامج: " + program;
      }
    }
    if (selectedYearText) {
      selectedYearText.textContent = "سنة التقييم: " + year;
    }
    if (evaluationFileInput) {
      evaluationFileInput.value = "";
    }
    selectedProgramInput.value = program;
    if (selectedSpecialtyInput) {
      selectedSpecialtyInput.value = specialty;
    }
    selectedYearInput.value = year;
    if (selectedStartYearInput) {
      selectedStartYearInput.value = startYear;
    }
    programDialog.classList.add("hidden");
  }
  dialogProgramSelect.addEventListener("change", function () {
    updateProgramUI(this.value, "", "");
  });
  dialogSpecialtySelect.addEventListener("change", function () {
    updateSpecialtyUI(this.value, "");
  });
  dialogYearSelect.addEventListener("change", validateProgramSelection);
  confirmProgramBtn.addEventListener("click", confirmProgramSelection);
  if (changeProgramBtn) {
    changeProgramBtn.addEventListener("click", function () {
      programDialog.classList.remove("hidden");
      prefillDialogFromCurrentInputs();
    });
  }
  if (dataEntryForm) {
    dataEntryForm.addEventListener("submit", function (event) {
      if (
        !safeText(selectedProgramInput.value) ||
        !safeText(selectedYearInput.value)
      ) {
        event.preventDefault();
        programDialog.classList.remove("hidden");
        prefillDialogFromCurrentInputs();
      }
    });
  }
  prefillDialogFromCurrentInputs();
}
/* ========================================================= Editable Tables ========================================================= */ function refreshRowNumbers(
  table,
) {
  if (!table) {
    return;
  }
  table.querySelectorAll("tbody tr").forEach(function (row, index) {
    const numberCell = row.querySelector(".row-number");
    if (numberCell) {
      numberCell.textContent = index + 1;
    }
  });
}
function clearTableBody(table) {
  const tbody = table ? table.querySelector("tbody") : null;
  if (tbody) {
    tbody.innerHTML = "";
  }
}
function getFieldValueFromRowData(rowData, fieldName, fieldIndex) {
  if (Array.isArray(rowData)) {
    return rowData[fieldIndex] || "";
  }
  if (rowData && typeof rowData === "object") {
    const cleanName = String(fieldName || "").replace(/\[\]$/, "");
    if (Object.prototype.hasOwnProperty.call(rowData, fieldName)) {
      return rowData[fieldName];
    }
    if (Object.prototype.hasOwnProperty.call(rowData, cleanName)) {
      return rowData[cleanName];
    }
    if (Object.prototype.hasOwnProperty.call(rowData, fieldIndex)) {
      return rowData[fieldIndex];
    }
  }
  return "";
}
function updateAdmissionCriteriaRowspan() {
  const table = getElement("admissionCriteriaTable");
  if (!table) {
    return;
  }
  const tbody = table.querySelector("tbody");
  const capacityCell = getElement("admissionCapacityCell");
  if (!tbody || !capacityCell) {
    return;
  }
  capacityCell.rowSpan = tbody.querySelectorAll("tr").length;
}
function getAdmissionCriterionValue(rowData) {
  if (Array.isArray(rowData)) {
    if (rowData.length >= 3 && /^\d+$/.test(safeText(rowData[0]))) {
      return rowData[1] || "";
    }
    return rowData[0] || "";
  }
  if (rowData && typeof rowData === "object") {
    return (
      rowData["admission_criteria[]"] ||
      rowData.admission_criteria ||
      rowData.criterion ||
      ""
    );
  }
  return "";
}
function fillAdmissionCriteriaTableFromRows(rows) {
  const table = getElement("admissionCriteriaTable");
  if (!table) {
    return;
  }
  const tbody = table.querySelector("tbody");
  if (!tbody) {
    return;
  }
  const oldCapacityField = table.querySelector('[name="admission_capacity"]');
  const capacityValue = oldCapacityField ? oldCapacityField.value : "";
  const cleanRows = Array.isArray(rows)
    ? rows
        .map(function (rowData) {
          return getAdmissionCriterionValue(rowData);
        })
        .filter(function (value) {
          return safeText(value) !== "";
        })
    : [];
  const rowCount = Math.max(3, cleanRows.length);
  tbody.innerHTML = "";
  for (let index = 0; index < rowCount; index++) {
    const row = document.createElement("tr");
    const numberCell = document.createElement("td");
    numberCell.className = "row-number";
    numberCell.textContent = index + 1;
    row.appendChild(numberCell);
    const criteriaCell = document.createElement("td");
    const criteriaInput = document.createElement("input");
    criteriaInput.type = "text";
    criteriaInput.name = "admission_criteria[]";
    criteriaInput.value = cleanRows[index] || "";
    criteriaCell.appendChild(criteriaInput);
    row.appendChild(criteriaCell);
    if (index === 0) {
      const capacityCell = document.createElement("td");
      capacityCell.className = "admission-capacity-cell";
      capacityCell.id = "admissionCapacityCell";
      capacityCell.rowSpan = rowCount;
      const capacityTextarea = document.createElement("textarea");
      capacityTextarea.name = "admission_capacity";
      capacityTextarea.rows = 8;
      capacityTextarea.value = capacityValue;
      capacityCell.appendChild(capacityTextarea);
      row.appendChild(capacityCell);
    }
    tbody.appendChild(row);
  }
  updateAdmissionCriteriaRowspan();
  refreshRowNumbers(table);
  refreshCardAfterTableChange(table);
}
function fillTableFromRows(tableId, rows) {
  if (tableId === "admissionCriteriaTable") {
    fillAdmissionCriteriaTableFromRows(rows);
    return;
  }
  const table = getElement(tableId);
  if (!table || !Array.isArray(rows) || rows.length === 0) {
    return;
  }
  const tbody = table.querySelector("tbody");
  const templateRow = tbody ? tbody.querySelector("tr") : null;
  if (!tbody || !templateRow) {
    return;
  }
  const templateClone = templateRow.cloneNode(true);
  const templateFields = Array.from(
    templateClone.querySelectorAll("input, select, textarea"),
  );
  clearTableBody(table);
  rows.forEach(function (rowData) {
    const newRow = templateClone.cloneNode(true);
    const fields = Array.from(
      newRow.querySelectorAll("input, select, textarea"),
    );
    fields.forEach(function (field, index) {
      const templateField = templateFields[index];
      const value = getFieldValueFromRowData(
        rowData,
        templateField ? templateField.name : field.name,
        index,
      );
      setFieldValue(field, value);
    });
    tbody.appendChild(newRow);
  });
  refreshRowNumbers(table);
  if (tableId === "studentsLevelsTable") {
    initializeStudentLevelsAutoTotals();
  }
  if (tableId === "graduatesTable") {
    initializeGraduatesAutoTotals();
  }
  if (
    tableId === "classroomsDataTable" ||
    tableId === "labsDataTable" ||
    tableId === "classroomsCriteriaTable" ||
    tableId === "labsCriteriaTable"
  ) {
    setTimeout(calculatePhysicalEnvironmentCriteria, 50);
  }
  refreshCardAfterTableChange(table);
}
function refreshCardAfterTableChange(table) {
  const card = table ? table.closest(".aq-card") : null;
  if (card) {
    bindCompletionEventsForCard(card);
    updateCardCompletionStatus(card);
  }
  refreshAllCompletionStatuses();
}
function addTableRow(tableId) {
  if (tableId === "admissionCriteriaTable") {
    const table = getElement("admissionCriteriaTable");
    const tbody = table ? table.querySelector("tbody") : null;
    if (!table || !tbody) {
      return;
    }
    const newRow = document.createElement("tr");
    const numberCell = document.createElement("td");
    numberCell.className = "row-number";
    newRow.appendChild(numberCell);
    const criteriaCell = document.createElement("td");
    const criteriaInput = document.createElement("input");
    criteriaInput.type = "text";
    criteriaInput.name = "admission_criteria[]";
    criteriaCell.appendChild(criteriaInput);
    newRow.appendChild(criteriaCell);
    tbody.appendChild(newRow);
    refreshRowNumbers(table);
    updateAdmissionCriteriaRowspan();
    refreshCardAfterTableChange(table);
    return;
  }
  const table = getElement(tableId);
  const tbody = table ? table.querySelector("tbody") : null;
  const lastRow = tbody ? tbody.querySelector("tr:last-child") : null;
  if (!table || !tbody || !lastRow) {
    return;
  }
  const newRow = lastRow.cloneNode(true);
  const fields = newRow.querySelectorAll("input, select, textarea");
  fields.forEach(function (field) {
    if (field.tagName === "SELECT") {
      field.selectedIndex = 0;
    } else if (field.type === "checkbox" || field.type === "radio") {
      field.checked = false;
    } else {
      field.value = "";
    }
    delete field.dataset.completionBound;
    delete field.dataset.studentCountBound;
    delete field.dataset.facultySummaryBound;
    delete field.dataset.performanceBound;
    delete field.dataset.physicalBound;
  });
  tbody.appendChild(newRow);
  refreshRowNumbers(table);
  if (tableId === "studentsLevelsTable") {
    initializeStudentLevelsAutoTotals();
  }
  if (tableId === "graduatesTable") {
    initializeGraduatesAutoTotals();
  }
  refreshCardAfterTableChange(table);
}
window.addTableRow = addTableRow;
/* ========================================================= Import Excel / CSV ========================================================= */ function rowHasAnyValue(
  row,
) {
  return row.some(function (cell) {
    return safeText(cell) !== "";
  });
}
function looksLikeHeaderRow(row) {
  const headerWords = [
    "م",
    "اسم",
    "رمز",
    "عدد",
    "العام",
    "المستوى",
    "البند",
    "الحالة",
    "النسبة",
    "المرفق",
    "الشاهد",
    "ملاحظات",
    "متطلبات",
    "الجامعة",
    "الكلية",
    "القسم",
    "البرنامج",
    "المقرر",
    "المؤهل",
    "سنة",
    "تاريخ",
    "المرتبة",
    "نوع",
    "المصدر",
    "العنوان",
    "الوصف",
    "المساحة",
    "التجهيزات",
  ];
  let matchCount = 0;
  row.forEach(function (cell) {
    const text = safeText(cell);
    if (!text) {
      return;
    }
    if (
      headerWords.some(function (word) {
        return text.includes(word);
      })
    ) {
      matchCount += 1;
    }
  });
  return matchCount >= 2;
}
function cleanImportedRows(rows) {
  let cleanedRows = rows.filter(rowHasAnyValue);
  if (cleanedRows.length > 1 && looksLikeHeaderRow(cleanedRows[0])) {
    cleanedRows.shift();
  }
  return cleanedRows;
}
function importCSV(file, tableId) {
  const reader = new FileReader();
  reader.onload = function (event) {
    const text = event.target.result || "";
    let rows = text.split(/\r?\n/).map(function (line) {
      return line.split(",");
    });
    rows = cleanImportedRows(rows);
    fillTableFromRows(tableId, rows);
  };
  reader.readAsText(file, "UTF-8");
}
function importSpreadsheetToTable(event, tableId) {
  const input = event.target;
  const file = input.files && input.files[0];
  if (!file) {
    return;
  }
  const fileName = file.name.toLowerCase();
  if (fileName.endsWith(".csv")) {
    importCSV(file, tableId);
    input.value = "";
    return;
  }
  if (typeof XLSX === "undefined") {
    alert(
      "استيراد ملفات Excel يحتاج مكتبة XLSX. تأكدي من اتصال الإنترنت أو استخدمي ملف CSV.",
    );
    input.value = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = function (readerEvent) {
    const data = new Uint8Array(readerEvent.target.result);
    const workbook = XLSX.read(data, { type: "array" });
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) {
      input.value = "";
      return;
    }
    const sheet = workbook.Sheets[firstSheetName];
    let rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });
    rows = cleanImportedRows(rows);
    fillTableFromRows(tableId, rows);
    input.value = "";
  };
  reader.onerror = function () {
    alert("تعذر قراءة الملف. جرّبي حفظه بصيغة CSV أو Excel مرة أخرى.");
    input.value = "";
  };
  reader.readAsArrayBuffer(file);
}
window.importSpreadsheetToTable = importSpreadsheetToTable;
/* ========================================================= Students Totals ========================================================= */ function calculateStudentRowTotal(
  row,
) {
  if (!row) {
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  const maleField = row.querySelector('[name="student_male[]"]');
  const femaleField = row.querySelector('[name="student_female[]"]');
  const totalField = row.querySelector('[name="student_total[]"]');
  if (!maleField || !femaleField || !totalField) {
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  totalField.readOnly = true;
  totalField.dataset.completionIgnore = "1";
  const maleRaw = normalizeNumberText(maleField.value);
  const femaleRaw = normalizeNumberText(femaleField.value);
  const hasValue = maleRaw !== "" || femaleRaw !== "";
  if (!hasValue) {
    totalField.value = "";
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  const male = toSafeNumber(maleField.value);
  const female = toSafeNumber(femaleField.value);
  const total = male + female;
  totalField.value = total;
  return { male: male, female: female, total: total, hasValue: true };
}
function calculateAllStudentTotals() {
  const table = getElement("studentsLevelsTable");
  if (!table) {
    return;
  }
  const rows = table.querySelectorAll("tbody tr");
  let maleGrandTotal = 0;
  let femaleGrandTotal = 0;
  let grandTotal = 0;
  let hasAnyValue = false;
  rows.forEach(function (row) {
    const result = calculateStudentRowTotal(row);
    if (result.hasValue) {
      hasAnyValue = true;
    }
    maleGrandTotal += result.male;
    femaleGrandTotal += result.female;
    grandTotal += result.total;
  });
  setCalculatedField(
    getInputByIdOrName("studentsMaleGrandTotal", "students_male_grand_total"),
    hasAnyValue ? maleGrandTotal : "",
  );
  
  setCalculatedField(
    getInputByIdOrName(
      "studentsFemaleGrandTotal",
      "students_female_grand_total",
    ),
    
    hasAnyValue ? femaleGrandTotal : "",
  );
  setCalculatedField(
    getInputByIdOrName("studentsGrandTotal", "students_grand_total"),
    hasAnyValue ? grandTotal : "",
  );
  if (window.calculatePhysicalEnvironmentCriteria) {
    window.calculatePhysicalEnvironmentCriteria();
}
  refreshCardAfterTableChange(table);
  calculatePhysicalEnvironmentCriteria();
}
function initializeStudentLevelsAutoTotals() {
  const table = getElement("studentsLevelsTable");
  if (!table) {
    return;
  }
  table.querySelectorAll('[name="student_total[]"]').forEach(function (field) {
    field.readOnly = true;
    field.dataset.completionIgnore = "1";
  });
  calculateAllStudentTotals();
}
window.calculateAllStudentTotals = calculateAllStudentTotals;
window.initializeStudentLevelsAutoTotals = initializeStudentLevelsAutoTotals;
/* ========================================================= Graduates Totals ========================================================= */ function calculateGraduateRowTotal(
  row,
) {
  if (!row) {
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  const maleField = row.querySelector('[name="graduates_male[]"]');
  const femaleField = row.querySelector('[name="graduates_female[]"]');
  const totalField = row.querySelector('[name="graduates_total[]"]');
  if (!maleField || !femaleField || !totalField) {
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  totalField.readOnly = true;
  totalField.dataset.completionIgnore = "1";
  const maleRaw = normalizeNumberText(maleField.value);
  const femaleRaw = normalizeNumberText(femaleField.value);
  const hasValue = maleRaw !== "" || femaleRaw !== "";
  if (!hasValue) {
    totalField.value = "";
    return { male: 0, female: 0, total: 0, hasValue: false };
  }
  const male = toSafeNumber(maleField.value);
  const female = toSafeNumber(femaleField.value);
  const total = male + female;
  totalField.value = total;
  return { male: male, female: female, total: total, hasValue: true };
}
function calculateAllGraduateTotals() {
  const table = getElement("graduatesTable");
  if (!table) {
    return;
  }
  const rows = table.querySelectorAll("tbody tr");
  let maleGrandTotal = 0;
  let femaleGrandTotal = 0;
  let grandTotal = 0;
  let hasAnyValue = false;
  rows.forEach(function (row) {
    const result = calculateGraduateRowTotal(row);
    if (result.hasValue) {
      hasAnyValue = true;
    }
    maleGrandTotal += result.male;
    femaleGrandTotal += result.female;
    grandTotal += result.total;
  });
  setCalculatedField(
    getInputByIdOrName("graduatesMaleGrandTotal", "graduates_male_grand_total"),
    hasAnyValue ? maleGrandTotal : "",
  );
  setCalculatedField(
    getInputByIdOrName(
      "graduatesFemaleGrandTotal",
      "graduates_female_grand_total",
    ),
    hasAnyValue ? femaleGrandTotal : "",
  );
  setCalculatedField(
    getInputByIdOrName("graduatesGrandTotal", "graduates_grand_total"),
    hasAnyValue ? grandTotal : "",
  );
  refreshCardAfterTableChange(table);
}
function initializeGraduatesAutoTotals() {
  const table = getElement("graduatesTable");
  if (!table) {
    return;
  }
  table
    .querySelectorAll('[name="graduates_total[]"]')
    .forEach(function (field) {
      field.readOnly = true;
      field.dataset.completionIgnore = "1";
    });
  calculateAllGraduateTotals();
}
window.calculateAllGraduateTotals = calculateAllGraduateTotals;
window.initializeGraduatesAutoTotals = initializeGraduatesAutoTotals;
/* ========================================================= Faculty Summary Totals ========================================================= */ function updateFacultyGroupTotal(
  fieldNames,
  totalFieldName,
  totalFieldId,
) {
  let total = 0;
  let hasAnyValue = false;
  fieldNames.forEach(function (fieldName) {
    const field = getFieldByName(fieldName);
    if (!field) {
      return;
    }
    if (safeText(field.value) !== "") {
      hasAnyValue = true;
    }
    total += toSafeNumber(field.value);
  });
  const totalField = getFieldByName(totalFieldName) || getElement(totalFieldId);
  if (!totalField) {
    return;
  }
  setCalculatedField(totalField, hasAnyValue ? total : "");
}
function updateAllFacultySummaryTotals() {
  updateFacultyGroupTotal(
    [
      "fulltime_professor",
      "fulltime_associate_professor",
      "fulltime_assistant_professor",
      "fulltime_assistant_lecturer",
      "fulltime_research_assistant",
    ],
    "fulltime_faculty_total",
    "fulltimeFacultyTotal",
  );
  updateFacultyGroupTotal(
    [
      "supporting_professor",
      "supporting_associate_professor",
      "supporting_assistant_professor",
      "supporting_assistant_lecturer",
      "supporting_research_assistant",
    ],
    "supporting_faculty_total",
    "supportingFacultyTotal",
  );
  refreshAllCompletionStatuses();
}
function isFacultySummaryField(field) {
  if (!field || !field.name) {
    return false;
  }
  return [
    "fulltime_professor",
    "fulltime_associate_professor",
    "fulltime_assistant_professor",
    "fulltime_assistant_lecturer",
    "fulltime_research_assistant",
    "supporting_professor",
    "supporting_associate_professor",
    "supporting_assistant_professor",
    "supporting_assistant_lecturer",
    "supporting_research_assistant",
  ].includes(field.name);
}
function initializeFacultySummaryTotals() {
  const fields = document.querySelectorAll(
    '[name="fulltime_professor"], ' +
      '[name="fulltime_associate_professor"], ' +
      '[name="fulltime_assistant_professor"], ' +
      '[name="fulltime_assistant_lecturer"], ' +
      '[name="fulltime_research_assistant"], ' +
      '[name="supporting_professor"], ' +
      '[name="supporting_associate_professor"], ' +
      '[name="supporting_assistant_professor"], ' +
      '[name="supporting_assistant_lecturer"], ' +
      '[name="supporting_research_assistant"]',
  );
  fields.forEach(function (field) {
    if (field.dataset.facultySummaryBound === "1") {
      return;
    }
    field.dataset.facultySummaryBound = "1";
    field.addEventListener("input", updateAllFacultySummaryTotals);
    field.addEventListener("change", updateAllFacultySummaryTotals);
  });
  updateAllFacultySummaryTotals();
}
window.updateAllFacultySummaryTotals = updateAllFacultySummaryTotals;
window.initializeFacultySummaryTotals = initializeFacultySummaryTotals;
/* ========================================================= Program Specification Calculator ========================================================= */ function getHoursValue(
  fieldName,
) {
  const field = getFieldByName(fieldName);
  return field ? toSafeNumber(field.value) : 0;
}
function hasHoursValue(fieldName) {
  const field = getFieldByName(fieldName);
  return field ? normalizeNumberText(field.value) !== "" : false;
}
function setCalculatedPercentage(fieldName, value) {
  const field = getFieldByName(fieldName);
  if (!field) {
    return;
  }
  setCalculatedField(field, value);
}
function updateProgramSpecificationPercentages() {
  const universityHours = getHoursValue("university_requirements_hours");
  const collegeHours = getHoursValue("college_requirements_hours");
  const departmentHours = getHoursValue("department_requirements_hours");
  const oldMajorHours = getHoursValue("major_requirements_hours");
  const majorRequiredHours = getHoursValue("major_required_hours");
  const majorOptionalHours = getHoursValue("major_optional_hours");
  const majorHours = oldMajorHours || majorRequiredHours;
  const calculatedTotal =
    universityHours +
    collegeHours +
    departmentHours +
    majorHours +
    majorOptionalHours;
  const totalField = getFieldByName("total_credit_hours");
  let totalHours = calculatedTotal;
  if (totalField) {
    const totalRaw = normalizeNumberText(totalField.value);
    if (totalRaw !== "" && totalField.dataset.autoCalculated !== "1") {
      totalHours = toSafeNumber(totalField.value);
    } else {
      totalField.value = calculatedTotal ? calculatedTotal : "";
      totalField.dataset.autoCalculated = calculatedTotal ? "1" : "0";
      totalHours = calculatedTotal;
    }
  }
  const hasAnyHours =
    hasHoursValue("university_requirements_hours") ||
    hasHoursValue("college_requirements_hours") ||
    hasHoursValue("department_requirements_hours") ||
    hasHoursValue("major_requirements_hours") ||
    hasHoursValue("major_required_hours") ||
    hasHoursValue("major_optional_hours") ||
    (totalField && normalizeNumberText(totalField.value) !== "");
  if (!hasAnyHours || !totalHours) {
    setCalculatedPercentage("university_requirements_percentage", "");
    setCalculatedPercentage("college_requirements_percentage", "");
    setCalculatedPercentage("department_requirements_percentage", "");
    setCalculatedPercentage("major_requirements_percentage", "");
    setCalculatedPercentage("major_required_percentage", "");
    setCalculatedPercentage("major_optional_percentage", "");
    refreshAllCompletionStatuses();
    return;
  }
  setCalculatedPercentage(
    "university_requirements_percentage",
    formatPercentNumber(universityHours, totalHours),
  );
  setCalculatedPercentage(
    "college_requirements_percentage",
    formatPercentNumber(collegeHours, totalHours),
  );
  setCalculatedPercentage(
    "department_requirements_percentage",
    formatPercentNumber(departmentHours, totalHours),
  );
  setCalculatedPercentage(
    "major_requirements_percentage",
    formatPercentNumber(majorHours, totalHours),
  );
  setCalculatedPercentage(
    "major_required_percentage",
    formatPercentNumber(majorHours, totalHours),
  );
  setCalculatedPercentage(
    "major_optional_percentage",
    formatPercentNumber(majorOptionalHours, totalHours),
  );
  refreshAllCompletionStatuses();
}
function initializeProgramSpecificationCalculator() {
  const hourFields = [
    "university_requirements_hours",
    "college_requirements_hours",
    "department_requirements_hours",
    "major_requirements_hours",
    "major_required_hours",
    "major_optional_hours",
    "total_credit_hours",
  ];
  hourFields.forEach(function (fieldName) {
    const field = getFieldByName(fieldName);
    if (!field || field.dataset.programSpecBound === "1") {
      return;
    }
    field.dataset.programSpecBound = "1";
    field.addEventListener("input", function () {
      if (fieldName === "total_credit_hours") {
        field.dataset.autoCalculated = "0";
      }
      updateProgramSpecificationPercentages();
    });
    field.addEventListener("change", function () {
      if (fieldName === "total_credit_hours") {
        field.dataset.autoCalculated = "0";
      }
      updateProgramSpecificationPercentages();
    });
  });
  updateProgramSpecificationPercentages();
}
/* ========================================================= Teaching Hours Indicators ========================================================= */ function updateTeachingHoursIndicators() {
  const fulltimeHours = getHoursValue("fulltime_teaching_hours");
  const parttimeHours = getHoursValue("parttime_teaching_hours");
  const totalTeachingHours = fulltimeHours + parttimeHours;
  const hasFullOrPart =
    hasHoursValue("fulltime_teaching_hours") ||
    hasHoursValue("parttime_teaching_hours");
  setCalculatedPercentage(
    "fulltime_parttime_teaching_percentage",
    hasFullOrPart ? formatPercentNumber(fulltimeHours, totalTeachingHours) : "",
  );
  const phdHours = getHoursValue("phd_teaching_hours");
  const programTotalHours = getHoursValue("program_total_teaching_hours");
  const hasPhdData =
    hasHoursValue("phd_teaching_hours") ||
    hasHoursValue("program_total_teaching_hours");
  setCalculatedPercentage(
    "phd_teaching_hours_percentage",
    hasPhdData ? formatPercentNumber(phdHours, programTotalHours) : "",
  );
  refreshAllCompletionStatuses();
}
function initializeTeachingHoursIndicators() {
  [
    "fulltime_teaching_hours",
    "parttime_teaching_hours",
    "phd_teaching_hours",
    "program_total_teaching_hours",
  ].forEach(function (fieldName) {
    const field = getFieldByName(fieldName);
    if (!field || field.dataset.teachingHoursBound === "1") {
      return;
    }
    field.dataset.teachingHoursBound = "1";
    field.addEventListener("input", updateTeachingHoursIndicators);
    field.addEventListener("change", updateTeachingHoursIndicators);
  });
  updateTeachingHoursIndicators();
}
/* ========================================================= Performance Rates Average Calculator ========================================================= */ function normalizeRateNumber(
  value,
) {
  return String(value || "")
    .trim()
    .replace("%", "")
    .replace(/٠/g, "0")
    .replace(/١/g, "1")
    .replace(/٢/g, "2")
    .replace(/٣/g, "3")
    .replace(/٤/g, "4")
    .replace(/٥/g, "5")
    .replace(/٦/g, "6")
    .replace(/٧/g, "7")
    .replace(/٨/g, "8")
    .replace(/٩/g, "9");
}
function parseRateNumber(value) {
  const cleaned = normalizeRateNumber(value);
  if (cleaned === "") {
    return null;
  }
  const numberValue = Number(cleaned);
  return Number.isNaN(numberValue) ? null : numberValue;
}
function formatRateAverage(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
function calculateOnePerformanceAverage(maleName, femaleName, averageName) {
  const maleField = getFieldByName(maleName);
  const femaleField = getFieldByName(femaleName);
  const averageField = getFieldByName(averageName);
  if (!averageField) {
    return;
  }
  averageField.readOnly = true;
  averageField.dataset.completionIgnore = "1";
  const maleValue = maleField ? parseRateNumber(maleField.value) : null;
  const femaleValue = femaleField ? parseRateNumber(femaleField.value) : null;
  const values = [];
  if (maleValue !== null) {
    values.push(maleValue);
  }
  if (femaleValue !== null) {
    values.push(femaleValue);
  }
  if (values.length === 0) {
    averageField.value = "";
    return;
  }
  const total = values.reduce(function (sum, item) {
    return sum + item;
  }, 0);
  averageField.value = formatRateAverage(total / values.length);
}
function calculatePerformanceRatesAverages() {
  calculateOnePerformanceAverage(
    "male_success_rate",
    "female_success_rate",
    "average_success_rate",
  );
  calculateOnePerformanceAverage(
    "male_cumulative_gpa",
    "female_cumulative_gpa",
    "average_cumulative_gpa",
  );
  calculateOnePerformanceAverage(
    "male_progress_rate",
    "female_progress_rate",
    "average_progress_rate",
  );
  calculateOnePerformanceAverage(
    "male_retention_rate",
    "female_retention_rate",
    "average_retention_rate",
  );
  calculateOnePerformanceAverage(
    "male_flow_rate",
    "female_flow_rate",
    "average_flow_rate",
  );
  calculateOnePerformanceAverage(
    "male_withdrawal_rate",
    "female_withdrawal_rate",
    "average_withdrawal_rate",
  );
  refreshAllCompletionStatuses();
}
function initializePerformanceRatesCalculator() {
  [
    "male_success_rate",
    "female_success_rate",
    "male_cumulative_gpa",
    "female_cumulative_gpa",
    "male_progress_rate",
    "female_progress_rate",
    "male_retention_rate",
    "female_retention_rate",
    "male_flow_rate",
    "female_flow_rate",
    "male_withdrawal_rate",
    "female_withdrawal_rate",
  ].forEach(function (name) {
    const field = getFieldByName(name);
    if (!field || field.dataset.performanceBound === "1") {
      return;
    }
    field.dataset.performanceBound = "1";
    field.addEventListener("input", calculatePerformanceRatesAverages);
    field.addEventListener("change", calculatePerformanceRatesAverages);
  });
  calculatePerformanceRatesAverages();
}
window.calculatePerformanceRatesAverages = calculatePerformanceRatesAverages;
/* ========================================================= Collapsible Cards ========================================================= */ function initializeCollapsibleSections() {
  const panels = document.querySelectorAll(".aq-panel");
  panels.forEach(function (panel) {
    const cards = Array.from(panel.querySelectorAll(":scope > .aq-card"));
    cards.forEach(function (card, index) {
      if (card.classList.contains("collapse-ready")) {
        return;
      }
      let header =
        card.querySelector(":scope > .standard6-card-head") ||
        card.querySelector(":scope > .aq-card-head");
      const directTitle = card.querySelector(":scope > h3");
      let body = card.querySelector(":scope > .collapse-body");
      if (header) {
        header.classList.add("collapse-header");
        header.setAttribute("role", "button");
        header.setAttribute("tabindex", "0");
        if (!header.querySelector(".collapse-icon")) {
          const icon = document.createElement("span");
          icon.className = "collapse-icon";
          icon.textContent = "⌄";
          const actions = header.querySelector(".standard6-head-actions");
          if (actions) {
            actions.appendChild(icon);
          } else {
            header.appendChild(icon);
          }
        }
      } else if (directTitle) {
        header = document.createElement("button");
        header.type = "button";
        header.className = "collapse-header";
        header.innerHTML =
          '<span class="collapse-title">' +
          directTitle.textContent +
          '</span><span class="collapse-icon">⌄</span>';
        directTitle.replaceWith(header);
      }
      if (!header) {
        return;
      }
      if (!body) {
        body = document.createElement("div");
        body.className = "collapse-body";
        while (header.nextSibling) {
          body.appendChild(header.nextSibling);
        }
        card.appendChild(body);
      }
      card.classList.add("collapse-ready");
      const isFirstCard = index === 0;
      const isTableCard = card.classList.contains("aq-table-section");
      const isAttachmentsCard = card.classList.contains("aq-attachments");
      if (!isFirstCard || isTableCard || isAttachmentsCard) {
        card.classList.add("is-collapsed");
        header.setAttribute("aria-expanded", "false");
      } else {
        header.setAttribute("aria-expanded", "true");
      }
      function toggleCard(event) {
        if (event && event.target.closest(".table-actions")) {
          return;
        }
        if (event && event.target.closest(".standard6-add-btn")) {
          return;
        }
        if (
          event &&
          event.target.closest("input, select, textarea, label, a, button") &&
          !event.target.closest(".collapse-header")
        ) {
          return;
        }
        const collapsed = card.classList.toggle("is-collapsed");
        header.setAttribute("aria-expanded", collapsed ? "false" : "true");
        setTimeout(refreshAllCompletionStatuses, 50);
      }
      header.addEventListener("click", toggleCard);
      header.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggleCard(event);
        }
      });
    });
  });
}
/* ========================================================= Completion Status ========================================================= */ function completionText(
  value,
) {
  return String(value || "").trim();
}
function isAutoCalculatedOrIgnoredField(field) {
  if (!field) {
    return true;
  }
  const ignoredNames = [
    "student_total[]",
    "students_male_grand_total",
    "students_female_grand_total",
    "students_grand_total",
    "graduates_total[]",
    "graduates_male_grand_total",
    "graduates_female_grand_total",
    "graduates_grand_total",
    "fulltime_faculty_total",
    "supporting_faculty_total",
    "university_requirements_percentage",
    "college_requirements_percentage",
    "department_requirements_percentage",
    "major_requirements_percentage",
    "major_required_percentage",
    "major_optional_percentage",
    "fulltime_parttime_teaching_percentage",
    "phd_teaching_hours_percentage",
    "facility_count[]",
    "facility_area[]",
    "facility_equipment[]",
    "facility_notes[]",
  ];
  if (field.type === "hidden") {
    return true;
  }
  if (field.disabled) {
    return true;
  }
  if (field.dataset.completionIgnore === "1") {
    return true;
  }
  if (ignoredNames.includes(field.name)) {
    return true;
  }
  return false;
}
function isEmptySelectValue(value) {
  const text = completionText(value);
  return (
    text === "" ||
    text === "اختر" ||
    text === "اختار" ||
    text === "اختاري" ||
    text === "اختاري العام" ||
    text === "اختاري البرنامج أولًا" ||
    text === "لم يتم تحديد سنة بداية البرنامج"
  );
}
function isCompletionFieldFilled(field) {
  if (!field) {
    return false;
  }
  if (field.type === "file") {
    return field.files && field.files.length > 0;
  }
  if (field.type === "checkbox" || field.type === "radio") {
    return field.checked;
  }
  if (field.tagName && field.tagName.toLowerCase() === "select") {
    return !isEmptySelectValue(field.value);
  }
  return completionText(field.value) !== "";
}
function getCardBody(card) {
  return (
    card.querySelector(":scope > .collapse-body") ||
    card.querySelector(".collapse-body") ||
    card
  );
}
function getCardInputs(card) {
  const body = getCardBody(card);
  if (!body) {
    return [];
  }
  return Array.from(body.querySelectorAll("input, textarea, select")).filter(
    function (field) {
      if (isAutoCalculatedOrIgnoredField(field)) {
        return false;
      }
      if (field.closest(".table-actions")) {
        return false;
      }
      if (field.closest(".standard6-head-actions")) {
        return false;
      }
      return true;
    },
  );
}
function getStudentLevelsCompletionStatus(card) {
  const table = card ? card.querySelector("#studentsLevelsTable") : null;
  if (!table) {
    return null;
  }
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  let requiredCount = 0;
  let filledCount = 0;
  rows.forEach(function (row) {
    const maleField = row.querySelector('[name="student_male[]"]');
    const femaleField = row.querySelector('[name="student_female[]"]');
    [maleField, femaleField].forEach(function (field) {
      if (!field) {
        return;
      }
      requiredCount += 1;
      if (completionText(field.value) !== "") {
        filledCount += 1;
      }
    });
  });
  if (filledCount === 0) {
    return { status: "empty", title: "لم يتم إدخال بيانات أعداد الطلبة" };
  }
  if (filledCount < requiredCount) {
    return {
      status: "partial",
      title:
        "تم إدخال جزء من بيانات الطلبة: " +
        filledCount +
        " من " +
        requiredCount,
    };
  }
  return { status: "complete", title: "تم استكمال بيانات أعداد الطلبة" };
}
function getGraduatesCompletionStatus(card) {
  const table = card ? card.querySelector("#graduatesTable") : null;
  if (!table) {
    return null;
  }
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  let requiredCount = 0;
  let filledCount = 0;
  rows.forEach(function (row) {
    const yearField = row.querySelector('[name="graduates_year[]"]');
    const maleField = row.querySelector('[name="graduates_male[]"]');
    const femaleField = row.querySelector('[name="graduates_female[]"]');
    [yearField, maleField, femaleField].forEach(function (field) {
      if (!field) {
        return;
      }
      requiredCount += 1;
      if (isCompletionFieldFilled(field)) {
        filledCount += 1;
      }
    });
  });
  if (filledCount === 0) {
    return { status: "empty", title: "لم يتم إدخال بيانات الخريجين" };
  }
  if (filledCount < requiredCount) {
    return {
      status: "partial",
      title:
        "تم إدخال جزء من بيانات الخريجين: " +
        filledCount +
        " من " +
        requiredCount,
    };
  }
  return { status: "complete", title: "تم استكمال بيانات الخريجين" };
}
function updateCardCompletionStatus(card) {
  if (!card) {
    return;
  }
  const icon =
    card.querySelector(":scope > .collapse-header .collapse-icon") ||
    card.querySelector(".collapse-header .collapse-icon") ||
    card.querySelector(".collapse-icon");
  if (!icon) {
    return;
  }
  icon.classList.remove("status-empty", "status-partial", "status-complete");
  const studentStatus = getStudentLevelsCompletionStatus(card);
  if (studentStatus) {
    icon.classList.add("status-" + studentStatus.status);
    icon.title = studentStatus.title;
    return;
  }
  const graduatesStatus = getGraduatesCompletionStatus(card);
  if (graduatesStatus) {
    icon.classList.add("status-" + graduatesStatus.status);
    icon.title = graduatesStatus.title;
    return;
  }
  const fields = getCardInputs(card);
  if (fields.length === 0) {
    icon.classList.add("status-empty");
    icon.title = "لا توجد بيانات مطلوبة في هذا القسم";
    return;
  }
  const filledCount = fields.filter(isCompletionFieldFilled).length;
  if (filledCount === 0) {
    icon.classList.add("status-empty");
    icon.title = "لم يتم إدخال بيانات في هذا القسم";
    return;
  }
  if (filledCount < fields.length) {
    icon.classList.add("status-partial");
    icon.title =
      "تم إدخال جزء من البيانات: " + filledCount + " من " + fields.length;
    return;
  }
  icon.classList.add("status-complete");
  icon.title = "تم استكمال بيانات هذا القسم";
}
function refreshAllCompletionStatuses() {
  document.querySelectorAll(".aq-card").forEach(function (card) {
    updateCardCompletionStatus(card);
  });
}
function bindCompletionEventsForCard(card) {
  if (!card) {
    return;
  }
  getCardInputs(card).forEach(function (field) {
    if (field.dataset.completionBound === "1") {
      return;
    }
    field.dataset.completionBound = "1";
    field.addEventListener("input", function () {
      updateCardCompletionStatus(card);
      refreshAllCompletionStatuses();
    });
    field.addEventListener("change", function () {
      updateCardCompletionStatus(card);
      refreshAllCompletionStatuses();
    });
  });
}
function initializeCompletionStatus() {
  refreshAllCompletionStatuses();
  document.querySelectorAll(".aq-card").forEach(function (card) {
    bindCompletionEventsForCard(card);
  });
  document.addEventListener("input", function (event) {
    const card = event.target.closest(".aq-card");
    if (card) {
      updateCardCompletionStatus(card);
    }
  });
  document.addEventListener("change", function (event) {
    const card = event.target.closest(".aq-card");
    if (card) {
      updateCardCompletionStatus(card);
    }
  });
  setTimeout(refreshAllCompletionStatuses, 100);
  setTimeout(refreshAllCompletionStatuses, 500);
  setTimeout(refreshAllCompletionStatuses, 1000);
}
window.updateCardCompletionStatus = updateCardCompletionStatus;
window.refreshAllCompletionStatuses = refreshAllCompletionStatuses;
window.bindCompletionEventsForCard = bindCompletionEventsForCard;
/* ========================================================= Saved Evaluation Files Modal ========================================================= */ function initializeSavedFilesModal() {
  const openSavedFilesBtn = getElement("openSavedFilesBtn");
  const closeSavedFilesBtn = getElement("closeSavedFilesBtn");
  const savedFilesModal = getElement("savedFilesModal");
  if (openSavedFilesBtn && savedFilesModal) {
    openSavedFilesBtn.addEventListener("click", function () {
      savedFilesModal.classList.remove("hidden");
    });
  }
  if (closeSavedFilesBtn && savedFilesModal) {
    closeSavedFilesBtn.addEventListener("click", function () {
      savedFilesModal.classList.add("hidden");
    });
  }
  if (savedFilesModal) {
    savedFilesModal.addEventListener("click", function (event) {
      if (event.target === savedFilesModal) {
        savedFilesModal.classList.add("hidden");
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        savedFilesModal.classList.add("hidden");
      }
    });
  }
}
/* ========================================================= Load Saved Data ========================================================= */ function fillSavedFormFields() {
  const savedFormData = parseJsonScript("savedFormData");
  if (
    !savedFormData ||
    typeof savedFormData !== "object" ||
    Array.isArray(savedFormData)
  ) {
    return;
  }
  Object.keys(savedFormData).forEach(function (fieldName) {
    if (fieldName.endsWith("[]")) {
      return;
    }
    const fields = document.getElementsByName(fieldName);
    if (!fields || fields.length === 0) {
      return;
    }
    const value = savedFormData[fieldName];
    Array.from(fields).forEach(function (field, index) {
      if (!field || field.type === "file" || field.type === "hidden") {
        return;
      }
      if (Array.isArray(value)) {
        setFieldValue(field, value[index] || "");
      } else {
        setFieldValue(field, value);
      }
      fireFieldEvents(field);
    });
  });
}
function normalizeSavedTableRows(tableData) {
  if (Array.isArray(tableData)) {
    return tableData;
  }
  if (tableData && typeof tableData === "object") {
    if (Array.isArray(tableData.rows)) {
      return tableData.rows;
    }
    if (Array.isArray(tableData.data)) {
      return tableData.data;
    }
  }
  return [];
}
function fillSavedTables() {
  const savedTablesData = parseJsonScript("savedTablesData");
  if (
    !savedTablesData ||
    typeof savedTablesData !== "object" ||
    Array.isArray(savedTablesData)
  ) {
    return;
  }
  Object.keys(savedTablesData).forEach(function (tableId) {
    const rows = normalizeSavedTableRows(savedTablesData[tableId]);
    if (!rows || rows.length === 0) {
      return;
    }
    fillTableFromRows(tableId, rows);
  });
}
function refreshCompletionStatusAfterLoading() {
  initializeStudentLevelsAutoTotals();
  initializeGraduatesAutoTotals();
  initializeFacultySummaryTotals();
  updateAllFacultySummaryTotals();
  updateProgramSpecificationPercentages();
  updateTeachingHoursIndicators();
  calculatePerformanceRatesAverages();
  calculatePhysicalEnvironmentCriteria();
  document.querySelectorAll(".aq-card.collapse-ready").forEach(function (card) {
    bindCompletionEventsForCard(card);
    updateCardCompletionStatus(card);
  });
}
/* ========================================================= Old Infrastructure Compliance Support ========================================================= */ function syncInfrastructureComplianceRows() {
  const table = getElement("infrastructureTable");
  if (!table) {
    return;
  }
  table.querySelectorAll("tbody tr").forEach(function (row) {
    const hiddenStatus = row.querySelector('[name="facility_equipment[]"]');
    if (!hiddenStatus) {
      return;
    }
    const statusValue = safeText(hiddenStatus.value);
    const radios = row.querySelectorAll(
      'input[type="radio"][name^="facility_match_"]',
    );
    radios.forEach(function (radio) {
      radio.checked = radio.value === statusValue;
    });
    row.classList.remove("is-matched", "is-not-matched");
    if (statusValue === "مطابق") {
      row.classList.add("is-matched");
    }
    if (statusValue === "غير مطابق") {
      row.classList.add("is-not-matched");
    }
  });
}
function initializeInfrastructureComplianceControls() {
  const table = getElement("infrastructureTable");
  if (!table) {
    return;
  }
  table
    .querySelectorAll('input[type="radio"][name^="facility_match_"]')
    .forEach(function (radio) {
      if (radio.dataset.infrastructureBound === "1") {
        return;
      }
      radio.dataset.infrastructureBound = "1";
      radio.addEventListener("change", function () {
        const row = radio.closest("tr");
        if (!row) {
          return;
        }
        const hiddenStatus = row.querySelector('[name="facility_equipment[]"]');
        if (hiddenStatus) {
          hiddenStatus.value = radio.value;
        }
        syncInfrastructureComplianceRows();
        refreshAllCompletionStatuses();
      });
    });
  syncInfrastructureComplianceRows();
}
window.initializeInfrastructureComplianceControls =
  initializeInfrastructureComplianceControls;
window.syncInfrastructureComplianceRows = syncInfrastructureComplianceRows;
/* ========================================================= Standard 6: Physical Environment Auto Compliance ========================================================= */ function physicalNumber(
  value,
) {
  return toSafeNumber(value);
}
function physicalHasValue(value) {
  return safeText(value) !== "";
}
function getTotalStudentsForPhysical() {
    const grandTotalField =
        document.getElementById("studentsGrandTotal") ||
        document.querySelector('[name="students_grand_total"]');

    const fieldValue = grandTotalField ? physicalNumber(grandTotalField.value) : 0;

    if (fieldValue > 0) {
        return fieldValue;
    }

    /*
        احتياط مهم:
        إذا كان حقل الإجمالي لم يتحدث بعد، نحسب إجمالي الطلبة مباشرة من جدول الطلاب.
        هذا يمنع ظهور المطلوب = 1 أو 0 رغم وجود بيانات في جدول الطلاب.
    */
    const studentsTable = document.getElementById("studentsLevelsTable");

    if (!studentsTable) {
        return 0;
    }

    let totalStudents = 0;

    studentsTable.querySelectorAll("tbody tr").forEach(function (row) {
        const maleField = row.querySelector('[name="student_male[]"]');
        const femaleField = row.querySelector('[name="student_female[]"]');
        const totalField = row.querySelector('[name="student_total[]"]');

        const rowTotal = totalField ? physicalNumber(totalField.value) : 0;

        if (rowTotal > 0) {
            totalStudents += rowTotal;
            return;
        }

        totalStudents += physicalNumber(maleField ? maleField.value : 0);
        totalStudents += physicalNumber(femaleField ? femaleField.value : 0);
    });

    return totalStudents;
}
function getClassroomRowsData() {
    const table = document.getElementById("classroomsDataTable");

    if (!table) {
        return [];
    }

    return Array.from(table.querySelectorAll("tbody tr"))
        .map(function (row) {
            return {
                group: row.querySelector('[name="classroom_group[]"]')?.value || "",
                name: row.querySelector('[name="classroom_name[]"]')?.value || "",
                area: physicalNumber(row.querySelector('[name="classroom_area[]"]')?.value),
                capacity: physicalNumber(row.querySelector('[name="classroom_capacity[]"]')?.value),
                desk: row.querySelector('[name="classroom_has_desk[]"]')?.value || "",
                projector: row.querySelector('[name="classroom_has_projector[]"]')?.value || "",
                board: row.querySelector('[name="classroom_has_board[]"]')?.value || "",
                platform: row.querySelector('[name="classroom_has_platform[]"]')?.value || ""
            };
        })
        .filter(function (item) {
            return (
                physicalHasValue(item.name) ||
                item.area > 0 ||
                item.capacity > 0
            );
        });
}
function getLabRowsData() {
  const table = getElement("labsDataTable");
  if (!table) {
    return [];
  }
  return Array.from(table.querySelectorAll("tbody tr"))
    .map(function (row) {
      return {
        kind: row.querySelector('[name="lab_kind[]"]')?.value || "",
        name: row.querySelector('[name="lab_name[]"]')?.value || "",
        area: physicalNumber(row.querySelector('[name="lab_area[]"]')?.value),
        capacity: physicalNumber(
          row.querySelector('[name="lab_capacity[]"]')?.value,
        ),
        devices: physicalNumber(
          row.querySelector('[name="lab_devices_count[]"]')?.value,
        ),
        projector:
          row.querySelector('[name="lab_has_projector[]"]')?.value || "",
        board: row.querySelector('[name="lab_has_board[]"]')?.value || "",
      };
    })
    .filter(function (item) {
      return (
        physicalHasValue(item.kind) ||
        physicalHasValue(item.name) ||
        item.area > 0 ||
        item.capacity > 0 ||
        item.devices > 0
      );
    });
}
function setPhysicalCriterion(
  tableId,
  criterionName,
  availableText,
  isMatched,
) {
  const table = getElement(tableId);
  if (!table) {
    return;
  }
  const row = table.querySelector('[data-criterion="' + criterionName + '"]');
  if (!row) {
    return;
  }
  const availableInput = row.querySelector('[name="facility_count[]"]');
  const equipmentInput = row.querySelector('[name="facility_equipment[]"]');
  if (availableInput) {
    availableInput.value = availableText || "";
    availableInput.readOnly = true;
    availableInput.dataset.completionIgnore = "1";
  }
  const status = availableText ? (isMatched ? "مطابق" : "غير مطابق") : "";
  if (equipmentInput) {
    equipmentInput.value = status;
  }
  row.querySelectorAll('input[type="radio"]').forEach(function (radio) {
    radio.checked = radio.value === status;
  });
  row.classList.remove("is-matched", "is-not-matched");
  if (status === "مطابق") {
    row.classList.add("is-matched");
  }
  if (status === "غير مطابق") {
    row.classList.add("is-not-matched");
  }
}
function clearClassroomsCriteria() {
  [
    "classroom_share",
    "classroom_area",
    "classroom_capacity_30",
    "public_halls",
  ].forEach(function (criterion) {
    setPhysicalCriterion("classroomsCriteriaTable", criterion, "", false);
  });
}
function clearLabsCriteria() {
  [
    "labs_count",
    "lab_area",
    "lab_capacity",
    "workshop_count",
    "workshop_area",
    "workshop_capacity",
    "computer_lab_count",
    "computer_lab_capacity",
  ].forEach(function (criterion) {
    setPhysicalCriterion("labsCriteriaTable", criterion, "", false);
  });
}
function calculateClassroomsCriteria() {
  const rooms = getClassroomRowsData();
  const totalStudents = getTotalStudentsForPhysical();
  if (rooms.length === 0) {
    clearClassroomsCriteria();
    return;
  }
  const capacities = rooms
    .map(function (item) {
      return item.capacity;
    })
    .filter(function (value) {
      return value > 0;
    });
  const areas = rooms
    .map(function (item) {
      return item.area;
    })
    .filter(function (value) {
      return value > 0;
    });
  const maxCapacity = capacities.length ? Math.max.apply(null, capacities) : 0;
  const minArea = areas.length ? Math.min.apply(null, areas) : 0;
  const roomsWithShare = rooms.filter(function (item) {
    return item.area > 0 && item.capacity > 0;
  });
  const minShare = roomsWithShare.length
    ? Math.min.apply(
        null,
        roomsWithShare.map(function (item) {
          return item.area / item.capacity;
        }),
      )
    : 0;
  const shareMatched =
    roomsWithShare.length > 0 && minShare >= 1 && maxCapacity <= 40;
  setPhysicalCriterion(
    "classroomsCriteriaTable",
    "classroom_share",
    roomsWithShare.length
      ? "أقل حصة: " + minShare.toFixed(2) + "م²، أعلى سعة: " + maxCapacity
      : "",
    shareMatched,
  );
  setPhysicalCriterion(
    "classroomsCriteriaTable",
    "classroom_area",
    minArea ? "أقل مساحة: " + minArea + "م²" : "",
    minArea >= 40,
  );
  const totalCapacity = rooms.reduce(function (sum, item) {
    return sum + item.capacity;
  }, 0);
  const requiredCapacity = totalStudents ? Math.ceil(totalStudents * 0.3) : 0;
  setPhysicalCriterion(
    "classroomsCriteriaTable",
    "classroom_capacity_30",
    totalStudents
      ? "السعة: " + totalCapacity + " / المطلوب: " + requiredCapacity
      : "السعة: " + totalCapacity,
    totalStudents ? totalCapacity >= requiredCapacity : false,
  );
 /*
    بعد حذف نوع القاعة:
    كل القاعات تعتبر قاعات تدريس/محاضرات/مناقشة.
    لذلك نحسب القاعات المجهزة من جميع القاعات، وليس من نوع "محاضرة عامة" فقط.
*/
const equippedClassrooms = rooms.filter(function (item) {
    return (
        item.capacity > 0 &&
        item.capacity <= 100 &&
        item.desk === "نعم" &&
        item.projector === "نعم" &&
        item.board === "نعم"
    );
});

setPhysicalCriterion(
    "classroomsCriteriaTable",
    "public_halls",
    "عدد القاعات المجهزة المطابقة: " + equippedClassrooms.length,
    equippedClassrooms.length >= 2
);
}
function calculateLabsCriteria() {
  const labs = getLabRowsData();
  if (labs.length === 0) {
    clearLabsCriteria();
    return;
  }
  const labsOnly = labs.filter(function (item) {
    return item.kind === "مختبر" || item.kind === "معمل";
  });
  const workshops = labs.filter(function (item) {
    return item.kind === "ورشة";
  });
  const computerLabs = labs.filter(function (item) {
    return item.kind === "معمل حاسب";
  });
  setPhysicalCriterion(
    "labsCriteriaTable",
    "labs_count",
    "المختبرات/المعامل: " + labsOnly.length,
    labsOnly.length >= 1,
  );
  const labAreas = labsOnly
    .map(function (item) {
      return item.area;
    })
    .filter(function (value) {
      return value > 0;
    });
  const minLabArea = labAreas.length ? Math.min.apply(null, labAreas) : 0;
  setPhysicalCriterion(
    "labsCriteriaTable",
    "lab_area",
    minLabArea ? "أقل مساحة: " + minLabArea + "م²" : "",
    minLabArea >= 45,
  );
  const labCapacities = labsOnly
    .map(function (item) {
      return item.capacity;
    })
    .filter(function (value) {
      return value > 0;
    });
  const maxLabCapacity = labCapacities.length
    ? Math.max.apply(null, labCapacities)
    : 0;
  setPhysicalCriterion(
    "labsCriteriaTable",
    "lab_capacity",
    maxLabCapacity ? "أعلى عدد طلبة: " + maxLabCapacity : "",
    maxLabCapacity > 0 && maxLabCapacity <= 20,
  );
  setPhysicalCriterion(
    "labsCriteriaTable",
    "workshop_count",
    "عدد الورش: " + workshops.length,
    workshops.length >= 1,
  );
  const workshopAreas = workshops
    .map(function (item) {
      return item.area;
    })
    .filter(function (value) {
      return value > 0;
    });
  const minWorkshopArea = workshopAreas.length
    ? Math.min.apply(null, workshopAreas)
    : 0;
  setPhysicalCriterion(
    "labsCriteriaTable",
    "workshop_area",
    minWorkshopArea ? "أقل مساحة: " + minWorkshopArea + "م²" : "",
    minWorkshopArea >= 45,
  );
  const workshopCapacities = workshops
    .map(function (item) {
      return item.capacity;
    })
    .filter(function (value) {
      return value > 0;
    });
  const maxWorkshopCapacity = workshopCapacities.length
    ? Math.max.apply(null, workshopCapacities)
    : 0;
  setPhysicalCriterion(
    "labsCriteriaTable",
    "workshop_capacity",
    maxWorkshopCapacity ? "أعلى عدد طلبة: " + maxWorkshopCapacity : "",
    maxWorkshopCapacity > 0 && maxWorkshopCapacity <= 20,
  );
  setPhysicalCriterion(
    "labsCriteriaTable",
    "computer_lab_count",
    "عدد معامل الحاسب: " + computerLabs.length,
    computerLabs.length >= 1,
  );
  const computerCapacities = computerLabs
    .map(function (item) {
      return item.capacity;
    })
    .filter(function (value) {
      return value > 0;
    });
  const maxComputerCapacity = computerCapacities.length
    ? Math.max.apply(null, computerCapacities)
    : 0;
  setPhysicalCriterion(
    "labsCriteriaTable",
    "computer_lab_capacity",
    maxComputerCapacity ? "أعلى عدد طلبة: " + maxComputerCapacity : "",
    maxComputerCapacity > 0 && maxComputerCapacity <= 20,
  );
}
function calculatePhysicalEnvironmentCriteria() {
  calculateClassroomsCriteria();
  calculateLabsCriteria();
  refreshAllCompletionStatuses();
}
function renumberPhysicalTableRows(table) {
  refreshRowNumbers(table);
}
function addPhysicalClassroomRow() {
  const table = getElement("classroomsDataTable");
  const tbody = table ? table.querySelector("tbody") : null;
  const firstRow = tbody ? tbody.querySelector("tr") : null;
  if (!table || !tbody || !firstRow) {
    return;
  }
  const newRow = firstRow.cloneNode(true);
  newRow.querySelectorAll("input, select").forEach(function (field) {
    if (field.tagName === "SELECT") {
      field.selectedIndex = 0;
    } else {
      field.value = "";
    }
    delete field.dataset.completionBound;
    delete field.dataset.physicalBound;
  });
  tbody.appendChild(newRow);
  renumberPhysicalTableRows(table);
  calculatePhysicalEnvironmentCriteria();
  refreshCardAfterTableChange(table);
}
function addPhysicalLabRow() {
  const table = getElement("labsDataTable");
  const tbody = table ? table.querySelector("tbody") : null;
  const firstRow = tbody ? tbody.querySelector("tr") : null;
  if (!table || !tbody || !firstRow) {
    return;
  }
  const newRow = firstRow.cloneNode(true);
  newRow.querySelectorAll("input, select").forEach(function (field) {
    if (field.tagName === "SELECT") {
      field.selectedIndex = 0;
    } else {
      field.value = "";
    }
    delete field.dataset.completionBound;
    delete field.dataset.physicalBound;
  });
  tbody.appendChild(newRow);
  renumberPhysicalTableRows(table);
  calculatePhysicalEnvironmentCriteria();
  refreshCardAfterTableChange(table);
}
function initializePhysicalEnvironmentControls() {
  const tables = [
    getElement("classroomsDataTable"),
    getElement("labsDataTable"),
  ].filter(Boolean);
  tables.forEach(function (table) {
    table.querySelectorAll("input, select").forEach(function (field) {
      if (field.dataset.physicalBound === "1") {
        return;
      }
      field.dataset.physicalBound = "1";
      field.addEventListener("input", calculatePhysicalEnvironmentCriteria);
      field.addEventListener("change", calculatePhysicalEnvironmentCriteria);
    });
  });
  [
    "studentsGrandTotal",
    "studentsMaleGrandTotal",
    "studentsFemaleGrandTotal",
  ].forEach(function (id) {
    const field = getElement(id);
    if (field && field.dataset.physicalTotalBound !== "1") {
      field.dataset.physicalTotalBound = "1";
      field.addEventListener("input", calculatePhysicalEnvironmentCriteria);
      field.addEventListener("change", calculatePhysicalEnvironmentCriteria);
    }
  });
  calculatePhysicalEnvironmentCriteria();
}
window.calculatePhysicalEnvironmentCriteria =
  calculatePhysicalEnvironmentCriteria;
window.addPhysicalClassroomRow = addPhysicalClassroomRow;
window.addPhysicalLabRow = addPhysicalLabRow;
/* ========================================================= Delegated Events ========================================================= */ document.addEventListener(
  "input",
  function (event) {
    const target = event.target;
    if (!target) {
      return;
    }
    if (
      target.matches('[name="student_male[]"]') ||
      target.matches('[name="student_female[]"]')
    ) {
      calculateAllStudentTotals();
    }
    if (
      target.matches('[name="graduates_male[]"]') ||
      target.matches('[name="graduates_female[]"]')
    ) {
      calculateAllGraduateTotals();
    }
    if (isFacultySummaryField(target)) {
      updateAllFacultySummaryTotals();
    }
    if (
      target.closest("#classroomsDataTable") ||
      target.closest("#labsDataTable")
    ) {
      calculatePhysicalEnvironmentCriteria();
    }
  },
);
document.addEventListener("change", function (event) {
  const target = event.target;
  if (!target) {
    return;
  }
  if (
    target.matches('[name="student_male[]"]') ||
    target.matches('[name="student_female[]"]')
  ) {
    calculateAllStudentTotals();
  }
  if (
    target.matches('[name="graduates_male[]"]') ||
    target.matches('[name="graduates_female[]"]')
  ) {
    calculateAllGraduateTotals();
  }
  if (isFacultySummaryField(target)) {
    updateAllFacultySummaryTotals();
  }
  if (
    target.closest("#classroomsDataTable") ||
    target.closest("#labsDataTable")
  ) {
    calculatePhysicalEnvironmentCriteria();
  }
});
/* ========================================================= Main Init ========================================================= */ function initializeDataEntryPage() {
  initializeTabs();
  initializeProgramDialog();
  fillSavedFormFields();
  fillSavedTables();
  initializeCollapsibleSections();
  initializeStudentLevelsAutoTotals();
  initializeGraduatesAutoTotals();
  initializeFacultySummaryTotals();
  initializeProgramSpecificationCalculator();
  initializeTeachingHoursIndicators();
  initializePerformanceRatesCalculator();
  initializeInfrastructureComplianceControls();
  initializePhysicalEnvironmentControls();
  initializeStandard6DefaultRows();
  initializeCompletionStatus();
  initializeSavedFilesModal();
  setTimeout(refreshCompletionStatusAfterLoading, 150);
  setTimeout(refreshCompletionStatusAfterLoading, 500);
  setTimeout(refreshCompletionStatusAfterLoading, 1000);
}
/* =========================================================
   Minimum Default Rows for Standard 6
========================================================= */

function ensureMinimumRows(tableId, minimumRows, addRowFunction) {
    const table = document.getElementById(tableId);
    const tbody = table ? table.querySelector("tbody") : null;

    if (!table || !tbody) {
        return;
    }

    let currentRows = tbody.querySelectorAll("tr").length;

    /*
        إذا كان عدد الصفوف أقل من المطلوب
        أضيفي صفوفًا حتى يصل إلى العدد المحدد
    */
    while (currentRows < minimumRows) {
        addRowFunction();
        currentRows = tbody.querySelectorAll("tr").length;
    }

    refreshRowNumbers(table);

    if (tableId === "classroomsDataTable" || tableId === "labsDataTable") {
        calculatePhysicalEnvironmentCriteria();
    }
}

function initializeStandard6DefaultRows() {
    /*
        نريد 4 صفوف افتراضيًا للقاعات
        و4 صفوف افتراضيًا للمعامل
    */
    ensureMinimumRows("classroomsDataTable", 4, addPhysicalClassroomRow);
    ensureMinimumRows("labsDataTable", 4, addPhysicalLabRow);
}
/* =========================================================
   FINAL STANDARD 6 COLLAPSE + SOFT SELECT FIX
========================================================= */

(function () {
    function updateStandard6SelectState(select) {
        if (!select) {
            return;
        }

        if (String(select.value || "").trim() === "") {
            select.classList.add("is-empty");
        } else {
            select.classList.remove("is-empty");
        }
    }

    function refreshStandard6Selects() {
        document.querySelectorAll(".standard6-card select").forEach(function (select) {
            updateStandard6SelectState(select);

            if (select.dataset.standard6SelectBound === "1") {
                return;
            }

            select.dataset.standard6SelectBound = "1";

            select.addEventListener("change", function () {
                updateStandard6SelectState(select);
            });

            select.addEventListener("input", function () {
                updateStandard6SelectState(select);
            });
        });
    }

    function toggleStandard6Card(card) {
        if (!card) {
            return;
        }

        const header = card.querySelector(":scope > .standard6-card-head");
        const collapsed = card.classList.toggle("is-collapsed");

        if (header) {
            header.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }

        if (typeof window.refreshAllCompletionStatuses === "function") {
            window.refreshAllCompletionStatuses();
        }
    }

    /*
        نستخدم capture = true
        حتى نمنع تكرار حدث الطي القديم الذي قد يفتح ويغلق في نفس اللحظة.
    */
    document.addEventListener(
        "click",
        function (event) {
            const header = event.target.closest(".standard6-card-head");

            if (!header) {
                return;
            }

            const card = header.closest(".standard6-card");

            if (!card) {
                return;
            }

            if (event.target.closest(".standard6-add-btn")) {
                event.stopPropagation();
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            toggleStandard6Card(card);
        },
        true
    );

    document.addEventListener(
        "keydown",
        function (event) {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }

            const header = event.target.closest(".standard6-card-head");

            if (!header) {
                return;
            }

            const card = header.closest(".standard6-card");

            if (!card) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            toggleStandard6Card(card);
        },
        true
    );

    function initializeStandard6FinalFix() {
        refreshStandard6Selects();

        document.querySelectorAll(".standard6-card-head").forEach(function (header) {
            header.setAttribute("role", "button");
            header.setAttribute("tabindex", "0");
        });
    }

    document.addEventListener("DOMContentLoaded", initializeStandard6FinalFix);

    document.addEventListener("change", function (event) {
        if (event.target && event.target.closest(".standard6-card")) {
            refreshStandard6Selects();
        }
    });

    document.addEventListener("input", function (event) {
        if (event.target && event.target.closest(".standard6-card")) {
            refreshStandard6Selects();
        }
    });

    setTimeout(initializeStandard6FinalFix, 100);
    setTimeout(initializeStandard6FinalFix, 500);
    setTimeout(initializeStandard6FinalFix, 1000);
})

();

document.addEventListener("DOMContentLoaded", initializeDataEntryPage);
