document.addEventListener("DOMContentLoaded", function () {
    const analysisPage = document.querySelector(".analysis-page");

    if (!analysisPage) {
        return;
    }

    /* =========================================================
       تنظيف علامات الطي القديمة التي أضيفت سابقًا
       لا يتم إنشاء أي علامة طي جديدة من JavaScript
    ========================================================= */

    document
        .querySelectorAll(
            ".analysis-accordion-toggle, " +
            ".analysis-user-guide-toggle, " +
            ".analysis-user-guide-toggle-fixed"
        )
        .forEach(function (element) {
            element.remove();
        });


    /* =========================================================
       إدارة حالة الأقسام القابلة للطي
    ========================================================= */

    const accordionCards = document.querySelectorAll(
        "details.analysis-accordion-card"
    );

    accordionCards.forEach(function (card) {
        const summary = Array.from(card.children).find(
            function (element) {
                return element.tagName === "SUMMARY";
            }
        );

        if (!summary) {
            return;
        }

        function updateAccordionState() {
            card.classList.toggle("is-active", card.open);

            summary.setAttribute(
                "aria-expanded",
                card.open ? "true" : "false"
            );
        }

        updateAccordionState();

        card.addEventListener("toggle", function () {
            updateAccordionState();

            if (
                typeof window.renderAnalysisTemporalChart === "function"
            ) {
                window.setTimeout(function () {
                    window.renderAnalysisTemporalChart();
                }, 40);
            }
        });
    });


    /* =========================================================
       فلترة السنوات حسب البرنامج المختار
    ========================================================= */

    const programSelect = document.getElementById("program_id");
    const yearSelect = document.getElementById("academic_year");
    const yearsMapScript = document.getElementById(
        "analysisProgramYearsMap"
    );

    let programYearsMap = {};

    if (yearsMapScript) {
        try {
            programYearsMap = JSON.parse(
                yearsMapScript.textContent || "{}"
            );
        } catch (error) {
            console.error(
                "تعذر قراءة سنوات البرامج:",
                error
            );

            programYearsMap = {};
        }
    }

    const originalYearOptions = yearSelect
        ? Array.from(
            yearSelect.querySelectorAll("option")
        ).map(function (option) {
            return {
                value: option.value,
                text: option.textContent.trim()
            };
        })
        : [];

    function getAllStoredYears() {
        return originalYearOptions
            .filter(function (option) {
                return (
                    option.value &&
                    option.value !== "all"
                );
            })
            .map(function (option) {
                return option.value;
            });
    }

    function addYearOption(value, text, selected) {
        if (!yearSelect) {
            return;
        }

        const option = document.createElement("option");

        option.value = value;
        option.textContent = text;
        option.selected = Boolean(selected);

        yearSelect.appendChild(option);
    }

    function rebuildYearOptions(keepCurrentValue) {
        if (!programSelect || !yearSelect) {
            return;
        }

        const selectedProgram =
            programSelect.value || "all";

        const previousYear = keepCurrentValue
            ? yearSelect.value || "all"
            : "all";

        let availableYears = [];

        if (selectedProgram === "all") {
            availableYears = getAllStoredYears();
        } else {
            availableYears =
                programYearsMap[selectedProgram] || [];
        }

        yearSelect.innerHTML = "";

        addYearOption(
            "all",
            "كل السنوات",
            previousYear === "all"
        );

        if (!availableYears.length) {
            const emptyOption =
                document.createElement("option");

            emptyOption.value = "";
            emptyOption.textContent =
                "لا توجد سنوات محفوظة لهذا الاختيار";
            emptyOption.disabled = true;

            yearSelect.appendChild(emptyOption);
            yearSelect.value = "all";

            return;
        }

        availableYears.forEach(function (year) {
            addYearOption(
                year,
                year,
                previousYear === year
            );
        });

        if (
            previousYear !== "all" &&
            !availableYears.includes(previousYear)
        ) {
            yearSelect.value = "all";
        }
    }

    if (programSelect && yearSelect) {
        rebuildYearOptions(true);

        programSelect.addEventListener(
            "change",
            function () {
                rebuildYearOptions(false);
            }
        );
    }


    /* =========================================================
       تحديد صف الجدول عند الضغط عليه
    ========================================================= */

    const tableRows = document.querySelectorAll(
        ".analysis-table tbody tr"
    );

    tableRows.forEach(function (row) {
        row.addEventListener("click", function () {
            tableRows.forEach(function (item) {
                item.classList.remove(
                    "is-selected-row"
                );
            });

            row.classList.add("is-selected-row");
        });
    });


    /* =========================================================
       الانتقال الناعم للروابط الداخلية العادية
       مع تجاهل روابط تبويبات التحليل
    ========================================================= */

    if (
        window.location.hash &&
        !window.location.hash.startsWith("#analysis-")
    ) {
        let target = null;

        try {
            target = document.querySelector(
                window.location.hash
            );
        } catch (error) {
            target = null;
        }

        if (target) {
            window.setTimeout(function () {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }, 250);
        }
    }


    /* =========================================================
       أزرار إنشاء خطط التحسين
    ========================================================= */

    const improvementForms = document.querySelectorAll(
        ".analysis-improvement-form"
    );

    improvementForms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector("button");

            if (!button) {
                return;
            }

            button.disabled = true;
            button.textContent = "جاري الإنشاء...";
        });
    });


    /* =========================================================
       الطباعة
    ========================================================= */

    const printButtons = document.querySelectorAll(
        "[data-analysis-print]"
    );

    printButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            renderAnalysisTemporalChart();

            window.setTimeout(function () {
                window.print();
            }, 100);
        });
    });


    /* =========================================================
       تحويل القيم النصية إلى أرقام
    ========================================================= */

    function parseChartNumber(value) {
        const normalizedValue = String(
            value === undefined || value === null
                ? ""
                : value
        )
            .replace("%", "")
            .replace(",", ".")
            .trim();

        const number = parseFloat(normalizedValue);

        return Number.isFinite(number)
            ? number
            : null;
    }


    /* =========================================================
       قراءة لون مفتاح الرسم
    ========================================================= */

    function getLegendColor(
        selector,
        fallbackColor
    ) {
        const legendItem =
            document.querySelector(selector);

        if (!legendItem) {
            return fallbackColor;
        }

        const computedStyle =
            window.getComputedStyle(legendItem);

        const backgroundColor =
            computedStyle.backgroundColor;

        const borderColor =
            computedStyle.borderColor;

        if (
            backgroundColor &&
            backgroundColor !== "transparent" &&
            backgroundColor !== "rgba(0, 0, 0, 0)"
        ) {
            return backgroundColor;
        }

        if (
            borderColor &&
            borderColor !== "transparent" &&
            borderColor !== "rgba(0, 0, 0, 0)"
        ) {
            return borderColor;
        }

        return fallbackColor;
    }


    /* =========================================================
       إنشاء عنصر SVG
    ========================================================= */

    function createSvgElement(tagName, attributes) {
        const element = document.createElementNS(
            "http://www.w3.org/2000/svg",
            tagName
        );

        Object.keys(attributes || {}).forEach(
            function (name) {
                element.setAttribute(
                    name,
                    attributes[name]
                );
            }
        );

        return element;
    }


    /* =========================================================
       رسم مقارنة العام الحالي بالعام السابق
    ========================================================= */

    function renderAnalysisTemporalChart() {
        const svg = document.getElementById(
            "analysisTemporalChart"
        );

        const dataContainer = document.getElementById(
            "analysisTemporalData"
        );

        if (!svg || !dataContainer) {
            return;
        }

        const chartPanel = svg.closest(
            ".analysis-tab-panel"
        );

        /*
         * لا يتم الرسم أثناء إخفاء تبويب الرسوم.
         */
        if (
            chartPanel &&
            (
                chartPanel.hidden ||
                window.getComputedStyle(
                    chartPanel
                ).display === "none"
            )
        ) {
            return;
        }

        const rows = Array.from(
            dataContainer.querySelectorAll("span")
        )
            .map(function (item, index) {
                return {
                    number:
                        item.dataset.number ||
                        String(index + 1),

                    label:
                        item.dataset.label ||
                        "المعيار " + (index + 1),

                    current:
                        parseChartNumber(
                            item.dataset.current
                        ),

                    previous:
                        parseChartNumber(
                            item.dataset.previous
                        )
                };
            })
            .filter(function (item) {
                return (
                    item.current !== null ||
                    item.previous !== null
                );
            });

        svg.innerHTML = "";

        if (!rows.length) {
            const emptyText = createSvgElement(
                "text",
                {
                    x: "410",
                    y: "160",
                    "text-anchor": "middle",
                    fill: "#6f8292",
                    "font-size": "15"
                }
            );

            emptyText.textContent =
                "لا توجد درجات صالحة لرسم المقارنة";

            svg.appendChild(emptyText);

            return;
        }

        const width = 820;
        const height = 320;

        const margin = {
            top: 28,
            right: 30,
            bottom: 58,
            left: 60
        };

        const chartWidth =
            width -
            margin.left -
            margin.right;

        const chartHeight =
            height -
            margin.top -
            margin.bottom;

        const maximumScore = 5;

        svg.setAttribute(
            "viewBox",
            "0 0 " + width + " " + height
        );

        svg.setAttribute(
            "preserveAspectRatio",
            "xMidYMid meet"
        );

        const currentColor = getLegendColor(
            ".analysis-line-legend .is-current",
            "#2f96df"
        );

        const previousColor = getLegendColor(
            ".analysis-line-legend .is-previous",
            "#9fb8c3"
        );

        function getX(index) {
            if (rows.length === 1) {
                return (
                    margin.left +
                    chartWidth / 2
                );
            }

            return (
                margin.left +
                (
                    index /
                    (rows.length - 1)
                ) *
                chartWidth
            );
        }

        function getY(value) {
            const safeValue = Math.max(
                0,
                Math.min(
                    maximumScore,
                    value
                )
            );

            return (
                margin.top +
                chartHeight -
                (
                    safeValue /
                    maximumScore
                ) *
                chartHeight
            );
        }


        /* =====================================================
           خلفية الرسم
        ===================================================== */

        svg.appendChild(
            createSvgElement("rect", {
                x: "0",
                y: "0",
                width: String(width),
                height: String(height),
                fill: "transparent"
            })
        );


        /* =====================================================
           خطوط الشبكة وأرقام محور الدرجات
        ===================================================== */

        const gridGroup = createSvgElement(
            "g",
            {
                "aria-hidden": "true"
            }
        );

        for (
            let value = 0;
            value <= maximumScore;
            value += 1
        ) {
            const y = getY(value);

            gridGroup.appendChild(
                createSvgElement("line", {
                    x1: margin.left,
                    y1: y,

                    x2:
                        width -
                        margin.right,

                    y2: y,

                    stroke: "#e3edf4",

                    "stroke-width": "1"
                })
            );

            const yLabel = createSvgElement(
                "text",
                {
                    x:
                        margin.left -
                        12,

                    y: y + 4,

                    "text-anchor": "end",

                    fill: "#718596",

                    "font-size": "12"
                }
            );

            yLabel.textContent =
                String(value);

            gridGroup.appendChild(yLabel);
        }

        svg.appendChild(gridGroup);


        /* =====================================================
           المحور الأفقي
        ===================================================== */

        svg.appendChild(
            createSvgElement("line", {
                x1: margin.left,

                y1:
                    margin.top +
                    chartHeight,

                x2:
                    width -
                    margin.right,

                y2:
                    margin.top +
                    chartHeight,

                stroke: "#c9d9e4",

                "stroke-width": "1.2"
            })
        );


        /* =====================================================
           المحور الرأسي
        ===================================================== */

        svg.appendChild(
            createSvgElement("line", {
                x1: margin.left,
                y1: margin.top,

                x2: margin.left,

                y2:
                    margin.top +
                    chartHeight,

                stroke: "#c9d9e4",

                "stroke-width": "1.2"
            })
        );


        /* =====================================================
           عنوان محور الدرجات
        ===================================================== */

        const axisCenter =
            margin.top +
            chartHeight / 2;

        const axisTitle = createSvgElement(
            "text",
            {
                x: "18",

                y: String(axisCenter),

                transform:
                    "rotate(-90 18 " +
                    axisCenter +
                    ")",

                "text-anchor": "middle",

                fill: "#718596",

                "font-size": "12"
            }
        );

        axisTitle.textContent =
            "الدرجة من 5";

        svg.appendChild(axisTitle);


        /* =====================================================
           أسماء المعايير أسفل الرسم
        ===================================================== */

        rows.forEach(function (item, index) {
            const x = getX(index);

            svg.appendChild(
                createSvgElement("line", {
                    x1: x,

                    y1:
                        margin.top +
                        chartHeight,

                    x2: x,

                    y2:
                        margin.top +
                        chartHeight +
                        6,

                    stroke: "#c9d9e4",

                    "stroke-width": "1"
                })
            );

            const xLabel = createSvgElement(
                "text",
                {
                    x: x,

                    y:
                        margin.top +
                        chartHeight +
                        26,

                    "text-anchor": "middle",

                    fill: "#607789",

                    "font-size": "12"
                }
            );

            xLabel.textContent =
                "م" + item.number;

            const title =
                createSvgElement("title");

            title.textContent =
                item.label;

            xLabel.appendChild(title);

            svg.appendChild(xLabel);
        });


        /* =====================================================
           تكوين بيانات الخطوط
        ===================================================== */

        function buildSeries(key) {
            const points = rows
                .map(function (item, index) {
                    const value = item[key];

                    if (value === null) {
                        return null;
                    }

                    return {
                        x: getX(index),
                        y: getY(value),
                        value: value,
                        item: item
                    };
                })
                .filter(function (point) {
                    return point !== null;
                });

            const pathData = points
                .map(function (point, index) {
                    const command =
                        index === 0
                            ? "M"
                            : "L";

                    return (
                        command +
                        " " +
                        point.x +
                        " " +
                        point.y
                    );
                })
                .join(" ");

            return {
                points: points,
                pathData: pathData
            };
        }


        /* =====================================================
           رسم الخط والنقاط
        ===================================================== */

        function drawSeries(
            key,
            color,
            label
        ) {
            const series =
                buildSeries(key);

            if (!series.points.length) {
                return;
            }

            if (series.points.length > 1) {
                svg.appendChild(
                    createSvgElement(
                        "path",
                        {
                            d:
                                series.pathData,

                            fill: "none",

                            stroke: color,

                            "stroke-width": "3",

                            "stroke-linecap":
                                "round",

                            "stroke-linejoin":
                                "round"
                        }
                    )
                );
            }

            series.points.forEach(
                function (point) {
                    const circle =
                        createSvgElement(
                            "circle",
                            {
                                cx: point.x,
                                cy: point.y,

                                r: "5",

                                fill: "#ffffff",

                                stroke: color,

                                "stroke-width": "3",

                                tabindex: "0"
                            }
                        );

                    const title =
                        createSvgElement(
                            "title"
                        );

                    title.textContent =
                        point.item.label +
                        " — " +
                        label +
                        ": " +
                        point.value +
                        " من 5";

                    circle.appendChild(title);

                    svg.appendChild(circle);

                    const valueText =
                        createSvgElement(
                            "text",
                            {
                                x: point.x,

                                y:
                                    point.y -
                                    11,

                                "text-anchor":
                                    "middle",

                                fill: color,

                                "font-size":
                                    "11",

                                "font-weight":
                                    "700"
                            }
                        );

                    valueText.textContent =
                        String(point.value);

                    svg.appendChild(valueText);
                }
            );
        }

        /*
         * رسم العام السابق أولًا،
         * ثم العام الحالي فوقه.
         */
        drawSeries(
            "previous",
            previousColor,
            "العام السابق"
        );

        drawSeries(
            "current",
            currentColor,
            "العام الحالي"
        );
    }

    window.renderAnalysisTemporalChart =
        renderAnalysisTemporalChart;


    /* =========================================================
       إعادة رسم المخطط عند فتح تبويب الرسوم
    ========================================================= */

    const chartsTabButton = document.querySelector(
        '[data-analysis-tab="charts"]'
    );

    if (chartsTabButton) {
        chartsTabButton.addEventListener(
            "click",
            function () {
                window.setTimeout(function () {
                    renderAnalysisTemporalChart();
                }, 80);
            }
        );
    }


    /* =========================================================
       فتح الصفحة مباشرة على تبويب الرسوم
    ========================================================= */

    if (
        window.location.hash ===
        "#analysis-charts"
    ) {
        window.setTimeout(function () {
            renderAnalysisTemporalChart();
        }, 160);
    }


    /* =========================================================
       إعادة الرسم عند تغيير رابط التبويب
    ========================================================= */

    window.addEventListener(
        "hashchange",
        function () {
            if (
                window.location.hash ===
                "#analysis-charts"
            ) {
                window.setTimeout(function () {
                    renderAnalysisTemporalChart();
                }, 80);
            }
        }
    );


    /* =========================================================
       إعادة الرسم عند تغيير حجم الشاشة
    ========================================================= */

    let resizeTimer = null;

    window.addEventListener(
        "resize",
        function () {
            window.clearTimeout(resizeTimer);

            resizeTimer =
                window.setTimeout(
                    function () {
                        renderAnalysisTemporalChart();
                    },
                    120
                );
        }
    );


    /* =========================================================
       ضبط خطوط التقدم في الجداول
    ========================================================= */

    const progressBars = document.querySelectorAll(
        ".analysis-current-progress, " +
        ".analysis-table-progress"
    );

    progressBars.forEach(function (track) {
        const rawValue =
            track.getAttribute("data-progress") ||
            track.style.getPropertyValue(
                "--progress-width"
            ) ||
            "0";

        const normalizedValue =
            String(rawValue)
                .replace("%", "")
                .replace(",", ".")
                .trim();

        let value =
            parseFloat(normalizedValue);

        if (!Number.isFinite(value)) {
            value = 0;
        }

        value = Math.max(
            0,
            Math.min(100, value)
        );

        track.style.setProperty(
            "--progress-width",
            value + "%"
        );

        const fill =
            track.querySelector(
                ".analysis-current-progress-fill"
            ) ||
            track.querySelector(
                ".analysis-table-progress-fill"
            ) ||
            track.querySelector("span");

        if (fill) {
            fill.style.setProperty(
                "width",
                value + "%",
                "important"
            );
        }
    });
});