document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const evaluationPage = document.querySelector(".evaluation-page");
    const isLoadDraft = evaluationPage && evaluationPage.getAttribute("data-load-draft") === "1";

    const tabs = document.querySelectorAll(".ev-tab");
    const panels = document.querySelectorAll(".ev-standard-panel");

    const modeInput = document.getElementById("evaluationModeInput");
    const autoModeBtn = document.getElementById("useAutoModeBtn");
    const manualModeBtn = document.getElementById("useManualModeBtn");
    const reviewForm = document.getElementById("reviewForm");

    const activeStandardInput = document.getElementById("activeStandardIdInput");
    const standardReviewInput = document.getElementById("standardReviewIdInput");

    const confirmModal = document.getElementById("evConfirmModal");
    const confirmTitle = document.getElementById("evConfirmTitle");
    const confirmMessage = document.getElementById("evConfirmMessage");
    const confirmIcon = document.getElementById("evConfirmIcon");
    const confirmOk = document.getElementById("evConfirmOk");
    const confirmCancel = document.getElementById("evConfirmCancel");

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
        textarea.style.height = Math.max(textarea.scrollHeight, 84) + "px";
    }

    function resizeAllTextareas() {
        document.querySelectorAll("textarea").forEach(function (textarea) {
            autoResizeTextarea(textarea);
        });
    }

    function resizePanelTextareas(panel) {
        if (!panel) {
            return;
        }

        panel.querySelectorAll("textarea").forEach(function (textarea) {
            autoResizeTextarea(textarea);
        });
    }

    function getActivePanel() {
        return document.querySelector(".ev-standard-panel.active") || panels[0] || null;
    }

    function getPanelStandardId(panel) {
        if (!panel) {
            return "";
        }

        return panel.getAttribute("data-standard-review-id") || "";
    }

    function syncActiveStandard(panel) {
        const activePanel = panel || getActivePanel();
        const standardId = getPanelStandardId(activePanel);

        if (activeStandardInput) {
            activeStandardInput.value = standardId;
        }

        if (standardReviewInput) {
            standardReviewInput.value = standardId;
        }

        return standardId;
    }

    function openConfirm(options, callback) {
        if (!confirmModal || !confirmTitle || !confirmMessage || !confirmOk || !confirmCancel) {
            callback(true);
            return;
        }

        pendingConfirmCallback = callback;

        confirmTitle.textContent = options.title || "تأكيد الإجراء";
        confirmMessage.textContent = options.message || "هل تريدين المتابعة؟";
        confirmOk.textContent = options.confirmText || "متابعة";
        confirmCancel.textContent = options.cancelText || "إلغاء";

        if (confirmIcon) {
            confirmIcon.textContent = options.icon || "!";
            confirmIcon.className = "ev-confirm-icon " + (options.type || "info");
        }

        confirmModal.classList.add("active");
        confirmModal.setAttribute("aria-hidden", "false");

        setTimeout(function () {
            confirmOk.focus();
        }, 50);
    }

    function closeConfirm(result) {
        if (!confirmModal) {
            return;
        }

        confirmModal.classList.remove("active");
        confirmModal.setAttribute("aria-hidden", "true");

        if (typeof pendingConfirmCallback === "function") {
            const callback = pendingConfirmCallback;
            pendingConfirmCallback = null;
            callback(result);
        }
    }

    if (confirmOk) {
        confirmOk.addEventListener("click", function () {
            closeConfirm(true);
        });
    }

    if (confirmCancel) {
        confirmCancel.addEventListener("click", function () {
            closeConfirm(false);
        });
    }

    document.querySelectorAll("[data-ev-close-modal]").forEach(function (item) {
        item.addEventListener("click", function () {
            closeConfirm(false);
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && confirmModal && confirmModal.classList.contains("active")) {
            closeConfirm(false);
        }
    });

    function activatePanel(tab) {
        const targetId = tab.getAttribute("data-target");

        tabs.forEach(function (item) {
            item.classList.remove("active");
        });

        panels.forEach(function (panel) {
            panel.classList.remove("active");
        });

        tab.classList.add("active");

        const targetPanel = document.getElementById(targetId);

        if (targetPanel) {
            targetPanel.classList.add("active");
            syncActiveStandard(targetPanel);
            resizePanelTextareas(targetPanel);
        }
    }

    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            activatePanel(tab);
        });
    });

    function setActiveMode(mode) {
        if (!modeInput || !autoModeBtn || !manualModeBtn) {
            return;
        }

        modeInput.value = mode;

        autoModeBtn.classList.toggle("active", mode === "auto");
        manualModeBtn.classList.toggle("active", mode === "manual");

        document.body.classList.toggle("evaluation-auto-mode", mode === "auto");
        document.body.classList.toggle("evaluation-manual-mode", mode === "manual");

        normalizeInputsDirection();
        resizeAllTextareas();
    }

    function markScoreGap(select) {
        const autoScore = parseInt(select.getAttribute("data-auto-score") || "0", 10);
        const reviewerScore = parseInt(select.value || "0", 10);

        select.classList.remove("ev-gap-warning");

        if (autoScore && reviewerScore && Math.abs(autoScore - reviewerScore) >= 2) {
            select.classList.add("ev-gap-warning");
        }
    }

    function buildStrengths(panel) {
        const strengths = [];

        panel.querySelectorAll(".js-indicator-row").forEach(function (row) {
            const score = parseInt(row.getAttribute("data-auto-score") || "0", 10);
            const text = row.getAttribute("data-indicator-text") || "";

            if (score >= 4 && text) {
                strengths.push("• " + text);
            }
        });

        if (strengths.length === 0) {
            return "لا توجد نقاط قوة آلية واضحة بناءً على نتائج المؤشرات الحالية.";
        }

        return strengths.join("\n");
    }

    function buildWeaknesses(panel) {
        const weaknesses = [];

        panel.querySelectorAll(".js-indicator-row").forEach(function (row) {
            const score = parseInt(row.getAttribute("data-auto-score") || "0", 10);
            const text = row.getAttribute("data-indicator-text") || "";

            if (score <= 2 && text) {
                weaknesses.push("• " + text);
            }
        });

        if (weaknesses.length === 0) {
            return "لا توجد نقاط ضعف حرجة ظاهرة آليًا بناءً على نتائج المؤشرات الحالية.";
        }

        return weaknesses.join("\n");
    }

    function buildImprovementPlan(panel) {
        const weakItems = [];

        panel.querySelectorAll(".js-indicator-row").forEach(function (row) {
            const score = parseInt(row.getAttribute("data-auto-score") || "0", 10);
            const text = row.getAttribute("data-indicator-text") || "";

            if (score <= 2 && text) {
                weakItems.push("• استكمال وتحسين: " + text);
            }
        });

        if (weakItems.length === 0) {
            return "الاستمرار في المتابعة الدورية والحفاظ على مستوى استيفاء المؤشرات.";
        }

        return weakItems.join("\n");
    }

    function fillAutoModeForActiveStandard() {
        const panel = getActivePanel();

        if (!panel) {
            return;
        }

        const standardScore = panel.querySelector(".js-standard-score");
        const standardNotes = panel.querySelector(".js-standard-notes");
        const strengths = panel.querySelector(".js-strengths");
        const weaknesses = panel.querySelector(".js-weaknesses");
        const improvementPlan = panel.querySelector(".js-improvement-plan");
        const executionTime = panel.querySelector(".js-execution-time");

        if (standardScore) {
            const autoScore = standardScore.getAttribute("data-auto-score");
            standardScore.value = autoScore || "";
            markScoreGap(standardScore);
        }

        /*
           مهم:
           لا ننسخ ملاحظة النظام إلى ملاحظة المراجع.
           ملاحظات المراجع يجب أن تبقى فارغة حتى تعبئها المراجعة يدويًا.
        */
        if (standardNotes) {
            standardNotes.value = "";
            autoResizeTextarea(standardNotes);
        }

        if (strengths) {
            strengths.value = buildStrengths(panel);
            autoResizeTextarea(strengths);
        }

        if (weaknesses) {
            weaknesses.value = buildWeaknesses(panel);
            autoResizeTextarea(weaknesses);
        }

        if (improvementPlan) {
            improvementPlan.value = buildImprovementPlan(panel);
            autoResizeTextarea(improvementPlan);
        }

        if (executionTime && !executionTime.value) {
            executionTime.value = "خلال الفصل القادم";
        }

        panel.querySelectorAll(".js-indicator-score").forEach(function (select) {
            const autoScore = select.getAttribute("data-auto-score");
            select.value = autoScore || "";
        });

        /*
           مهم:
           لا ننسخ ملاحظات النظام الخاصة بالمؤشرات إلى ملاحظات المراجع.
        */
        panel.querySelectorAll(".js-indicator-notes").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        syncActiveStandard(panel);
        setActiveMode("auto");
    }

    function clearManualModeForActiveStandard() {
        const panel = getActivePanel();

        if (!panel) {
            return;
        }

        panel.querySelectorAll(".js-standard-score").forEach(function (select) {
            select.value = "";
            markScoreGap(select);
        });

        panel.querySelectorAll(".js-standard-notes").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        panel.querySelectorAll(".js-indicator-score").forEach(function (select) {
            select.value = "";
        });

        panel.querySelectorAll(".js-indicator-notes").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        panel.querySelectorAll(".js-strengths").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        panel.querySelectorAll(".js-weaknesses").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        panel.querySelectorAll(".js-improvement-plan").forEach(function (textarea) {
            textarea.value = "";
            autoResizeTextarea(textarea);
        });

        panel.querySelectorAll(".js-execution-time").forEach(function (input) {
            input.value = "";
        });

        syncActiveStandard(panel);
        setActiveMode("manual");
    }

    function openDraftEditLinks() {
        document.querySelectorAll(".ev-draft-edit-btn").forEach(function (link) {
            link.addEventListener("click", function (event) {
                const href = link.getAttribute("href");

                if (href) {
                    event.preventDefault();
                    window.location.href = href;
                }
            });
        });
    }

    if (autoModeBtn) {
        autoModeBtn.addEventListener("click", function () {
            openConfirm({
                title: "استخدام التقييم الآلي للمعيار الحالي",
                message: "سيتم تعبئة درجة المعيار ودرجات المؤشرات فقط بنتائج النظام، أما ملاحظات المراجع فستبقى فارغة لتعبئتها يدويًا.",
                confirmText: "استخدام التقييم الآلي",
                cancelText: "إلغاء",
                icon: "✓",
                type: "success"
            }, function (confirmed) {
                if (confirmed) {
                    fillAutoModeForActiveStandard();
                }
            });
        });
    }

    if (manualModeBtn) {
        manualModeBtn.addEventListener("click", function () {
            openConfirm({
                title: "بدء تقييم يدوي فارغ للمعيار الحالي",
                message: "سيتم تفريغ حقول المعيار المفتوح فقط، ولن تتأثر بقية المعايير أو المسودات.",
                confirmText: "بدء تقييم يدوي",
                cancelText: "إلغاء",
                icon: "!",
                type: "warning"
            }, function (confirmed) {
                if (confirmed) {
                    clearManualModeForActiveStandard();
                }
            });
        });
    }

    document.querySelectorAll(".review-score-select").forEach(function (select) {
        markScoreGap(select);

        select.addEventListener("change", function () {
            markScoreGap(select);
        });
    });

    document.querySelectorAll("textarea").forEach(function (textarea) {
        autoResizeTextarea(textarea);

        textarea.addEventListener("input", function () {
            autoResizeTextarea(textarea);
        });
    });

    if (reviewForm) {
        reviewForm.addEventListener("submit", function (event) {
            const activePanel = getActivePanel();
            const activeStandardId = syncActiveStandard(activePanel);
            const submitter = event.submitter;

            if (!activeStandardId) {
                event.preventDefault();

                openConfirm({
                    title: "لم يتم تحديد معيار",
                    message: "افتحي المعيار المطلوب حفظه أولًا، ثم اضغطي حفظ كمسودة أو اعتماد.",
                    confirmText: "حسنًا",
                    cancelText: "إلغاء",
                    icon: "!",
                    type: "warning"
                }, function () {});

                return;
            }

            if (submitter && submitter.value === "approve" && !approveAllowed) {
                event.preventDefault();

                openConfirm({
                    title: "اعتماد المعيار الحالي",
                    message: "سيتم اعتماد المعيار المفتوح فقط كنسخة نهائية. تأكدي من مراجعة درجته وملاحظاته قبل المتابعة.",
                    confirmText: "اعتماد المعيار",
                    cancelText: "إلغاء",
                    icon: "✓",
                    type: "success"
                }, function (confirmed) {
                    if (confirmed) {
                        approveAllowed = true;
                        syncActiveStandard(getActivePanel());

                        if (reviewForm.requestSubmit) {
                            reviewForm.requestSubmit(submitter);
                        } else {
                            const actionInput = document.createElement("input");
                            actionInput.type = "hidden";
                            actionInput.name = "action";
                            actionInput.value = "approve";
                            reviewForm.appendChild(actionInput);
                            reviewForm.submit();
                        }
                    }
                });
            }
        });
    }

    openDraftEditLinks();
    normalizeInputsDirection();
    syncActiveStandard(getActivePanel());

    if (isLoadDraft) {
        setActiveMode("manual");
        resizeAllTextareas();
    } else {
        setActiveMode("manual");
    }
});