document.addEventListener(
    "click",
    function (event) {
        const link = event.target.closest("a");

        if (!link) {
            return;
        }

        const targetUrl = link.href;

        if (
            !targetUrl ||
            (!targetUrl.startsWith("http://") &&
                !targetUrl.startsWith("https://"))
        ) {
            return;
        }

        if (targetUrl.startsWith("http://127.0.0.1:5000")) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        console.log("[CRIS] Intercepted URL:", targetUrl);

        const interceptorUrl =
            "http://127.0.0.1:5000/intercept?target=" +
            encodeURIComponent(targetUrl);

        window.location.href = interceptorUrl;
    },
    true
);