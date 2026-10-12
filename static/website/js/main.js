const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector("#nav-links");

menuButton.addEventListener("click", () => {
  const open = navigation.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

navigation.addEventListener("click", () => {
  navigation.classList.remove("open");
  menuButton.setAttribute("aria-expanded", "false");
});

const form = document.querySelector("#lead-form");

if (form) {
  const status = form.querySelector(".form-status");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");

    status.textContent = "Sending...";
    status.className = "form-status full";
    button.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: new FormData(form),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const firstError = data.errors && Object.values(data.errors)[0];
        throw new Error((firstError && firstError[0]) || "Please check the form and try again.");
      }

      form.reset();
      status.textContent = "Thanks. We will contact you within one business day.";
      status.classList.add("success");
    } catch (error) {
      status.textContent = error.message;
      status.classList.add("error");
    } finally {
      button.disabled = false;
    }
  });
}

// Image popup (lightbox) for project pages: cover, gallery and images inside the case study.
const lightbox = document.querySelector("[data-lightbox-dialog]");

if (lightbox) {
  // Make images inside the case-study text open in the popup too.
  document.querySelectorAll(".case-body img").forEach((img) => {
    img.dataset.lightbox = "project";
    img.dataset.src = img.currentSrc || img.src;
    img.dataset.caption = img.alt || "";
    img.tabIndex = 0;
    img.setAttribute("role", "button");
    img.setAttribute("aria-label", "Enlarge image");
  });

  const triggers = [...document.querySelectorAll("[data-lightbox]")];
  const image = lightbox.querySelector("[data-lb-img]");
  const caption = lightbox.querySelector("[data-lb-caption]");
  const count = lightbox.querySelector("[data-lb-count]");
  const prev = lightbox.querySelector("[data-lb-prev]");
  const next = lightbox.querySelector("[data-lb-next]");
  const close = lightbox.querySelector("[data-lb-close]");
  let index = 0;
  let opener = null;

  const show = (i) => {
    index = (i + triggers.length) % triggers.length;
    const item = triggers[index];
    image.src = item.dataset.src;
    image.alt = item.dataset.caption || "";
    caption.textContent = item.dataset.caption || "";
    count.textContent = triggers.length > 1 ? `${index + 1} / ${triggers.length}` : "";
  };
  const open = (i, trigger) => {
    opener = trigger;
    show(i);
    lightbox.hidden = false;
    document.body.classList.add("lightbox-open");
    prev.hidden = next.hidden = triggers.length < 2;
    close.focus();
  };
  const hide = () => {
    lightbox.hidden = true;
    document.body.classList.remove("lightbox-open");
    image.removeAttribute("src");
    opener?.focus();
  };

  triggers.forEach((trigger, i) => {
    trigger.addEventListener("click", () => open(i, trigger));
    trigger.addEventListener("keydown", (event) => {
      if (trigger.tagName === "IMG" && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        open(i, trigger);
      }
    });
  });
  close.addEventListener("click", hide);
  prev.addEventListener("click", () => show(index - 1));
  next.addEventListener("click", () => show(index + 1));
  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox || event.target.classList.contains("lb-figure")) hide();
  });
  document.addEventListener("keydown", (event) => {
    if (lightbox.hidden) return;
    if (event.key === "Escape") hide();
    if (event.key === "ArrowLeft") show(index - 1);
    if (event.key === "ArrowRight") show(index + 1);
    if (event.key === "Tab") {
      // keep keyboard focus inside the popup
      const focusable = [close, prev, next].filter((b) => !b.hidden);
      const at = focusable.indexOf(document.activeElement);
      event.preventDefault();
      focusable[(at + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length].focus();
    }
  });

  // Swipe on phones
  let startX = null;
  lightbox.addEventListener("touchstart", (event) => { startX = event.touches[0].clientX; }, { passive: true });
  lightbox.addEventListener("touchend", (event) => {
    if (startX === null) return;
    const dx = event.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  });
}
