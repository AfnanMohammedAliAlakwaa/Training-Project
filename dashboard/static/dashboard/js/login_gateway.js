document.addEventListener("DOMContentLoaded", function () {
    const card =
        document.getElementById("portalCard");

    const transitionLayer =
        document.getElementById("portalTransition");

    const options =
        document.querySelectorAll(".portal-option");

    if (!card || !transitionLayer || !options.length) {
        return;
    }

    let isTransitioning = false;

    function resetTransition() {
        isTransitioning = false;

        card.classList.remove("is-loading");

        transitionLayer.classList.remove(
            "is-active",
            "to-main",
            "to-admin"
        );

        options.forEach(function (option) {
            option.classList.remove("is-selected");
        });
    }

    function openSelectedLogin(option) {
        if (isTransitioning) {
            return;
        }

        const targetUrl =
            option.dataset.url;

        if (!targetUrl) {
            return;
        }

        isTransitioning = true;

        const isMainSystem =
            option.classList.contains(
                "portal-main-system"
            );

        /* إزالة أي حركة قديمة */
        transitionLayer.classList.remove(
            "is-active",
            "to-main",
            "to-admin"
        );

        options.forEach(function (item) {
            item.classList.remove("is-selected");
        });

        /* تحديد لون الحركة من data-color */
        transitionLayer.style.setProperty(
            "--transition-color",
            option.dataset.color || "#dceeff"
        );

        /* تحديد اتجاه الحركة */
        if (isMainSystem) {
            transitionLayer.classList.add(
                "to-main"
            );
        } else {
            transitionLayer.classList.add(
                "to-admin"
            );
        }

        card.classList.add("is-loading");
        option.classList.add("is-selected");

        /*
           استخدام إطارين حتى يبدأ المتصفح من الخط
           ثم يشغل التمدد بوضوح.
        */
        window.requestAnimationFrame(function () {
            window.requestAnimationFrame(function () {
                transitionLayer.classList.add(
                    "is-active"
                );
            });
        });

        /* الانتقال بعد اكتمال الأنميشن */
        window.setTimeout(function () {
            window.location.assign(targetUrl);
        }, 740);
    }

    options.forEach(function (option) {
        option.addEventListener(
            "click",
            function () {
                openSelectedLogin(option);
            }
        );

        option.addEventListener(
            "keydown",
            function (event) {
                if (
                    event.key !== "Enter"
                    && event.key !== " "
                ) {
                    return;
                }

                event.preventDefault();

                openSelectedLogin(option);
            }
        );
    });

    /*
       عند الرجوع للصفحة بزر الرجوع
       تزال حالة الأنميشن السابقة.
    */
    window.addEventListener(
        "pageshow",
        function () {
            resetTransition();
        }
    );
});