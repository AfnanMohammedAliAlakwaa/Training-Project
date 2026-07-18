document.addEventListener("DOMContentLoaded", function () {
    const tableRows = document.querySelectorAll(".imp-table tbody tr");

    tableRows.forEach(function (row) {
        row.addEventListener("click", function () {
            tableRows.forEach(function (item) {
                item.classList.remove("is-selected-row");
            });

            row.classList.add("is-selected-row");
        });
    });
});