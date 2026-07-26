document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const evaluationPage =
        document.querySelector(".evaluation-page");

    const isLoadDraft =
        evaluationPage &&
        evaluationPage.getAttribute("data-load-draft") === "1";

    const tabs =
        document.querySelectorAll(".ev-tab");

    const panels =
        document.querySelectorAll(".ev-standard-panel");

    const modeInput =
        document.getElementById("evaluationModeInput");

    const autoModeBtn =
        document.getElementById("useAutoModeBtn");

    const manualModeBtn =
        document.getElementById("useManualModeBtn");

    const reviewForm =
        document.getElementById("reviewForm");

    const activeStandardInput =
        document.getElementById("activeStandardIdInput");

    const standardReviewInput =
        document.getElementById("standardReviewIdInput");

    const confirmModal =
        document.getElementById("evConfirmModal");

    const confirmTitle =
        document.getElementById("evConfirmTitle");

    const confirmMessage =
        document.getElementById("evConfirmMessage");

    const confirmIcon =
        document.getElementById("evConfirmIcon");

    const confirmOk =
        document.getElementById("evConfirmOk");

    const confirmCancel =
        document.getElementById("evConfirmCancel");

    let pendingConfirmCallback = null;
    let approveAllowed = false;

    function normalizeInputsDirection() {
        document.querySelectorAll(
            ".ev-field textarea, " +
            ".ev-field input, " +
            ".ev-field select, " +
            ".ev-table textarea, " +
            ".ev-table select, " +
            ".ev-general-notes textarea"
        ).forEach(function (field) {
            field.setAttribute("dir", "rtl");
            field.style.textAlign = "right";
        });
    }

    function autoResizeTextarea(textarea) {
        if (!textarea) {
            return;
        }

        textarea.style.height = "auto";

        textarea.style.height =
            Math.max(
                textarea.scrollHeight,
                84
            ) + "px";
    }

    function resizeAllTextareas() {
        document
            .querySelectorAll("textarea")
            .forEach(function (textarea) {
                autoResizeTextarea(textarea);
            });
    }

    function resizePanelTextareas(panel) {
        if (!panel) {
            return;
        }

        panel
            .querySelectorAll("textarea")
            .forEach(function (textarea) {
                autoResizeTextarea(textarea);
            });
    }

    function getActivePanel() {
        return (
            document.querySelector(
                ".ev-standard-panel.active"
            ) ||
            panels[0] ||
            null
        );
    }

    function getPanelStandardId(panel) {
        if (!panel) {
            return "";
        }

        return (
            panel.getAttribute(
                "data-standard-review-id"
            ) || ""
        );
    }

    function syncActiveStandard(panel) {
        const activePanel =
            panel || getActivePanel();

        const standardId =
            getPanelStandardId(activePanel);

        if (activeStandardInput) {
            activeStandardInput.value =
                standardId;
        }

        if (standardReviewInput) {
            standardReviewInput.value =
                standardId;
        }

        return standardId;
    }

    function openConfirm(
        options,
        callback
    ) {
        if (
            !confirmModal ||
            !confirmTitle ||
            !confirmMessage ||
            !confirmOk ||
            !confirmCancel
        ) {
            callback(true);
            return;
        }

        pendingConfirmCallback =
            callback;

        confirmTitle.textContent =
            options.title ||
            "تأكيد الإجراء";

        confirmMessage.textContent =
            options.message ||
            "هل تريدين المتابعة؟";

        confirmOk.textContent =
            options.confirmText ||
            "متابعة";

        confirmCancel.textContent =
            options.cancelText ||
            "إلغاء";

        if (confirmIcon) {
            confirmIcon.textContent =
                options.icon || "!";

            confirmIcon.className =
                "ev-confirm-icon " +
                (options.type || "info");
        }

        confirmModal.classList.add(
            "active"
        );

        confirmModal.setAttribute(
            "aria-hidden",
            "false"
        );

        setTimeout(function () {
            confirmOk.focus();
        }, 50);
    }

    function closeConfirm(result) {
        if (!confirmModal) {
            return;
        }

        confirmModal.classList.remove(
            "active"
        );

        confirmModal.setAttribute(
            "aria-hidden",
            "true"
        );

        if (
            typeof pendingConfirmCallback ===
            "function"
        ) {
            const callback =
                pendingConfirmCallback;

            pendingConfirmCallback =
                null;

            callback(result);
        }
    }

    if (confirmOk) {
        confirmOk.addEventListener(
            "click",
            function () {
                closeConfirm(true);
            }
        );
    }

    if (confirmCancel) {
        confirmCancel.addEventListener(
            "click",
            function () {
                closeConfirm(false);
            }
        );
    }

    document
        .querySelectorAll(
            "[data-ev-close-modal]"
        )
        .forEach(function (item) {
            item.addEventListener(
                "click",
                function () {
                    closeConfirm(false);
                }
            );
        });

    document.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key === "Escape" &&
                confirmModal &&
                confirmModal.classList.contains(
                    "active"
                )
            ) {
                closeConfirm(false);
            }
        }
    );

    function activatePanel(tab) {
        const targetId =
            tab.getAttribute(
                "data-target"
            );

        tabs.forEach(
            function (item) {
                item.classList.remove(
                    "active"
                );
            }
        );

        panels.forEach(
            function (panel) {
                panel.classList.remove(
                    "active"
                );
            }
        );

        tab.classList.add("active");

        const targetPanel =
            document.getElementById(
                targetId
            );

        if (targetPanel) {
            targetPanel.classList.add(
                "active"
            );

            syncActiveStandard(
                targetPanel
            );

            resizePanelTextareas(
                targetPanel
            );
        }
    }

    tabs.forEach(function (tab) {
        tab.addEventListener(
            "click",
            function () {
                activatePanel(tab);
            }
        );
    });

    function setActiveMode(mode) {
        if (
            !modeInput ||
            !autoModeBtn ||
            !manualModeBtn
        ) {
            return;
        }

        modeInput.value = mode;

        autoModeBtn.classList.toggle(
            "active",
            mode === "auto"
        );

        manualModeBtn.classList.toggle(
            "active",
            mode === "manual"
        );

        document.body.classList.toggle(
            "evaluation-auto-mode",
            mode === "auto"
        );

        document.body.classList.toggle(
            "evaluation-manual-mode",
            mode === "manual"
        );

        normalizeInputsDirection();
        resizeAllTextareas();
    }

    function markScoreGap(select) {
        const autoScore = parseInt(
            select.getAttribute(
                "data-auto-score"
            ) || "0",
            10
        );

        const reviewerScore = parseInt(
            select.value || "0",
            10
        );

        select.classList.remove(
            "ev-gap-warning"
        );

        if (
            autoScore &&
            reviewerScore &&
            Math.abs(
                autoScore -
                reviewerScore
            ) >= 2
        ) {
            select.classList.add(
                "ev-gap-warning"
            );
        }
    }

    function buildStrengths(panel) {
        const strengths = [];

        panel
            .querySelectorAll(
                ".js-indicator-row"
            )
            .forEach(function (row) {
                const score = parseInt(
                    row.getAttribute(
                        "data-auto-score"
                    ) || "0",
                    10
                );

                const text =
                    row.getAttribute(
                        "data-indicator-text"
                    ) || "";

                /*
                 * الدرجة 3 فأكثر تعتبر
                 * مؤشرًا مستوفى وتظهر
                 * في نقاط القوة.
                 */
                if (
                    score >= 3 &&
                    text
                ) {
                    strengths.push(
                        "• " + text
                    );
                }
            });

        if (
            strengths.length === 0
        ) {
            return (
                "لا توجد نقاط قوة آلية واضحة " +
                "بناءً على نتائج المؤشرات الحالية."
            );
        }

        return strengths.join("\n");
    }

    function convertIndicatorToWeakness(
        text
    ) {
        const cleanText =
            String(
                text || ""
            ).trim();

        if (!cleanText) {
            return "";
        }

        /*
         * تحويل صياغة المؤشر الإيجابية
         * إلى صياغة ضعف منطقية.
         */
        const replacements = [
            [
                "تتوفر",
                "عدم توفر"
            ],
            [
                "يتوفر",
                "عدم توفر"
            ],
            [
                "توجد",
                "عدم وجود"
            ],
            [
                "يوجد",
                "عدم وجود"
            ],
            [
                "يمتلك",
                "عدم امتلاك"
            ],
            [
                "يملك",
                "عدم امتلاك"
            ],
            [
                "تتسق",
                "عدم اتساق"
            ],
            [
                "يلتزم",
                "عدم الالتزام بـ"
            ],
            [
                "تم إعداد",
                "عدم استكمال إعداد"
            ],
            [
                "هناك قياس",
                "عدم توفر قياس"
            ],
            [
                "اكتمال",
                "عدم اكتمال"
            ],
            [
                "توفر",
                "عدم توفر"
            ]
        ];

        for (
            const replacement
            of replacements
        ) {
            const source =
                replacement[0];

            const target =
                replacement[1];

            if (
                cleanText.startsWith(
                    source
                )
            ) {
                return (
                    target +
                    cleanText.slice(
                        source.length
                    )
                );
            }
        }

        return (
            "عدم استيفاء المؤشر: " +
            cleanText
        );
    }

    function buildWeaknesses(panel) {
        const weaknesses = [];

        panel
            .querySelectorAll(
                ".js-indicator-row"
            )
            .forEach(function (row) {
                const score = parseInt(
                    row.getAttribute(
                        "data-auto-score"
                    ) || "0",
                    10
                );

                const text =
                    row.getAttribute(
                        "data-indicator-text"
                    ) || "";

                /*
                 * الدرجة 1 أو 2
                 * تعتبر نقطة ضعف.
                 */
                if (
                    score <= 2 &&
                    text
                ) {
                    const weaknessText =
                        convertIndicatorToWeakness(
                            text
                        );

                    if (
                        weaknessText
                    ) {
                        weaknesses.push(
                            "• " +
                            weaknessText
                        );
                    }
                }
            });

        if (
            weaknesses.length === 0
        ) {
            return (
                "لا توجد نقاط ضعف آلية واضحة " +
                "بناءً على نتائج المؤشرات الحالية."
            );
        }

        return weaknesses.join("\n");
    }

    function convertIndicatorToImprovement(
        text
    ) {
        const cleanText =
            String(
                text || ""
            ).trim();

        if (!cleanText) {
            return "";
        }

        /*
         * الرسالة والأهداف.
         */
        if (
            cleanText.includes(
                "رسالة"
            )
        ) {
            return (
                "مراجعة رسالة البرنامج واستكمال اعتمادها، " +
                "والتأكد من اتساقها مع رسالة الكلية والجامعة."
            );
        }

        if (
            cleanText.includes(
                "أهداف البرنامج"
            ) ||
            cleanText.includes(
                "أهداف وخطط"
            )
        ) {
            return (
                "استكمال إعداد أهداف البرنامج واعتمادها، " +
                "وربطها برسالة البرنامج والخطة التنفيذية."
            );
        }

        if (
            cleanText.includes(
                "خطة تنفيذية"
            ) ||
            cleanText.includes(
                "الخطة التنفيذية"
            )
        ) {
            return (
                "إعداد خطة تنفيذية واضحة للبرنامج، " +
                "تتضمن الأنشطة والمسؤوليات ومؤشرات الأداء " +
                "والمدة الزمنية للتنفيذ."
            );
        }

        /*
         * مخرجات التعلم.
         */
        if (
            cleanText.includes(
                "مخرجات التعلم"
            ) ||
            cleanText.includes(
                "مخرجات تعلم"
            )
        ) {
            return (
                "استكمال صياغة مخرجات التعلم وقياسها، " +
                "وتوثيق نتائج القياس وخطط التحسين المرتبطة بها."
            );
        }

        /*
         * الخطة الدراسية والمقررات.
         */
        if (
            cleanText.includes(
                "الخطة الدراسية"
            ) ||
            cleanText.includes(
                "المقررات"
            ) ||
            cleanText.includes(
                "توصيف"
            )
        ) {
            return (
                "مراجعة الخطة الدراسية واستكمال بيانات المقررات " +
                "والساعات المعتمدة والتوصيفات المطلوبة."
            );
        }

        /*
         * الطلبة والخريجون.
         */
        if (
            cleanText.includes(
                "الطلبة"
            ) ||
            cleanText.includes(
                "الخريجين"
            ) ||
            cleanText.includes(
                "النجاح"
            ) ||
            cleanText.includes(
                "المعدل التراكمي"
            ) ||
            cleanText.includes(
                "التقدم"
            ) ||
            cleanText.includes(
                "البقاء"
            ) ||
            cleanText.includes(
                "الانسحاب"
            )
        ) {
            return (
                "استكمال بيانات الطلبة والخريجين ومؤشرات الأداء، " +
                "والتحقق من دقتها وتحديثها بصورة دورية."
            );
        }

        /*
         * القاعات والمعامل.
         */
        if (
            cleanText.includes(
                "القاعات"
            ) ||
            cleanText.includes(
                "المختبرات"
            ) ||
            cleanText.includes(
                "المعامل"
            ) ||
            cleanText.includes(
                "البنية التحتية"
            )
        ) {
            return (
                "استكمال بيانات القاعات والمعامل والتجهيزات، " +
                "ومعالجة أوجه النقص وفق الطاقة الاستيعابية للبرنامج."
            );
        }

        /*
         * المكتبة ومصادر التعلم.
         */
        if (
            cleanText.includes(
                "المكتبة"
            ) ||
            cleanText.includes(
                "المراجع"
            ) ||
            cleanText.includes(
                "مصادر"
            )
        ) {
            return (
                "استكمال بيانات المكتبة ومصادر التعلم والمراجع، " +
                "وتحديثها بما يتناسب مع احتياجات البرنامج."
            );
        }

        /*
         * رضا المستفيدين والعملية التعليمية.
         */
        if (
            cleanText.includes(
                "رضا"
            ) ||
            cleanText.includes(
                "العملية التعليمية"
            ) ||
            cleanText.includes(
                "العملية الامتحانية"
            ) ||
            cleanText.includes(
                "أداء أعضاء هيئة التدريس"
            )
        ) {
            return (
                "استكمال جمع وتحليل نتائج التقييم والرضا، " +
                "ووضع إجراءات تحسين موثقة ومتابعة تنفيذها."
            );
        }

        /*
         * بيانات البرنامج الأساسية.
         */
        if (
            cleanText.includes(
                "معلومات البرنامج"
            ) ||
            cleanText.includes(
                "مسؤول البرنامج"
            ) ||
            cleanText.includes(
                "الطاقة الاستيعابية"
            ) ||
            cleanText.includes(
                "معايير قبول"
            )
        ) {
            return (
                "استكمال المعلومات الأساسية للبرنامج، " +
                "ومراجعتها والتحقق من دقتها واعتمادها رسميًا."
            );
        }

        /*
         * خطة احتياطية لأي مؤشر
         * لا تنطبق عليه الحالات السابقة.
         */
        return (
            "استكمال البيانات والإجراءات اللازمة لتحقيق المؤشر: " +
            cleanText
        );
    }

    function buildImprovementPlan(
        panel
    ) {
        const improvementItems =
            [];

        panel
            .querySelectorAll(
                ".js-indicator-row"
            )
            .forEach(function (row) {
                const score = parseInt(
                    row.getAttribute(
                        "data-auto-score"
                    ) || "0",
                    10
                );

                const text =
                    row.getAttribute(
                        "data-indicator-text"
                    ) || "";

                if (
                    score <= 2 &&
                    text
                ) {
                    const improvementText =
                        convertIndicatorToImprovement(
                            text
                        );

                    const formattedItem =
                        "• " +
                        improvementText;

                    /*
                     * منع تكرار نفس خطة
                     * التحسين أكثر من مرة.
                     */
                    if (
                        improvementText &&
                        !improvementItems.includes(
                            formattedItem
                        )
                    ) {
                        improvementItems.push(
                            formattedItem
                        );
                    }
                }
            });

        if (
            improvementItems.length ===
            0
        ) {
            return (
                "المحافظة على مستوى استيفاء المؤشرات، " +
                "مع المتابعة والتحديث الدوري للبيانات."
            );
        }

        return improvementItems.join(
            "\n"
        );
    }

    function fillAutoModeForPanel(
        panel
    ) {
        if (!panel) {
            return;
        }

        const standardScore =
            panel.querySelector(
                ".js-standard-score"
            );

        const standardNotes =
            panel.querySelector(
                ".js-standard-notes"
            );

        const strengths =
            panel.querySelector(
                ".js-strengths"
            );

        const weaknesses =
            panel.querySelector(
                ".js-weaknesses"
            );

        const improvementPlan =
            panel.querySelector(
                ".js-improvement-plan"
            );

        const executionTime =
            panel.querySelector(
                ".js-execution-time"
            );

        /*
         * تعبئة درجة المعيار
         * من درجة النظام.
         */
        if (standardScore) {
            const autoScore =
                standardScore.getAttribute(
                    "data-auto-score"
                );

            standardScore.value =
                autoScore || "";

            markScoreGap(
                standardScore
            );
        }

        /*
         * لا يتم نسخ ملاحظة النظام
         * إلى ملاحظة المراجع.
         */
        if (standardNotes) {
            standardNotes.value = "";

            autoResizeTextarea(
                standardNotes
            );
        }

        /*
         * تعبئة نقاط القوة.
         */
        if (strengths) {
            strengths.value =
                buildStrengths(panel);

            autoResizeTextarea(
                strengths
            );
        }

        /*
         * تعبئة نقاط الضعف
         * بصياغة سلبية منطقية.
         */
        if (weaknesses) {
            weaknesses.value =
                buildWeaknesses(panel);

            autoResizeTextarea(
                weaknesses
            );
        }

        /*
         * تعبئة خطة التحسين.
         */
        if (improvementPlan) {
            improvementPlan.value =
                buildImprovementPlan(
                    panel
                );

            autoResizeTextarea(
                improvementPlan
            );
        }

        /*
         * تحديد زمن التنفيذ بناء
         * على وجود نقاط ضعف.
         */
        if (executionTime) {
            const hasWeakIndicators =
                Array.from(
                    panel.querySelectorAll(
                        ".js-indicator-row"
                    )
                ).some(
                    function (row) {
                        const score =
                            parseInt(
                                row.getAttribute(
                                    "data-auto-score"
                                ) || "0",
                                10
                            );

                        return (
                            score <= 2
                        );
                    }
                );

            executionTime.value =
                hasWeakIndicators
                    ? "خلال الفصل القادم"
                    : "متابعة دورية";
        }

        /*
         * تعبئة درجات المؤشرات
         * بنتائج التقييم الآلي.
         */
        panel
            .querySelectorAll(
                ".js-indicator-score"
            )
            .forEach(
                function (select) {
                    const autoScore =
                        select.getAttribute(
                            "data-auto-score"
                        );

                    select.value =
                        autoScore || "";
                }
            );

        /*
         * ملاحظات المراجع للمؤشرات
         * تظل فارغة.
         */
        panel
            .querySelectorAll(
                ".js-indicator-notes"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );
    }

    /*
     * تطبيق التقييم الآلي
     * على جميع المعايير.
     */
    function fillAutoModeForAllStandards() {
        panels.forEach(
            function (panel) {
                fillAutoModeForPanel(
                    panel
                );
            }
        );

        syncActiveStandard(
            getActivePanel()
        );

        setActiveMode("auto");

        resizeAllTextareas();
    }

    /*
     * تفريغ المعيار المفتوح فقط
     * عند اختيار الوضع اليدوي.
     */
    function clearManualModeForActiveStandard() {
        const panel =
            getActivePanel();

        if (!panel) {
            return;
        }

        panel
            .querySelectorAll(
                ".js-standard-score"
            )
            .forEach(
                function (select) {
                    select.value = "";

                    markScoreGap(
                        select
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-standard-notes"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-indicator-score"
            )
            .forEach(
                function (select) {
                    select.value = "";
                }
            );

        panel
            .querySelectorAll(
                ".js-indicator-notes"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-strengths"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-weaknesses"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-improvement-plan"
            )
            .forEach(
                function (textarea) {
                    textarea.value =
                        "";

                    autoResizeTextarea(
                        textarea
                    );
                }
            );

        panel
            .querySelectorAll(
                ".js-execution-time"
            )
            .forEach(
                function (input) {
                    input.value = "";
                }
            );

        syncActiveStandard(panel);

        setActiveMode("manual");
    }

    function openDraftEditLinks() {
        document
            .querySelectorAll(
                ".ev-draft-edit-btn"
            )
            .forEach(
                function (link) {
                    link.addEventListener(
                        "click",
                        function (event) {
                            const href =
                                link.getAttribute(
                                    "href"
                                );

                            if (href) {
                                event.preventDefault();

                                window.location.href =
                                    href;
                            }
                        }
                    );
                }
            );
    }

    /*
     * زر التقييم الآلي:
     * يطبق التقييم على جميع المعايير.
     */
    if (autoModeBtn) {
        autoModeBtn.addEventListener(
            "click",
            function () {
                openConfirm(
                    {
                        title:
                            "استخدام التقييم الآلي",

                        message:
                            "سيتم تعبئة درجات جميع المعايير والمؤشرات، " +
                            "ونقاط القوة والضعف وخطط التحسين وفق نتائج النظام. " +
                            "أما ملاحظات المراجع فستبقى فارغة لتعبئتها يدويًا.",

                        confirmText:
                            "استخدام التقييم الآلي",

                        cancelText:
                            "إلغاء",

                        icon:
                            "✓",

                        type:
                            "success"
                    },
                    function (
                        confirmed
                    ) {
                        if (
                            confirmed
                        ) {
                            fillAutoModeForAllStandards();
                        }
                    }
                );
            }
        );
    }

    /*
     * زر التقييم اليدوي:
     * يفرغ المعيار المفتوح فقط.
     */
    if (manualModeBtn) {
        manualModeBtn.addEventListener(
            "click",
            function () {
                openConfirm(
                    {
                        title:
                            "بدء تقييم يدوي فارغ للمعيار الحالي",

                        message:
                            "سيتم تفريغ حقول المعيار المفتوح فقط، " +
                            "ولن تتأثر بقية المعايير أو المسودات.",

                        confirmText:
                            "بدء تقييم يدوي",

                        cancelText:
                            "إلغاء",

                        icon:
                            "!",

                        type:
                            "warning"
                    },
                    function (
                        confirmed
                    ) {
                        if (
                            confirmed
                        ) {
                            clearManualModeForActiveStandard();
                        }
                    }
                );
            }
        );
    }

    document
        .querySelectorAll(
            ".review-score-select"
        )
        .forEach(
            function (select) {
                markScoreGap(select);

                select.addEventListener(
                    "change",
                    function () {
                        markScoreGap(
                            select
                        );
                    }
                );
            }
        );

    document
        .querySelectorAll(
            "textarea"
        )
        .forEach(
            function (textarea) {
                autoResizeTextarea(
                    textarea
                );

                textarea.addEventListener(
                    "input",
                    function () {
                        autoResizeTextarea(
                            textarea
                        );
                    }
                );
            }
        );

    if (reviewForm) {
        reviewForm.addEventListener(
            "submit",
            function (event) {
                const activePanel =
                    getActivePanel();

                const activeStandardId =
                    syncActiveStandard(
                        activePanel
                    );

                const submitter =
                    event.submitter;

                if (
                    !activeStandardId
                ) {
                    event.preventDefault();

                    openConfirm(
                        {
                            title:
                                "لم يتم تحديد معيار",

                            message:
                                "افتحي المعيار المطلوب حفظه أولًا، " +
                                "ثم اضغطي حفظ كمسودة أو اعتماد.",

                            confirmText:
                                "حسنًا",

                            cancelText:
                                "إلغاء",

                            icon:
                                "!",

                            type:
                                "warning"
                        },
                        function () {}
                    );

                    return;
                }

                if (
                    submitter &&
                    submitter.value ===
                        "approve" &&
                    !approveAllowed
                ) {
                    event.preventDefault();

                    openConfirm(
                        {
                            title:
                                "اعتماد المعيار الحالي",

                            message:
                                "سيتم اعتماد المعيار المفتوح فقط كنسخة نهائية. " +
                                "تأكدي من مراجعة درجته وملاحظاته قبل المتابعة.",

                            confirmText:
                                "اعتماد المعيار",

                            cancelText:
                                "إلغاء",

                            icon:
                                "✓",

                            type:
                                "success"
                        },
                        function (
                            confirmed
                        ) {
                            if (
                                confirmed
                            ) {
                                approveAllowed =
                                    true;

                                syncActiveStandard(
                                    getActivePanel()
                                );

                                if (
                                    reviewForm.requestSubmit
                                ) {
                                    reviewForm.requestSubmit(
                                        submitter
                                    );
                                } else {
                                    const actionInput =
                                        document.createElement(
                                            "input"
                                        );

                                    actionInput.type =
                                        "hidden";

                                    actionInput.name =
                                        "action";

                                    actionInput.value =
                                        "approve";

                                    reviewForm.appendChild(
                                        actionInput
                                    );

                                    reviewForm.submit();
                                }
                            }
                        }
                    );
                }
            }
        );
    }

    openDraftEditLinks();

    normalizeInputsDirection();

    syncActiveStandard(
        getActivePanel()
    );

    /*
     * عند فتح مسودة، يبقى الوضع
     * اليدوي حتى لا تتم الكتابة
     * فوق بيانات المراجع المحفوظة.
     */
    if (isLoadDraft) {
        setActiveMode("manual");
        resizeAllTextareas();
    } else {
        setActiveMode("manual");
    }
});